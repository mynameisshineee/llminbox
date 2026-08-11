"""El rótulo de sección de /inbox es un CONTRATO con los vigías de la flota.

`── <ledger> · N de M para ti …` no es texto decorativo: al menos 7 scripts de
`~/AGENTES/agentes_BIK/*/agent/tools/` lo parsean con el separador ` · ` PEGADO
al nombre del ledger. El 2026-08-11 metí `(carril: X)` en medio y estuvo 45
minutos desplegado cegando a todos en silencio — el vigía de backend hace
`continue` cuando no casa, o sea deja de mirar su bandeja para siempre.

Los patrones de abajo están COPIADOS de esos scripts (no inventados), con su
ruta, para que quien vuelva a tocar el rótulo vea a quién rompe antes de
mergear. Si un vigía cambia su patrón, este test se actualiza con él; lo que no
puede pasar es que el formato cambie sin que nadie lo note.
"""
from __future__ import annotations

import re

# (etiqueta, patrón tal cual lo usa el script, fichero de origen)
PATRONES_DE_LA_FLOTA = [
    ("backend·awk-seccion", r"^── 64bis-wiki ·",
     "backend-biklabs/agent/tools/ledger-vigia-64bis.sh:48"),
    ("backend·grep-continue", r"^── 64bis-wiki ·",
     "backend-biklabs/agent/tools/ledger-vigia-64bis.sh:141"),
    ("vision-canon·extrae-secciones", r"^── [a-z0-9-]+ · [0-9]+ de [0-9]+",
     "vision-canon/agent/tools/drenar-bandeja.sh:30,81"),
    ("qa·linea-seccion", r"── 64bis-wiki ·",
     "qa-biklabs/agent/tools/vigia-ledger-cockpit.sh:58"),
    ("cfo·sed-total", r".*── 64bis-wiki · [0-9]+ de ([0-9]+) para ti.*",
     "cfo-guardian/agent/tools/ledger-vigia-cfo.sh:45"),
    ("cfo-post·grep-n", r"^── 64bis-wiki · [0-9]+ de",
     "cfo-guardian/agent/tools/cfo-post.sh:402"),
    ("security·sed-de-M", r"^── 64bis-wiki · ([0-9]*) de ([0-9]*) para ti.*",
     "security-biklabs/tools/monitor-ledger-security.sh:120"),
    ("vigia-compartido·seccion", r"^── 64bis-wiki",
     "_shared_refs/tools/ledger-vigia.sh:187"),
    ("fe·seccion-sin-punto", r"── 64bis-wiki",
     "frontend-biklabs/agent/tools/watch-inbox-fe.sh:69"),
]

# El rótulo tal y como lo emite hoy inbox(), con y sin las partes opcionales.
ROTULOS = [
    "── 64bis-wiki · 2 de 116 para ti (lo más reciente · 114 más atrás) · escuchando equipo, FLOTA · carril: 64bis ──",
    "── 64bis-wiki · 2 de 2 para ti (lo más reciente) · carril: 64bis ──",
    "── 64bis-wiki · 5 de 5 para ti (lo más reciente) ──",          # ledger sin carril mapeado
]


def test_todos_los_patrones_de_la_flota_siguen_casando():
    """FALSADOR (el bug real, reproducido): con el rótulo intermedio
    `── 64bis-wiki (carril: 64bis) · …` — el que estuvo 45 min en producción —
    7 de estos 9 patrones dejan de casar. Aquí deben casar los 9, en las tres
    formas del rótulo.
    """
    for rotulo in ROTULOS:
        for etiqueta, patron, origen in PATRONES_DE_LA_FLOTA:
            assert re.search(patron, rotulo), (
                f"ROMPES A {etiqueta} ({origen}) con el rótulo: {rotulo}")


def test_el_rotulo_roto_de_verdad_rompia():
    """Control positivo del test de arriba: si el propio test no supiera
    detectar el formato malo, sería teatro. El rótulo con el carril EN MEDIO
    debe fallar en al menos 7 de los 9 patrones.
    """
    malo = "── 64bis-wiki (carril: 64bis) · 2 de 116 para ti (lo más reciente) ──"
    rotos = [e for e, p, _ in PATRONES_DE_LA_FLOTA if not re.search(p, malo)]
    assert len(rotos) >= 7, f"el control positivo no reproduce el daño: solo {rotos}"


def test_el_servicio_emite_un_rotulo_que_la_flota_parsea(cliente):
    """Y el mismo contrato contra la salida REAL del servicio, no contra una
    cadena escrita a mano en este fichero — el falsador de que los ROTULOS de
    arriba sigan pareciéndose a lo que inbox() emite de verdad.
    """
    texto = cliente.get("/inbox/backend").text
    linea = next(l for l in texto.splitlines() if l.startswith("── demo-ledger"))
    assert re.search(r"^── demo-ledger · [0-9]+ de [0-9]+ para ti", linea), linea
    assert "carril: demo" in linea      # ⑫ sigue vivo, pero fuera del prefijo contractual


# ── Lo que declara @cto (bikeus) que parsea, contestando a mi petición del
#    2026-08-11. Cada entrada aquí viene de SU mensaje, con su ruta de uso, no de
#    lo que yo suponga que consume. Si cambia su parse, se cambia aquí con él.
CONSUMIDORES_DECLARADOS = {
    # `llmi to` / `llmi q` → JSON de /entries. De 10 claves gatea 5.
    "cto·claves-json": ["line_no", "ts", "actor", "head", "to"],
}


def test_entries_conserva_las_claves_que_cto_gatea(cliente):
    """`line_no` es la crítica: la compara contra `grep -n` del fichero para
    verificar POR LÍNEA que su entrada entró en el índice. Si cambia de nombre
    o de base (0 vs 1), él creería que el canal le pierde entradas.

    FALSADOR: renombrar o quitar cualquiera de las 5 pone esto rojo.
    """
    filas = cliente.get("/entries?limit=1").json()
    assert filas, "sin datos no se puede afirmar el contrato"
    for k in CONSUMIDORES_DECLARADOS["cto·claves-json"]:
        assert k in filas[0], f"@cto gatea '{k}' en llmi to/q — ver su mensaje del 11-08"
    assert filas[0]["line_no"] >= 1, "line_no es 1-based: él lo cruza con `grep -n`"


def test_el_banner_ocupa_exactamente_la_linea_1(cliente):
    """@cto lee el rótulo con `sed -n '2p'`, o sea ASUME que el aviso de contenido
    ajeno ocupa la línea 1 y sólo una. Añadir una línea arriba lo rompe en
    silencio: leería una línea de datos como si fuera el rótulo.

    FALSADOR: meter una segunda línea de banner (o quitarlo) desplaza el rótulo
    y esta aserción cae.
    """
    lineas = cliente.get("/inbox/backend").text.splitlines()
    assert lineas[0].startswith("⚠️"), "la línea 1 debe ser el banner de contenido ajeno"
    assert lineas[1].startswith("── "), "la línea 2 debe ser el rótulo: @cto usa sed -n '2p'"


def test_adopcion_json_no_depende_de_columnas(cliente):
    """El parse que @cto declaró como su MÁS FRÁGIL —`grep -E "^   <nombre> "`,
    tres espacios y ancho fijo— ya se rompe hoy: un nombre de 28 caracteres en una
    columna de 22 desalinea la fila, su grep devuelve vacío y él lo lee como «ese
    agente no aparece». Un falso «no existe», silencioso, sobre adopción.

    `formato=json` le da un contrato que no depende de contar espacios.
    FALSADOR: si el JSON perdiera una clave o cambiara de forma, cae aquí.
    """
    d = cliente.get("/adopcion?formato=json").json()
    assert isinstance(d, list)
    if d:
        for k in ("agente", "lecturas", "ultima_lectura", "ledgers_consumidos"):
            assert k in d[0], f"falta '{k}' en el JSON de adopción"
    # y el texto sigue existiendo para quien ya lo usa
    assert "adopción ·" in cliente.get("/adopcion").text
