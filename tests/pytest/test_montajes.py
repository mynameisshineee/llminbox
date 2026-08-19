"""Ningún bind-mount de FICHERO ÚNICO en la composición de Docker.

Nace de un fallo de producción del 2026-08-18 y de su repetición evitada:

`roles-por-alias.json` estaba montado como fichero suelto. El host lo reemplazó
por rename —que es como se DEBE escribir un fichero de forma atómica: tmp + mv—,
el bind-mount se quedó clavado al INODO borrado, y `/organigrama` sirvió DOS DÍAS
un organigrama viejo sin avisar. Nadie lo notó porque el fallo no da error: da
datos, y son plausibles.

Un mount de DIRECTORIO no tiene el problema: la resolución del nombre se rehace en
cada `open()`, así que un rename encima se ve inmediatamente.

Esto es la invariante, no el recordatorio. Un comentario pide que alguien se
acuerde; un test falla solo cuando alguien no se acuerda.

⛔ LO QUE ESTE GUARDA NO CUBRE, dicho aquí para que su nombre no prometa de más:
   un fichero SIN EXTENSIÓN montado a un destino SIN EXTENSIÓN es indistinguible
   de un directorio mirando sólo la sintaxis, y mirar el disco no vale — en CI las
   rutas del host no existen y un guarda que sólo funciona en una máquina no
   guarda nada. Cubre las dos formas de Compose (corta y larga) y cualquier
   extremo con extensión conocida. El hueco queda escrito, no tapado.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
COMPOSES = ("docker-compose.yml", "docker-compose.override.yml")

# Extensiones que delatan un FICHERO. Se miran los DOS extremos: un `source` sin
# extensión con `target: /censo.json` sigue siendo un mount de fichero.
EXT_DE_FICHERO = (".json", ".tsv", ".md", ".yml", ".yaml", ".txt", ".env",
                  ".sqlite", ".db", ".sh", ".py", ".token", ".log", ".csv")

# ── RIESGO ACEPTADO TEMPORALMENTE ────────────────────────────────────────────
# No es «exento = seguro». Es un riesgo vivo con su ficha:
#
#   single-file mount ................ sí
#   protección mecánica contra rename . NO
#   invariante operativa ............. el ledger es append-only y se escribe con
#                                      `>>` en sitio, nunca con tmp+mv
#   consecuencia si se viola ......... inodo rancio en silencio, sin un error
#
# No se arregla montando su directorio: cada ledger vive en la raíz de un repo
# distinto y expondría nueve proyectos dentro del contenedor. La excepción se
# apoya en una DISCIPLINA, no en un mecanismo — y por eso v0.3.1 debe ligarla
# formalmente al guarda que sostiene esa disciplina (`guard-ledger-append-only`):
# si ese guarda se desactiva o deja de cubrir tmp+mv, ESTA excepción debería
# ponerse roja. Hoy sólo está documentada; esa dependencia no es demostrable
# desde aquí, y decir lo contrario sería el mismo defecto que el guarda persigue.
#
# Casa ORIGEN y DESTINO, no un prefijo suelto: `/ledgers/` a secas perdonaría
# cualquier fichero futuro que alguien meta ahí.
RIESGO_ACEPTADO = (
    (re.compile(r"/LEDGER[\w.-]*\.md$"),
     re.compile(r"^/ledgers/[\w.-]+\.md$"),
     "ledgers: append-only en sitio (disciplina, no mecanismo) — ver v0.3.1"),
)


def _aceptado(origen: str, destino: str) -> str | None:
    return next((m for o, d, m in RIESGO_ACEPTADO
                 if o.search(origen) and d.match(destino)), None)


def _montajes(texto: str):
    """(origen, destino) de cada volumen, en las DOS formas de Compose.

    La forma larga es Compose perfectamente válido:

        - type: bind
          source: ./roster.json
          target: /censo.json

    Un guarda que sólo mira la forma corta se puede rodear sin querer, y entonces
    su nombre promete una clase que no cubre. Ignora volúmenes nombrados.
    """
    lineas = texto.splitlines()
    i = 0
    while i < len(lineas):
        ln = lineas[i]
        m = re.match(r"(\s*)-\s*(.*)$", ln)
        if not m:
            i += 1
            continue
        sangria, resto = len(m.group(1)), m.group(2)
        # ── forma larga: el item abre un mapa con `type:`/`source:`/`target:` ──
        if re.match(r"(type|source|target|read_only)\s*:", resto):
            bloque = [resto]
            j = i + 1
            while j < len(lineas):
                sig = lineas[j]
                if not sig.strip():
                    j += 1
                    continue
                sang_sig = len(sig) - len(sig.lstrip())
                if sang_sig <= sangria and re.match(r"\s*-\s", sig):
                    break
                if sang_sig <= sangria:
                    break
                bloque.append(sig.strip())
                j += 1
            texto_bloque = "\n".join(bloque)
            src = re.search(r"source\s*:\s*[\"\']?([^\"\'\n]+)", texto_bloque)
            dst = re.search(r"target\s*:\s*[\"\']?([^\"\'\n]+)", texto_bloque)
            if src and dst:
                yield src.group(1).strip(), dst.group(1).strip()
            i = j
            continue
        # ── forma corta ──
        c = re.match(r'"?([^":]+):([^":]+?)(?::(ro|rw))?"?\s*$', resto)
        if c:
            origen, destino = c.group(1).strip(), c.group(2).strip()
            if "/" in origen or "." in origen:      # no es un volumen nombrado
                yield origen, destino
        i += 1


def _es_fichero(origen: str, destino: str) -> bool:
    return (origen.lower().endswith(EXT_DE_FICHERO)
            or destino.lower().endswith(EXT_DE_FICHERO))


def test_ningun_bind_mount_de_fichero_unico():
    """El falsador de la clase entera.

    FALSADOR: devolver `- ./roster.json:/censo.json:ro` —en cualquiera de las dos
    formas— pone esto rojo con el nombre del fichero."""
    culpables = []
    for nombre in COMPOSES:
        ruta = RAIZ / nombre
        if not ruta.exists():
            continue                      # el override es local, puede no estar
        for origen, destino in _montajes(ruta.read_text()):
            if _es_fichero(origen, destino) and not _aceptado(origen, destino):
                culpables.append(f"{nombre}: {origen} → {destino}")
    assert not culpables, (
        "bind-mount de FICHERO ÚNICO — se ata al inodo y el host puede jubilarlo "
        "con un rename, dejando al contenedor leyendo bytes muertos para siempre "
        "(pasó el 2026-08-18 con roles-por-alias.json: 2 días sirviendo un "
        "organigrama viejo, sin error). Monta el DIRECTORIO y apunta la ruta "
        "dentro:\n  " + "\n  ".join(culpables))


def test_el_guarda_ve_de_verdad_los_montajes():
    """CONTROL, y no es ceremonia: si el parser no reconociera ninguna línea de
    volumen, el test de arriba pasaría siempre — verde por no mirar. Ese es el
    modo de fallo más caro de este repo y tiene su propia cicatriz."""
    vistos = []
    for nombre in COMPOSES:
        ruta = RAIZ / nombre
        if ruta.exists():
            vistos += list(_montajes(ruta.read_text()))
    assert len(vistos) >= 2, f"el parser no ve los volúmenes: {vistos}"
    assert any(d.startswith("/") and not _es_fichero(o, d) for o, d in vistos), (
        f"no reconoce ningún mount de directorio: {vistos}")


def test_el_riesgo_aceptado_sigue_aplicando():
    """CONTROL de la lista de riesgos aceptados. Uno que ya no casa con nada es
    deuda invisible: parece cubrir algo y no cubre nada, y el día que alguien
    reintroduzca ese montaje lo tapará sin que nadie lo note.

    FALSADOR: cuando los ledgers dejen de montarse como fichero —que es el
    objetivo—, esto se pone rojo y obliga a RETIRAR la entrada."""
    usados = set()
    for nombre in COMPOSES:
        ruta = RAIZ / nombre
        if not ruta.exists():
            continue
        for origen, destino in _montajes(ruta.read_text()):
            if _es_fichero(origen, destino):
                m = _aceptado(origen, destino)
                if m:
                    usados.add(m)
    huerfanos = {m for _, _, m in RIESGO_ACEPTADO} - usados
    assert not huerfanos, (
        f"riesgos aceptados que ya no cubren nada: {sorted(huerfanos)} — retíralos "
        "en vez de dejarlos tapando algo que ya no existe")


CANARIO_CORTO = '      - "./roster.json:/censo.json:ro"\n'
# Origen SIN extensión, destino con ella: sigue siendo un mount de fichero, y
# mirar sólo el origen lo dejaba pasar. El mutante que quitaba el destino de la
# comprobación sobrevivía porque en las composiciones de hoy los dos extremos
# tienen extensión — el hueco existía y no había forma de verlo.
CANARIO_SIN_EXT_EN_ORIGEN = '      - "./censo:/censo.json:ro"\n'
CANARIO_LARGO = """      - type: bind
        source: ./roster.json
        target: /censo.json
        read_only: true
"""


def test_el_canario_se_caza_en_LAS_DOS_formas():
    """El guarda de la lista de excepciones Y del parser, que son los dos sitios
    donde un guarda se muere en silencio.

    · Una excepción puede ensancharse hasta tragárselo todo.
    · Un parser que sólo entiende la forma corta deja pasar la larga, que es
      Compose igual de válido. El mutante existía: reescribir el canario en forma
      larga sobrevivía al guarda anterior.
    · Y mirar sólo el ORIGEN deja pasar `./censo:/censo.json`, que es un mount de
      fichero con el origen disfrazado. Ese mutante también sobrevivía, porque en
      las composiciones de hoy los dos extremos llevan extensión.

    El canario es el montaje EXACTO que rompió el organigrama. Si deja de cazarse
    en cualquiera de las dos formas, el guarda ya no protege de la clase que su
    nombre promete."""
    for etiqueta, texto in (("corta", CANARIO_CORTO), ("larga", CANARIO_LARGO),
                            ("sin extensión en el origen", CANARIO_SIN_EXT_EN_ORIGEN)):
        montajes = list(_montajes(texto))
        assert montajes, f"el parser no ve la forma {etiqueta}: {texto!r}"
        origen, destino = montajes[0]
        assert _es_fichero(origen, destino), f"forma {etiqueta}: {origen} → {destino}"
        assert _aceptado(origen, destino) is None, (
            f"un riesgo aceptado se tragó el canario en forma {etiqueta} "
            f"({origen} → {destino}): el guarda ya no protege de nada")
