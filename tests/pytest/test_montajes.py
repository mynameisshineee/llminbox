"""Ningún bind-mount de FICHERO ÚNICO en la composición de Docker.

Nace de un fallo de producción del 2026-08-18 y de su repetición evitada:

`roles-por-alias.json` estaba montado como fichero suelto. El host lo reemplazó
por rename —que es como se DEBE escribir un fichero de forma atómica: tmp + mv—,
el bind-mount se quedó clavado al INODO borrado, y `/organigrama` sirvió DOS DÍAS
un organigrama viejo sin avisar. Nadie lo notó porque el fallo no da error: da
datos, y son plausibles.

El repo ya arrastraba la cicatriz vecina, documentada en el propio compose: si el
fichero NO existe antes de `docker compose up`, Docker lo sustituye en silencio
por un DIRECTORIO vacío. Dos formas del mismo filo: **montar un fichero suelto ata
el contenedor a un inodo que el host puede jubilar en cualquier momento.**

Un mount de DIRECTORIO no tiene el problema: la resolución del nombre se rehace en
cada `open()`, así que un rename encima se ve inmediatamente.

Esto es la invariante, no el recordatorio. Un comentario pide que alguien se
acuerde; un test falla solo cuando alguien no se acuerda.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
COMPOSES = ("docker-compose.yml", "docker-compose.override.yml")

# Extensiones que delatan un FICHERO. Se mira la SINTAXIS y no el disco a
# propósito: en CI las rutas del host no existen, y un guarda que sólo funciona
# en la máquina de uno no guarda nada.
EXT_DE_FICHERO = (".json", ".tsv", ".md", ".yml", ".yaml", ".txt", ".env",
                  ".sqlite", ".db", ".sh", ".py", ".token", ".log", ".csv")


# Exenciones CON MOTIVO. Una lista de excepciones que crece en silencio es como
# muere un guarda, así que: cada entrada dice por qué, y el test comprueba que
# SIGUE casando con algo — una exención que ya no aplica es deuda invisible.
EXENTOS = {
    "/ledgers/": (
        "los LEDGERS. Corren el mismo riesgo y NO se arregla montando su "
        "directorio: cada uno vive en la raíz de un repo distinto y montarlos "
        "expondría nueve proyectos enteros dentro del contenedor. La exención se "
        "apoya en una disciplina REAL —el ledger es append-only y se escribe con "
        "`>>` en sitio, nunca con tmp+mv—, así que el inodo no cambia. Pero es "
        "una disciplina, no un mecanismo: si alguien reescribe un ledger de forma "
        "atómica, el contenedor leerá bytes muertos sin un solo error. Queda "
        "abierto y anotado para v0.3.1; no se cierra a base de olvidarlo."),
}


def _exento(destino: str) -> str | None:
    return next((m for pre, m in EXENTOS.items() if destino.startswith(pre)), None)


def _montajes(texto: str):
    """(origen, destino) de cada línea de volumen. Ignora volúmenes nombrados."""
    for linea in texto.splitlines():
        m = re.match(r'\s*-\s*"?([^":]+):([^":]+?)(?::(ro|rw))?"?\s*$', linea)
        if not m:
            continue
        origen, destino = m.group(1).strip(), m.group(2).strip()
        if "/" not in origen and "." not in origen:
            continue                      # volumen nombrado (`llminbox-data:/data`)
        yield origen, destino


def test_ningun_bind_mount_de_fichero_unico():
    """El falsador de la clase entera.

    FALSADOR: devolver `- ./roster.json:/censo.json:ro` pone esto rojo con el
    nombre del fichero. Es exactamente el montaje que rompió el organigrama, una
    tabla más allá."""
    culpables = []
    for nombre in COMPOSES:
        ruta = RAIZ / nombre
        if not ruta.exists():
            continue                      # el override es local, puede no estar
        for origen, destino in _montajes(ruta.read_text()):
            if origen.lower().endswith(EXT_DE_FICHERO) and not _exento(destino):
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
    modo de fallo más caro de este repo y tiene su propia cicatriz.

    Se exige que encuentre montajes reales y que reconozca el de directorio que
    sustituyó al que falló."""
    vistos = []
    for nombre in COMPOSES:
        ruta = RAIZ / nombre
        if ruta.exists():
            vistos += list(_montajes(ruta.read_text()))
    assert len(vistos) >= 2, f"el parser no ve los volúmenes: {vistos}"
    assert any(d.startswith("/") and not o.lower().endswith(EXT_DE_FICHERO)
               for o, d in vistos), f"no reconoce ningún mount de directorio: {vistos}"


def test_las_exenciones_siguen_aplicando():
    """CONTROL de la lista de excepciones. Una exención que ya no casa con nada es
    deuda invisible: parece que cubre un riesgo y no cubre ninguno, y el día que
    alguien reintroduzca ese montaje la exención lo tapará sin que nadie lo note.

    FALSADOR: cuando los ledgers dejen de montarse como fichero —que es el
    objetivo—, este test se pone rojo y obliga a RETIRAR la exención en vez de
    dejarla ahí de adorno."""
    usadas = set()
    for nombre in COMPOSES:
        ruta = RAIZ / nombre
        if not ruta.exists():
            continue
        for origen, destino in _montajes(ruta.read_text()):
            if origen.lower().endswith(EXT_DE_FICHERO):
                for pre in EXENTOS:
                    if destino.startswith(pre):
                        usadas.add(pre)
    huerfanas = set(EXENTOS) - usadas
    assert not huerfanas, (
        f"exenciones que ya no cubren nada: {sorted(huerfanas)} — retíralas de "
        "EXENTOS en vez de dejarlas tapando un riesgo que ya no existe")


CANARIO = '      - "./roster.json:/censo.json:ro"\n'


def test_el_canario_siempre_se_caza():
    """El guarda de la lista de exenciones, que es donde se muere un guarda.

    Una exención puede ensancharse hasta tragárselo todo —basta con que su
    prefijo sea `/`— y entonces el test principal pasa siempre: verde por no
    mirar. El mutante que lo hacía sobrevivía, así que el hueco era real.

    El canario es el montaje EXACTO que rompió el organigrama. Si el conjunto de
    exenciones deja de cazarlo, es que ya no caza nada.

    FALSADOR: ensanchar cualquier exención a `/` (o vaciar `EXT_DE_FICHERO`)
    pone esto rojo antes de que nadie reintroduzca el montaje de verdad."""
    origen, destino = next(_montajes(CANARIO))
    assert origen.lower().endswith(EXT_DE_FICHERO), origen
    assert _exento(destino) is None, (
        f"una exención se tragó el canario ({origen} → {destino}): el guarda ya "
        "no protege de nada. Acota el prefijo de EXENTOS.")
