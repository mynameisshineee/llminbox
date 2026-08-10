#!/usr/bin/env python3
"""
ledger_parse — el troceador de entradas de la red de ledgers, medido contra el corpus real.

## Por qué se reescribe

Una versión anterior de este mismo sellador declaró «2.076 entradas selladas en 6
ledgers». Ese número era del INSTRUMENTO, no del corpus: su regex solo reconocía
cabeceras `## `, y la convención que la flota usa de verdad es `### [...]`. Medido
sobre el corpus real (2026-07-27): 37.126 entradas reales, 2.076 selladas = **5,6% de
cobertura**. En el ledger de mayor volumen de escritura de un solo agente selló UNA.
El hook de arranque imprimía «cadena de hashes íntegra» sobre ese 5,6% sin decir el
denominador.

## Las convenciones que existen de verdad (censo 2026-07-27)

| convención                | entradas | dónde                                          |
|----------------------------|---------|--------------------------------------------------|
| `### [...]`                |  35.030 | la mayoría de los ledgers de este despliegue      |
| `## <ISO> · a → b · T`     |     365 | solo uno de ellos (el de un único escritor spoke) |
| `## [...]` / `## <fecha>`  |   1.717 | el más grande, forma histórica                    |

Ver `PROTOCOL.md`, en este mismo repo, para la especificación completa de lo que el
troceador reconoce. Antes solo existía documentado el formato de UN ledger (el
spoke de un único escritor) — el que usa ~1% del tráfico real. No se corrige la
flota para que encaje con el documento: se reconoce lo que la flota escribe de
verdad, y el documento se ajusta después.

## Lo que este módulo NO hace

No adivina. Cuando no puede extraer un campo (actor, destinatarios, tipo) lo deja a
`None` y lo CUENTA. La cobertura por campo es una salida de primera clase, porque es
la medida de cuánto trabajo queda para tipar el ledger — no un detalle de implementación.
"""
from __future__ import annotations

import hashlib
import os
import re
import unicodedata
from dataclasses import dataclass, field

# Versión del TROCEADOR. Súbela con CUALQUIER cambio que altere qué se extrae
# (nuevos agentes, nuevas etiquetas, otro corte de destinatarios). El servicio la
# compara al arrancar y reconstruye el índice entero si no coincide.
#
# Existe porque hoy me pasó: arreglé el extractor (HEARTBEAT, destinatarios,
# mayúsculas) y el índice siguió sirviendo los datos VIEJOS — el fichero no había
# cambiado, así que no se reindexaba, y el troceador nuevo solo se aplicaba a lo
# que llegara después. Un `lint` verde sobre datos de la versión anterior es la
# misma clase de mentira que llevo cazando todo el día.
#
# v5 (2026-07-27): coautoría `CTO+BE →` ya no tira al coautor (7 cabeceras del
# corpus real cambian de actor); difusión (FLOTA/equipo/todos) sale de `to` a
# su propio campo (1.915 entradas cambian de forma, ninguna de cobertura real
# perdida — ver PROTOCOL.md, sección "Qué NO garantiza el formato hoy").
PARSER_V = 5

# Una entrada empieza en una cabecera de cualquiera de las convenciones vivas.
# Orden importante: `### [` es la dominante (94% del corpus).
H_ENTRY = re.compile(
    r"^(?:"
    r"### \["                                        # dominante: ### [cabecera libre]
    r"|## \d{4}-\d{2}-\d{2}T[\d:]+Z\s*·"             # spoke: ## <ISO> · a → b · TIPO
    r"|## \["                                        # forma histórica: ## [agente TS]
    r"|## \d{4}-\d{2}-\d{2}"                         # forma histórica: ## <fecha> [...]
    r")"
)

TS = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z")
TIPOS = ("PRODUCED", "INGESTED", "FYI", "REQUEST", "ACK", "HELD", "AMEND", "DELTA")

# Los nombres de agente vivos en la flota. Se listan explícitamente en vez de
# inferirse: inferir "la primera palabra" da basura sobre cabeceras que empiezan
# por emoji, verbo o adjetivo, y una atribución equivocada es peor que ninguna
# (lección propia, dos veces: 07-18 y 07-25).
# El CENSO vive en `roster.json`, no aquí. Era una constante de Python, y eso solo
# aguanta con un humano: en cuanto hay varios, cada uno con sus agentes, dar de alta
# a alguien obligaba a editar el troceador y redesplegar el servicio. Medido en el
# ensayo de equipo (2026-07-27): con un agente y un humano dados de alta SOLO en
# el censo local de otro, el extractor devolvía actor=None y destinatarios=[] —
# la bandeja salía vacía teniendo correo.
#
# El fichero lleva además, por agente, el humano que responde de él y un campo de
# clave vacío. Hoy nadie verifica esa clave; existe para que el día que el ledger
# tenga que servir de evidencia no haya que rehacer el formato ni reindexar.
def _censo():
    import json
    import os as _os
    ruta = _os.environ.get("LLMINBOX_ROSTER") or _os.path.join(
        _os.path.dirname(_os.path.abspath(__file__)), "roster.json")
    try:
        with open(ruta, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception as e:                    # sin censo se sigue, pero se DICE
        print(f"[censo] no pude leer {ruta}: {e} — el extractor no reconocerá a nadie")
        return [], {}, [], {}
    nombres = [a["nombre"] for a in d.get("agentes", [])]
    for h in d.get("humanos", []):
        nombres.append(h["nombre"])
        nombres.extend(h.get("alias", []))
    dueno = {a["nombre"].lower(): a.get("humano") for a in d.get("agentes", [])}
    # ESCUCHA — un agente puede recibir, además de lo suyo, el flujo dirigido a OTRO
    # nombre. Suena a alias y no lo es: el cursor sigue siendo suyo. Esa es toda la
    # diferencia entre *leer* un flujo y *consumirlo*, y es lo que permite que un
    # destilador trabaje la cola de la wiki sin vaciarle la bandeja a la sesión que
    # atiende esa misma wiki. Sin este campo, un segundo lector del mismo flujo
    # obliga a elegir entre compartir cursor (se pisan) o duplicar el destinatario
    # en cada entrada (obliga a cambiar cómo escriben los demás, que es justo lo que
    # este producto promete no hacer).
    escucha = {a["nombre"].lower(): list(a.get("escucha", []))
               for a in d.get("agentes", []) if a.get("escucha")}
    return nombres, dueno, d.get("difusion", []), escucha


AGENTES, DUENO, DIFUSION, ESCUCHA = _censo()


def _roles():
    """nombre → ROL, leído del censo. Sin heurística de sufijos: es DATO.

    El mismo rol vive en el censo bajo varios nombres (`qa` y `qa-2`, `cto` y
    `cto-b`: en el censo que motivó esto, 13 de 27 roles tenían más de uno). Para el reparto de
    trabajo eso es una fuga real — el tope triadversarial de 3 contaría 3 NOMBRES y
    dejaría que un mismo rol ocupe dos plazas de revisión.

    Se resuelve con un campo `rol` OPCIONAL en `roster.json`. Si no está, el nombre
    ES su rol y el comportamiento no cambia: nadie se encuentra una conducta nueva
    por actualizar. Deliberadamente NO se agrupa por parecido de nombre — la
    identidad se declara, no se adivina; adivinarla es cómo `cto-cfo-cockpit` acaba
    contando como `cto` el día que sean dos personas distintas.
    """
    import json as _json
    import os as _os
    ruta = _os.environ.get("LLMINBOX_ROSTER") or _os.path.join(
        _os.path.dirname(_os.path.abspath(__file__)), "roster.json")
    try:
        with open(ruta, encoding="utf-8") as fh:
            d = _json.load(fh)
    except Exception:
        return {}
    return {a["nombre"].lower(): (a.get("rol") or a["nombre"])
            for a in d.get("agentes", []) if a.get("nombre")}


ROL_DE = _roles()


def rol_de(nombre: str) -> str:
    """El rol de un agente. Si el censo no lo declara, su rol es él mismo."""
    return ROL_DE.get((nombre or "").lower(), canonico(nombre))
# Conjunto en minúsculas para separar, al leer destinatarios, quién es un agente
# concreto de quién es un destino de difusión (equipo/FLOTA/todos) — ver DIFSET
# más abajo, usado en `_campos` para no mezclarlos en `to`.
DIFSET = {d.lower() for d in DIFUSION}
AGENTES = AGENTES + DIFUSION

# minúsculas → nombre CANÓNICO. Sin esto, `IGNORECASE` parte la identidad: se
# devolvía el texto encontrado, así que `ADA`, `Ada` y `ada` entraban como tres
# actores distintos y un filtro por uno perdía a los otros dos. Salió al ver el
# desplegable de la interfaz lleno de parejas.
CANON = {a.lower(): a for a in AGENTES}


# ── Identidad para RESOLUCIÓN (llminbox ①/②) — DISTINTA de CANON/AGENTES/RE_AGENTE ──
# CANON/AGENTES son para PARSEAR el markdown (quién firma, a quién va dirigido).
# Esto es para decidir si un {agent} de una URL EXISTE. Mezclarlas ensancharía el
# enrutado de correo sin que nadie lo haya pedido — "fe" es palabra española común,
# "be" casaría con cualquier frase que la contenga. Nunca se usa para leer texto.
ROLES_VALIDOS = {r.lower() for r in ROL_DE.values()}   # ~14 tokens: be,cto,fe,wiki...


def _cargar_roles_por_alias():
    """Lee `roles-por-alias.json` — la fuente FIRMADA del censo (Albert, ver
    `_firmado_por`/`_orden` del propio fichero) — si está montada.

    Antes, `canon_identidad()` derivaba su unión de `roster.json` en exclusiva.
    Los dos ficheros eran byte-idénticos el 2026-08-10, pero sin ningún gate que
    lo garantice: un alta firmada AQUÍ sin tocar `roster.json` (que cada operador
    edita a mano en su máquina) devolvía 422 a una identidad legítima. Mismo
    patrón que `_cargar_carriles()` en servicio.py: env var vacía por defecto
    (`LLMINBOX_ROLES_ALIAS`) + mount read-only del fichero real — quien clone
    esto no se encuentra una fuente ajena montada sola.

    Devuelve None si la env var está vacía o el fichero no se deja leer — la
    señal de "no montado" que `canon_identidad()` usa para DEGRADAR a la
    conducta de hoy (roster.json) en vez de fallar abierto.

    ⚠️ `sin_rol` NO se carga como veto, y no es un descuido. Un primer intento
    de este fix devolvía 422 a todo nombre listado en `sin_rol`, leyendo su
    nombre como "no es identidad". Falsado contra el índice vivo el 2026-08-10:
    los 13 nombres de `sin_rol` están TODOS en `roster.json`, y dos tienen
    cursores ACTIVOS (`bikeus` en 2 ledgers, `lead-b-cfo-cockpit` en 1) —
    vetarlos habría roto la bandeja del carril bik.eus en el deploy. `sin_rol`
    significa "sin ROL que agrupe" (no colapsan en la migración ②, cada uno es
    su propia clave de cursor vía `rol_de()`), no "sin bandeja".
    """
    import json as _json
    import os as _os
    ruta = _os.environ.get("LLMINBOX_ROLES_ALIAS", "")
    if not ruta:
        return None
    try:
        with open(ruta, encoding="utf-8") as fh:
            d = _json.load(fh)
    except Exception as e:
        print(f"[roles-alias] no pude leer {ruta}: {e} — degrado a roster.json "
              f"(riesgo documentado: un alta firmada aquí sin tocar roster.json "
              f"no se vería hasta que el fichero vuelva a leerse)", flush=True)
        return None
    return {k.lower(): v for k, v in d.get("rol_por_alias", {}).items()}


ROLES_ALIAS = _cargar_roles_por_alias()


def canon_identidad(nombre: str) -> str | None:
    """Forma canónica de `nombre` para identidad de cursor, o None si no resuelve.

    Con `roles-por-alias.json` MONTADO (`LLMINBOX_ROLES_ALIAS`), la unión del
    encargo: `rol_por_alias` (claves = alias, valores = rol) ∪ sus propios
    tokens de rol sueltos ∪ agentes/humanos/difusión de roster.json (CANON).
    Los nombres de `sin_rol` NO vetan nada: si están en roster resuelven como
    ellos mismos (caso `bikeus`, con cursores vivos — ver docstring de
    `_cargar_roles_por_alias`), y si no están en ninguna fuente no resuelven,
    como cualquier otro nombre desconocido.

    SIN montar (env var vacía o fichero ilegible): degrada a la conducta de
    hoy — sólo roster.json (CANON ∪ ROLES_VALIDOS) — SIN fail-open. El riesgo
    de que las dos fuentes diverjan queda documentado, no resuelto: mientras
    no esté montado, un alta que sólo exista en roles-por-alias.json sigue sin
    resolver, igual que antes de este fix.
    """
    if not nombre:
        return None
    bajo = nombre.lower()
    if ROLES_ALIAS is not None:
        if bajo in ROLES_ALIAS:
            return ROLES_ALIAS[bajo]
        if bajo in ROLES_ALIAS.values():
            return bajo
        if bajo in CANON:
            return CANON[bajo]
        return None
    if bajo in CANON:
        return CANON[bajo]
    if bajo in ROLES_VALIDOS:
        return bajo
    return None


# ── Direccionamiento por `@nombre` en cabeceras SIN flecha ────────────────────
#
# Sin flecha, `to` se quedaba vacío. Y eso NO significaba «no iba a nadie»: medido
# sobre 64bis en agosto, de 1.350 cabeceras sin flecha **995 nombraban con `@` a un
# agente DEL CENSO** y llminbox no se lo entregaba a ninguno. El mensaje dirigido no
# llegaba dirigido ⇒ todos leían el canal entero ⇒ cualquiera cogía el trabajo. La
# duplicación que el operador nos reprocha la fabricaba este hueco, no la disciplina.
#
# Va con CORTE POR FECHA y apagado por defecto, y el motivo está medido: aplicarlo
# retroactivo haría aparecer **12.442 entradas de golpe** repartidas en 25 agentes
# —`qa` se despertaría con 1.977 sin leer—, y una bandeja de dos mil devuelve a
# cualquiera a leer el canal entero, que es justo lo que esto viene a quitar.
# `LLMINBOX_ARROBA_DESDE=YYYY-MM-DD` ⇒ sólo las entradas con sello IGUAL O POSTERIOR.
# Vacío ⇒ desactivado: quien clone esto no se encuentra un cambio de conducta.
ARROBA_DESDE = os.environ.get("LLMINBOX_ARROBA_DESDE", "").strip()
# El sigilo `@` ES la señal, y por eso no se leen los nombres a secas: mencionar a un
# agente («como midió backend…») es cita, no destino. Confundirlas convertiría cada
# cita en una entrega y multiplicaría el correo en vez de dirigirlo.
RE_ARROBA = re.compile(r"@([A-Za-z][A-Za-z0-9_-]{1,24})")


def canonico(nombre):
    return CANON.get(nombre.lower(), nombre) if nombre else nombre


def escuchados(agent: str) -> list[str]:
    """Los nombres cuyo correo cae en la bandeja de `agent`: el suyo y los que escuche.

    Canónicos y sin repetir, con el propio SIEMPRE primero. Un nombre que el censo no
    conoce se devuelve tal cual: alguien puede tener bandeja antes de estar dado de
    alta, y negársela por eso sería esconder correo que existe.
    """
    fuera, vistos = [], set()
    for n in [agent] + list(ESCUCHA.get(agent.lower(), [])):
        c = canonico(n)
        if c.lower() not in vistos:
            vistos.add(c.lower())
            fuera.append(c)
    return fuera
# Se ordenan de más largo a más corto para que `alice-backend` gane a `cto`.
AGENTES.sort(key=len, reverse=True)
# IGNORECASE: la convención histórica `## <fecha> [BE→CTO]` va en mayúsculas y sin
# esto no casaba ninguna — 1.717 entradas invisibles al extractor.
# Con el censo VACÍO —el día uno de cualquiera que instale esto— una alternancia sin
# ramas casa la cadena vacía en todas partes y devolvía `to=['']`: destinatarios
# fantasma en cada entrada. Un patrón que no puede casar nunca es la respuesta.
RE_AGENTE = re.compile(
    (r"(?<![\w-])(" + "|".join(re.escape(a) for a in AGENTES) + r")(?![\w-])")
    if AGENTES else r"(?!)", re.IGNORECASE)

# ETIQUETAS que NO son agentes aunque abran la cabecera. `HEARTBEAT` estaba en la
# lista de agentes y ganaba la carrera por posición: `### [HEARTBEAT alice-backend]`
# se atribuía a "HEARTBEAT" en vez de a alice-backend. Medido sobre el corpus real:
# **3.441 de 23.496 entradas (14,6%)** con el actor sustituido por la etiqueta, así
# que `/entries?actor=alice-backend` perdía todos sus heartbeats. Se saltan antes de
# buscar el actor, y se recogen como tipo.
ETIQUETAS = re.compile(r"^\s*(HEARTBEAT|CARRY-FORWARD|CLAIM|CANON|CERT|DONE|RESP|AVISO|MSG|ASK|ACK|STATUS|INFO|HANDOFF)"
                       r"(?:[/·\-]\s*(?:HEARTBEAT|CARRY-FORWARD|CLAIM|CANON|CERT|DONE|RESP|AVISO|MSG|ASK|ACK|STATUS|INFO|HANDOFF))*\s*",
                       re.IGNORECASE)

# Anotación entre paréntesis: los agentes explican CADA destinatario con su motivo,
# y esas explicaciones llevan dentro los mismos separadores (`·`, `—`, `]`) que se
# usaban para cortar la lista. Cortar en el primero perdía TODOS los destinatarios
# posteriores — medido a mano sobre 30 cabeceras: de 14 con 3+ destinatarios, 12
# perdieron al menos uno. Se quitan las anotaciones ANTES de leer la lista.
PARENT = re.compile(r"\([^()]*\)|\[[^\[\]]*\]")

# Separadores de destinatario usados de verdad en las cabeceras: →, ->, ∧, +, y
FLECHA = re.compile(r"\s*(?:→|->)\s*")

# Hueco entre dos agentes PEGADOS justo antes de la flecha (`CTO+BE →`, `BE/CTO
# →`): si entre el fin de uno y el principio del otro no hay nada más que este
# separador, son coautores, no "el segundo tapa al primero". Ver _campos().
JUNTA = re.compile(r"^\s*[+/∧]\s*$")

# La coautoría solo se lee cuando la flecha está CERCA del principio de la
# cabecera. Medido sobre el corpus real (2026-07-27): en las 7 cabeceras
# genuinas de coautoría (`[CTO+BE → ...]`), la flecha cae a 21-23 caracteres
# del principio. Pero hay cabeceras HEARTBEAT larguísimas —una sola línea de
# hasta 1.120 caracteres— donde aparece una flecha SUELTA dentro de la prosa
# libre (p.ej. "cutover B-1 (be/cto/sec/fe) → ..."), y justo antes por
# casualidad caen dos nombres de agente pegados: sin este tope, 17 de las 24
# cabeceras que cambiaban de actor eran ESTE ruido, no coautoría real — la
# más cercana de las falsas cae a 96 caracteres, así que 40 deja margen de
# sobra a un lado y al otro.
COAUTOR_MAX_IZQ = 40


def _sin_emoji(s: str) -> str:
    """Quita símbolos/pictogramas para que el extractor vea el texto."""
    return "".join(c for c in s if unicodedata.category(c) not in ("So", "Sk", "Cs"))


@dataclass
class Entrada:
    seq: int
    line_no: int
    byte_off: int
    head: str
    text: str
    ts: str | None = None
    actor: str | None = None
    to: list[str] = field(default_factory=list)
    # ¿Los destinatarios salieron de un `@` en una cabecera SIN flecha? Se marca
    # porque quien indexa necesita distinguirlo: para una entrada NUEVA se enrutan
    # siempre —es correo de ahora—, pero re-derivar el histórico añadiría 1.679
    # entradas de golpe a las bandejas. La decisión no la puede tomar el troceador,
    # que no sabe si la entrada es nueva; la toma `reindex`, que sí.
    por_arroba: bool = False
    # Destinos de DIFUSIÓN (equipo/FLOTA/todos — ver roster.json), separados de
    # `to` a propósito: no son un agente al que dirigir una bandeja individual.
    # Campo nuevo (PARSER_V 5); servicio.py de hoy no lo lee — es aditivo, no
    # rompe a quien solo mire `.to`.
    difusion: list[str] = field(default_factory=list)
    tipo: str | None = None

    @property
    def sha(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


def _campos(head: str, cola: str) -> tuple[str | None, str | None, list[str], list[str], str | None]:
    """Extrae (ts, actor, destinatarios, difusion, tipo, por_arroba).

    Devuelve None en lo que no se pueda leer. `por_arroba` dice si los destinatarios
    salieron de un `@` en una cabecera sin flecha — ver el campo del mismo nombre.
    """
    m = TS.search(head) or TS.search(cola)
    ts = m.group(1) if m else None

    # El cuerpo de la cabecera: lo de dentro del primer corchete si lo hay.
    inner = head
    mb = re.match(r"^#{2,3} \[(.*)$", head)
    if mb:
        inner = mb.group(1)
    inner = _sin_emoji(inner)

    # Las etiquetas de apertura (HEARTBEAT, CARRY-FORWARD…) se retiran antes de
    # buscar el actor: son el TIPO de la entrada, no quien la escribe.
    etiqueta = ETIQUETAS.match(inner)
    if etiqueta:
        inner = inner[etiqueta.end():]

    to: list[str] = []
    difusion: list[str] = []
    por_arroba = False
    actor = None
    if FLECHA.search(inner):
        izq, der = FLECHA.split(inner, 1)
        # El actor es el nombre PEGADO a la flecha, no el primero que se mencione:
        # una cabecera que MENCIONA a otro agente antes de la flecha (`escritor
        # ... cita a @lector ... → destinatarios`) se atribuía a "lector" por ir
        # antes en el texto. Se busca por la derecha.
        izq_limpio = PARENT.sub(" ", izq)
        ma = list(RE_AGENTE.finditer(izq_limpio))
        if ma:
            # Autoría conjunta: dos agentes PEGADOS justo antes de la flecha
            # (`CTO+BE →`, `BE/CTO →`), sin nada más entre ellos que el
            # separador. Medido sobre el corpus real (2026-07-27): 7 cabeceras
            # así en 37k entradas; tomar solo el último match (`ma[-1]`) tiraba
            # al coautor — `CTO+BE → FLOTA` quedaba con actor="BE" y "CTO" se
            # perdía sin dejar rastro. Se juntan con "+" SOLO cuando el hueco
            # entre los dos últimos matches es justo ese separador: si hay
            # cualquier otra cosa en medio (p.ej. "SECURITY · FE", una etiqueta
            # de tema seguida del actor real) el comportamiento no cambia — el
            # último gana, que es lo correcto ahí.
            if (len(ma) >= 2 and len(izq_limpio) <= COAUTOR_MAX_IZQ
                    and JUNTA.fullmatch(izq_limpio[ma[-2].end():ma[-1].start()])):
                actor = canonico(ma[-2].group(1)) + "+" + canonico(ma[-1].group(1))
            else:
                actor = canonico(ma[-1].group(1))
        # Se quitan las anotaciones entre paréntesis/corchetes y se lee la lista
        # ENTERA hasta el cierre de la cabecera, no hasta el primer separador.
        der = PARENT.sub(" ", der)
        der = re.split(r"\]\s|\s—\s|\s–\s", der, maxsplit=1)[0]
        vistos = set()
        for m in RE_AGENTE.finditer(der):
            n = canonico(m.group(1))
            if n.lower() not in vistos:
                vistos.add(n.lower())
                # Los destinos de DIFUSIÓN (equipo/FLOTA/todos, ver roster.json)
                # no son un agente concreto: mezclados en `to` hacían
                # indistinguible "esto iba a una persona" de "esto iba a todo
                # el mundo". Medido: 1.915 de 37k entradas tenían ambos tipos
                # en la misma lista — `/lint` no podía separar deuda real
                # (nadie nombrado) de aviso general (nombrado el equipo entero).
                if n.lower() in DIFSET:
                    difusion.append(n)
                else:
                    to.append(n)
    else:
        ma = RE_AGENTE.search(PARENT.sub(" ", inner))
        actor = canonico(ma.group(1)) if ma else None
        # Sin flecha no hay lista de destino que leer… salvo los `@` (ver arriba).
        # Se calculan SIEMPRE que la función esté activa. El corte por fecha ya no
        # se aplica aquí: exigir sello dejaba fuera el 15,7 % de las entradas —8.550
        # sin `ts`— y a ésas el router ni las miraba. Quien decide es `reindex`.
        if ARROBA_DESDE:
            vistos = {actor.lower()} if actor else set()
            for m in RE_ARROBA.finditer(inner):
                bruto = m.group(1)
                # La pertenencia al censo se comprueba AQUÍ y no se delega en
                # `canonico`, que devuelve tal cual lo que no conoce: sin esta línea
                # un `@deploy` o un `@media` de CSS entraría como destinatario.
                if bruto.lower() not in CANON or bruto.lower() in vistos:
                    continue
                vistos.add(bruto.lower())
                n = canonico(bruto)
                (difusion if n.lower() in DIFSET else to).append(n)
                por_arroba = True

    tipo = next((t for t in TIPOS if t in head), None)
    if tipo is None and etiqueta:
        tipo = etiqueta.group(1).upper()
    return ts, actor, to, difusion, tipo, por_arroba


def parse(path: str, desde_byte: int = 0):
    """Trocea el ledger en entradas. `desde_byte` permite ingesta incremental.

    Devuelve (entradas, byte_final). Las entradas se cortan en la SIGUIENTE cabecera,
    así que la última entrada de un fichero que está creciendo puede estar a medias:
    el llamante decide si la usa (leer) o la ignora (sellar).
    """
    with open(path, "rb") as fh:
        fh.seek(desde_byte)
        raw = fh.read()
    txt = raw.decode("utf-8", errors="replace")
    lines = txt.splitlines(keepends=True)

    offs, acc = [], desde_byte
    for l in lines:
        offs.append(acc)
        acc += len(l.encode("utf-8"))

    starts = [i for i, l in enumerate(lines) if H_ENTRY.match(l)]
    out = []
    for n, i in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        text = "".join(lines[i:end]).rstrip() + "\n"
        head = lines[i].rstrip("\n")
        cola = "".join(lines[i + 1:i + 4])
        ts, actor, to, difusion, tipo, por_arroba = _campos(head, cola)
        out.append(Entrada(seq=n, line_no=i + 1, byte_off=offs[i], head=head,
                           text=text, ts=ts, actor=actor, to=to, difusion=difusion,
                           tipo=tipo, por_arroba=por_arroba))
    return out, acc


if __name__ == "__main__":
    import os
    import sys

    def _rutas_por_defecto():
        """Sin argumentos en la línea de comandos, lee `LLMINBOX_LEDGERS` — mismo
        formato `nombre=ruta,nombre=ruta` que `docker-compose.yml` — para que este
        módulo no lleve cableados los ledgers de un despliegue concreto. Antes
        (PARSER_V<5) la lista por defecto era literalmente la de este despliegue;
        eso no vale para un repo publicado, que no conoce los ledgers de nadie."""
        crudo = os.environ.get("LLMINBOX_LEDGERS", "")
        return [ruta for _, ruta in (p.split("=", 1) for p in crudo.split(",") if "=" in p)]

    rutas = sys.argv[1:] or _rutas_por_defecto()
    if not rutas:
        print("uso: python3 ledger_parse.py <ledger.md> [otro.md ...]")
        print("     (o exporta LLMINBOX_LEDGERS='nombre=/ruta/a/ledger.md,...')")
        sys.exit(1)
    tot = 0
    print(f"{'ledger':<32}{'entradas':>9}{'ts':>7}{'actor':>7}{'to':>7}{'difusion':>9}{'tipo':>7}")
    for r in rutas:
        p = os.path.expanduser(r)
        if not os.path.exists(p):
            continue
        ents, _ = parse(p)
        tot += len(ents)
        n = max(len(ents), 1)
        pct = lambda f: f"{100 * sum(1 for e in ents if f(e)) // n}%"  # noqa: E731
        print(f"{os.path.basename(p):<32}{len(ents):>9}"
              f"{pct(lambda e: e.ts):>7}{pct(lambda e: e.actor):>7}"
              f"{pct(lambda e: e.to):>7}{pct(lambda e: e.difusion):>9}{pct(lambda e: e.tipo):>7}")
    print(f"{'TOTAL':<32}{tot:>9}")
