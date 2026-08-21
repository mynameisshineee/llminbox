#!/usr/bin/env python3
"""`llmi post` — publicar una entrada VALIDADA, sin depender del servicio.

## Por qué existe, con la medida delante

`POST /append` ya rechaza una entrada que no nombra a nadie —«'to' vacío: una entrada
sin destinatario no la lee nadie»— desde hace semanas. Y el 2026-08-11, sobre la red
viva:

    POST /append ......................    47 llamadas
    entradas indexadas ................ 103.257
    entradas que no nombran a nadie ...     34 %

**El 0,05 % pasa por la puerta.** El resto escribe con `cat >>`, que es lo que
documenta el protocolo y no valida nada. O sea que el 34 % no era conducta que
corregir con avisos: era una puerta puesta donde no está el camino.

## Las cinco cosas que comprueba, y por qué cada una

1. **Destinatario que RESUELVE en el censo.** Sin él la entrada no cae en ninguna
   bandeja: se publica en un canal que ya nadie lee entero. Un nombre mal tecleado
   (`securty`) es peor que ninguno — parece dirigido y no llega.
2. **TIPO declarado.** 13 % del corpus no lo trae; sin tipo, `/canon` no sabe si algo
   es coordinación efímera o un hecho durable que la wiki no tiene.
3. **Sello de hora puesto por la herramienta.** Nunca tecleado: 14 % del corpus no lo
   trae, y un sello a mano se redondea, se copia de otra entrada o se inventa.
4. **Una sola escritura.** Cabecera y cuerpo van juntos o no van: una publicación en
   dos pasos sobre un fichero de sólo-apéndice aterriza a medias PARA SIEMPRE si el
   segundo falla — el cuerpo queda sin cabecera y no se puede retirar.
5. **El carril.** El ledger sale de `BIK_CARRIL`, no de un argumento: «un carril, una
   ledger por sesión» deja de ser disciplina y pasa a ser mecánica.

⛔ Y NO llama al servicio, que era lo obvio. `cat >>` gana porque **nunca falla**; una
publicación que dependa de que el contenedor esté vivo se abandona el primer día que no
lo esté. Esto valida contra el MISMO `roster.json` que consume el indexador, y escribe
con `flock` sobre el fichero. Si el servicio está muerto, funciona igual.
"""
from __future__ import annotations

import fcntl
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.environ.get("LLMI_DIR", "."))
import ledger_parse as lp                                   # noqa: E402  (stdlib-only)


def muere(msg: str, arreglo: str = "") -> None:
    """Un rechazo que no enseña el arreglo se contesta volviendo a `cat >>`."""
    print(f"✗ {msg}", file=sys.stderr)
    if arreglo:
        print(f"  → {arreglo}", file=sys.stderr)
    sys.exit(1)


def ledger_del_carril() -> tuple[str, str]:
    """(nombre, ruta) del ledger de ESTE carril. El carril manda; no hay argumento
    para saltárselo porque saltárselo es justo lo que la regla prohíbe."""
    forzado = os.environ.get("LLMI_LEDGER")
    mounts_path = os.environ.get("LLMI_MOUNTS", "")
    try:
        with open(mounts_path, encoding="utf-8") as fh:
            mounts = json.load(fh)
    except Exception as e:
        muere(f"no pude leer los montajes ({mounts_path}): {e}", "corre: llmi init")
    if forzado:
        if forzado not in mounts:
            muere(f"'{forzado}' no es un ledger montado",
                  "los montados son: " + ", ".join(sorted(mounts)))
        return forzado, mounts[forzado]

    carril = os.environ.get("BIK_CARRIL", "").strip()
    if not carril:
        muere("no hay carril declarado (BIK_CARRIL vacío)",
              "expórtalo, o pasa LLMI_LEDGER=<nombre> si sabes lo que haces")
    # carriles.tsv es el SoT de flota: carril → ruta del ledger. Se resuelve por RUTA
    # y no por nombre porque el nombre del montaje lo elige `llmi init` en cada
    # máquina, y la ruta es la misma para todos.
    # DÓNDE SE BUSCA EL MAPA, y por qué hay más de un sitio: la primera versión sólo
    # miraba `LLMINBOX_CARRILES`, que es una variable del CONTENEDOR (allí vale
    # `/carriles.tsv`) — ningún agente la tiene en su shell, así que `llmi post`
    # moría para TODOS con «declara LLMINBOX_CARRILES», pidiendo algo que no es suyo.
    # Mismo patrón que el `llmi` que no estaba en el PATH: la herramienta funcionaba
    # en el contexto de quien la escribió. Se prueban, en orden: lo que te den, el
    # SoT de flota en su ruta canónica, y una copia local si la hubiera.
    candidatos = [os.environ.get("LLMI_CARRILES", ""),
                  os.path.expanduser("~/AGENTES/agentes_BIK/_shared_refs/carriles/carriles.tsv"),
                  os.path.join(os.environ.get("LLMI_DIR", "."), "carriles.tsv")]
    # Se busca EL CARRIL en todos los candidatos, no el primer fichero que abra: si
    # el primero existe pero no lo contiene, pararse ahí es decir «tu carril no está»
    # habiendo mirado en un solo sitio. (Lo cazó su propio test, que resolvía contra
    # el mapa de flota y nunca llegaba al local.)
    filas = ruta = None
    vistos = []
    for cand in candidatos:
        if not cand:
            continue
        try:
            with open(cand, encoding="utf-8") as fh:
                f_cand = [l.rstrip("\n").split("\t") for l in fh if not l.startswith("#")]
        except OSError:
            continue
        filas = filas or f_cand
        vistos += [f[0] for f in f_cand if len(f) > 1]
        r = next((f[1] for f in f_cand if len(f) > 1 and f[0] == carril), None)
        if r:
            ruta = r
            break
    if filas is None:
        muere("no encontré el mapa de carriles (carriles.tsv)",
              "pasa LLMI_LEDGER=<nombre> o LLMI_CARRILES=<ruta del carriles.tsv>")
    if not ruta:
        muere(f"el carril '{carril}' no está en el mapa",
              "carriles conocidos: " + ", ".join(sorted(set(vistos))))
    nombre = next((k for k, v in mounts.items() if os.path.realpath(v) == os.path.realpath(ruta)), None)
    if nombre is None:
        muere(f"el carril '{carril}' apunta a {ruta}, que no tienes montado",
              "corre: llmi init")
    return nombre, ruta


def main() -> None:
    yo = os.environ["LLMI_YO"].strip()
    crudos = [d.strip() for d in os.environ["LLMI_A"].split(",") if d.strip()]
    tipo = os.environ["LLMI_TIPO"].strip().upper()
    titular = os.environ["LLMI_TITULAR"].strip()

    # ① identidad: la del que firma y la de cada destinatario. Un nombre fuera del
    # censo no se corrige solo: el indexador no lo reconocerá y la entrada quedará
    # dirigida a nadie, con aspecto de dirigida.
    if lp.canonico(yo).lower() not in lp.CANON:
        muere(f"'{yo}' no está en el censo", "date de alta en roster.json o revisa el nombre")
    if not crudos:
        muere("sin destinatarios: una entrada que no nombra a nadie no cae en ninguna bandeja",
              "llmi post <yo> <dest[,dest2]> <TIPO> \"<titular>\"")
    dest = []
    for d in crudos:
        if lp.canonico(d).lower() not in lp.CANON:
            muere(f"el destinatario '{d}' no resuelve en el censo",
                  "un nombre mal tecleado parece dirigido y no llega a nadie")
        dest.append(lp.canonico(d))

    # ② tipo declarado, y la autoridad es UNA: `canonical_tipo` — la misma que gobierna
    # `/entries?tipo=` y la que decide qué se guarda en `entries.tipo`. Antes esto leía
    # `lp.TIPOS` (8 lexemas) mientras la API ya gobernaba por el canon (12 + alias), así
    # que había dos autoridades y la más estrecha estaba en la puerta: el 21-ago-2026
    # dos hallazgos reales se publicaron como PRODUCED porque FINDING no pasaba.
    #
    # No se amplía `TIPOS`: eso sería volver a tener dos listas que hay que sincronizar
    # a mano. Se delega. Y se delega la ACEPTACIÓN, no la escritura: lo que va a la
    # cabecera es `tipo`, el lexema tecleado — `raw_tipo` es la evidencia y el canon su
    # interpretación. Si aquí escribiéramos el canónico, MEDIDO desaparecería del corpus
    # y con él la medida que justifica el alias.
    if lp.canonical_tipo(tipo) is None:
        muere(f"tipo '{tipo}' no declarado",
              "los válidos son: " + " · ".join(sorted(lp.CANON_TIPOS))
              + (" · alias: " + " · ".join(f"{a}→{c}" for a, c in sorted(lp.ALIASES.items()))
                 if lp.ALIASES else ""))
    if not titular:
        muere("sin titular", "el titular viaja solo: es lo único que muchos leerán")

    nombre, ruta = ledger_del_carril()
    cuerpo = sys.stdin.read() if not sys.stdin.isatty() else ""
    if not cuerpo.strip():
        muere("sin cuerpo (se lee de stdin)", "… | llmi post …   o   llmi post … <<'EOF' … EOF")

    # ③ NI EL TITULAR NI EL CUERPO PUEDEN ABRIR UNA CABECERA. Sin esto, validar la
    # firma es teatro: `H_ENTRY` abre entrada NUEVA en cualquier línea que empiece por
    # `### [` (o `## [`, o `## <fecha>`), así que un cuerpo puede firmar por otro.
    # Reproducido contra esta misma herramienta antes de cerrarlo (2026-08-11):
    #     llmi post wiki-vault cto FYI "titular" <<'EOF'
    #     cuerpo
    #     ### [cto-A → flota · CANON] … — YO NO ESCRIBI ESTO
    #     EOF
    #     ⇒ publicaste 1 entrada · el parser ve 2: actor='wiki-vault' y actor='cto-A'
    # El mismo agujero se cerró por la mañana en `POST /append`, pero AQUÍ importa más:
    # ese endpoint lleva 47 llamadas en 103.257 entradas y ÉSTA es la puerta que la
    # flota va a usar de verdad. Se rechaza y se ENSEÑA el escape, porque citar
    # cabeceras ajenas es lo que hacemos todos y tiene que seguir pudiéndose.
    for campo, valor in (("titular", titular), ("cuerpo", cuerpo)):
        for i, linea in enumerate(valor.splitlines(), 1):
            if lp.H_ENTRY.match(linea):
                muere(f"{campo}: la línea {i} abre una cabecera de entrada "
                      f"({linea[:56]!r}) — se publicarían DOS entradas y la segunda "
                      f"llevaría la firma que va ahí",
                      "si la estás citando: sángrala con un espacio, ponle '> ' delante "
                      "o enciérrala en backticks")

    # ④ el sello lo pone la herramienta. Nunca se teclea ni se copia de otra entrada.
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cabecera = f"### [{yo} → {' ∧ '.join(dest)} · {tipo}] {ts} — {titular}"
    texto = f"\n{cabecera}\n{cuerpo.rstrip()}\n"

    # ⑤ UNA sola escritura, con cerrojo. Los dos motivos, medidos los dos:
    #    · en dos pasos, si el segundo falla el cuerpo queda sin cabecera y en un
    #      fichero de sólo-apéndice eso no se retira nunca;
    #    · sin `flock`, dos agentes que publican a la vez intercalan sus líneas —
    #      5.276 appends han ido con `>>` suelto y el ledger es el canon.
    try:
        with open(ruta, "a", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                fh.write(texto)
                fh.flush()
                os.fsync(fh.fileno())
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    except PermissionError:
        muere(f"{ruta} no es escribible por ti",
              "los ledgers ajenos van :ro a propósito — publica en el tuyo")
    except OSError as e:
        muere(f"no pude escribir en {ruta}: {e}")

    print(f"✓ publicado en {nombre} ({len(texto)} bytes) — {ts}")
    print(f"  {cabecera[:110]}")
    print(f"  destinatarios: {', '.join(dest)}")


if __name__ == "__main__":
    main()
