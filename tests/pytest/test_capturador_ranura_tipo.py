"""La ranura de tipo existe cuando la GRAMÁTICA la tiene, no cuando hay un `·`.

Defecto medido el 2026-08-20: `### [wiki-vault·64bis]` es `agente·carril` —dos
campos, sin ruta— y `raw_tipo_de()` tomaba el último campo igualmente, así que
devolvía el CARRIL como si fuera un tipo. 58 entradas en producción, y `64bis`
llegó a aparecer entre los tipos más frecuentes «fuera de canon», camino de que
alguien lo canonizara.

LA REGLA ES ESTRUCTURAL, y tenía que serlo: mirar si el candidato «parece un
carril» o «parece un agente» no sirve para decidir semántica, y está demostrado
en este mismo corpus — `HARNESS` parece un nombre de agente (lo es) y sin embargo
está legítimamente escrito en la posición de tipo. Un parche del tipo
`if candidato in CARRILES: return None` arreglaría el corpus de hoy y no la
sintaxis.

Las tres gramáticas, y sólo la del medio tiene ranura al final:

    [actor · carril]            → NO hay ranura de tipo
    [actor → destino · TIPO]    → sí la hay
    [TIPO actor → destino]      → tipo FRONTAL (otra rama, `ETIQUETAS`)

El discriminante es el OPERADOR DE RUTA. Sin él la cabecera no está dirigiendo a
nadie, y el último campo es un calificador —carril, sello, nota—, no un tipo.

Medido sobre producción antes de tocar nada: de las capturas de esta rama, 10.512
llevan operador de ruta y **270 no**. De esas 270: `64bis` 58, unos 35 timestamps
(`## [qa-biklabs · 2026-07-18T21:45:15Z]` capturaba la FECHA), nombres de agente y
fragmentos de prosa. El daño colateral aceptado y declarado: algún calificador que
sí parecía un tipo —`TRIAGE-PARKED`, `MÉTODO`— deja de extraerse, porque
estructuralmente no está en una ranura de tipo. El lexema NO se pierde: sigue
entero en `head`, que es de donde se deriva todo esto.
"""
from __future__ import annotations


def _raw(head):
    import ledger_parse as lp
    return lp.raw_tipo_de(head)


def test_agente_carril_sin_ruta_no_produce_el_carril_como_tipo():
    """EL CASO ROJO. `[wiki-vault·64bis]` no dirige a nadie: no hay ranura.

    FALSADOR: con la rama anterior devuelve `'64bis'` — un carril presentado como
    tipo, 58 veces en el corpus vivo.
    """
    assert _raw("### [wiki-vault·64bis] 2026-07-19T09:15:17Z — DONE") is None


def test_una_CONJUNCION_no_acredita_direccion():
    """`∧` y `&` juntan participantes; no dirigen a nadie.

    Mi primera versión de este arreglo usó `OPERADORES_RUTA`, que incluye las dos
    —porque `_es_token_de_tipo` las necesita para OTRA cosa: descartar candidatos
    que sean rutas—. Con eso, `[wiki-vault ∧ qa · 64bis]` volvía a dar `64bis`:
    maté una forma del defecto y dejé viva su variante, reutilizando una constante
    cuya semántica es más ancha que «flecha». Lo cazó el operador.

    FALSADOR: volver a `OPERADORES_RUTA` en `_dirigida` resucita las dos.
    """
    assert _raw("### [wiki-vault ∧ qa · 64bis] 2026-08-20T10:00Z — algo") is None
    assert _raw("### [wiki-vault & qa · 64bis] 2026-08-20T10:00Z — algo") is None


def test_una_conjuncion_JUNTO_a_una_flecha_si_dirige():
    """CONTROL: el caso mayoritario del corpus lleva las dos cosas —una flecha y
    varias conjunciones— y tiene que seguir extrayendo.

    FALSADOR: una regla que RECHACE la presencia de `∧` en vez de exigir flecha
    tira los miles de envíos multidestinatario.
    """
    assert _raw("### [db-mig → security ∧ qa ∧ cto · MEASURED] 2026-08-20T10:00Z — algo") == "MEASURED"


def test_con_ruta_el_ultimo_campo_SI_es_el_tipo():
    """CONTROL ①: la gramática dirigida conserva su ranura, y con un valor que
    ADEMÁS es nombre de agente — para que quede claro que la regla no mira el
    parecido del candidato.

    FALSADOR: una regla que exija que el tipo «no parezca un agente» rompe esto.
    """
    assert _raw("### [harness → sdet · HARNESS] 2026-08-19T09:35Z — algo") == "HARNESS"


def test_con_ruta_y_tipo_normal_sigue_igual():
    """CONTROL ②: el caso mayoritario, 10.512 capturas, no se mueve."""
    assert _raw("### [marketing → marketing · WAKE] 2026-08-11T16:43:05Z — algo") == "WAKE"


def test_el_tipo_FRONTAL_no_lo_toca_esta_regla():
    """CONTROL ③: `[TIPO actor → destino]` va por `ETIQUETAS`, otra rama.

    FALSADOR: gatear la rama equivocada tira los 21.574 HEARTBEAT y compañía —
    medido: 22.082 capturas vienen de cabeceras sin operador de ruta, y la
    inmensa mayoría son tipos FRONTALES que esta regla no debe rozar.
    """
    assert _raw("### [RESP marketing → bikeus] 2026-08-05T22:33:44Z — algo") == "RESP"
    assert _raw("### [HEARTBEAT bikeus] 2026-07-30T11:36:09Z — leí el ledger") == "HEARTBEAT"


def test_el_sello_de_fecha_deja_de_leerse_como_tipo():
    """El otro cuerpo de la basura: `[agente · <ISO>]` capturaba la FECHA.

    FALSADOR: sin la regla devuelve el timestamp como raw_tipo (~35 entradas).
    """
    assert _raw("## [qa-biklabs · 2026-07-18T21:45:15Z] Fechar el puntero") is None
