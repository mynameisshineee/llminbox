"""Nada de lo que la flota escribe en la posición del tipo se descarta.

Medido el 2026-08-18 sobre el ledger piloto: **641 entradas (8,2 %) llevan un tipo
escrito en posición canónica que el parser TIRA**, porque `TIPOS` es un tuple
cerrado de 8 y `publicar.py` rechaza cualquier otro. `MEDIDO` (339), `MEASURED`
(105), `ADJUDICADO` (75), `VEREDICTO` (27)… La flota los escribe en el sitio
correcto y el lector los convierte en «sin tipo».

Eso rompe dos cosas a la vez: `lint` los cuenta como «no declaran nada» cuando
declaran de sobra, y cualquier instrumento que clasifique tráfico por tipo mide
sobre un corpus mutilado.

**Sólo preservación, no interpretación** (ruling del operador): se guarda el texto
literal. `canonical_kind` y `kind_registry_rev` se crean YA pero quedan NULL —
existen para que el día que se interprete quede registrado CON QUÉ revisión del
registro se hizo. Sin ese campo, cambiar la taxonomía cambiaría en silencio las
métricas históricas.
"""
from __future__ import annotations

from conftest import construir, db_directa
from fastapi.testclient import TestClient

CABECERAS = (
    "### [cto-A → backend · FYI] canónica\ncuerpo\n"          # de los 8
    "### [cto-A → backend · MEDIDO] desconocida\ncuerpo\n"     # escrita y hoy tirada
    "### [cto-A → backend · ADJUDICADO] otra\ncuerpo\n"
    "### [cto-A → backend] sin tipo ninguno\ncuerpo\n"
)


def _monta(tmp_path, monkeypatch):
    s = construir(tmp_path, monkeypatch)
    (tmp_path / "DEMO-LEDGER.md").write_text(CABECERAS)
    with TestClient(s.app) as c:
        s.barrido()
        c.headers.update({"X-Llminbox-Token": "test-token"})
        yield_con = db_directa(s)
    return s, yield_con


def _filas(con):
    return {r["head"].split("]")[0].split()[-1] if "·" in r["head"] else "SIN":
            (r["tipo"], r["raw_tipo"], r["canonical_kind"], r["kind_registry_rev"])
            for r in con.execute("SELECT head,tipo,raw_tipo,canonical_kind,"
                                 "kind_registry_rev FROM entries WHERE ledger='demo-ledger'")}


def test_un_tipo_desconocido_se_conserva_literal(tmp_path, monkeypatch):
    """El caso de los 641: `MEDIDO` está escrito, luego `MEDIDO` se guarda.

    FALSADOR: hoy `raw_tipo` no existe; con la columna pero sin capturar, sale
    NULL y esta aserción cae — que es exactamente el descarte silencioso."""
    s, con = _monta(tmp_path, monkeypatch)
    f = _filas(con)
    assert f["MEDIDO"][1] == "MEDIDO", f
    assert f["ADJUDICADO"][1] == "ADJUDICADO", f


def test_no_se_interpreta_nada_todavia(tmp_path, monkeypatch):
    """El límite del ruling: preservar sí, interpretar no. `MEDIDO` NO se
    convierte en `MEASUREMENT` aquí, y `tipo` sigue sin inventarse.

    FALSADOR: si alguien cablea el registro canónico antes de tiempo, o mete el
    literal en `tipo`, esto se pone rojo — y con razón: `tipo` es el vocabulario
    que el sistema entiende, y ensancharlo por la puerta de atrás haría pasar por
    canónico lo que nadie ha aprobado."""
    s, con = _monta(tmp_path, monkeypatch)
    f = _filas(con)
    assert f["MEDIDO"][0] is None, "se coló en `tipo`: eso es interpretar"
    assert f["MEDIDO"][2] is None and f["MEDIDO"][3] is None
    assert f["FYI"][2] is None, "canonical_kind se rellena antes de tener registro"


def test_el_canonico_tambien_deja_su_literal(tmp_path, monkeypatch):
    """`raw_tipo` es «lo que estaba escrito», sin excepciones. Que coincida con
    `tipo` en los 8 canónicos no lo hace redundante: hace que la partición del
    corpus se pueda calcular en SQL sin casos especiales."""
    s, con = _monta(tmp_path, monkeypatch)
    f = _filas(con)
    assert f["FYI"] [:2] == ("FYI", "FYI"), f


def test_sin_tipo_escrito_no_se_inventa_uno(tmp_path, monkeypatch):
    """CONTROL NEGATIVO, y es el que hace que los de arriba signifiquen algo: una
    entrada que NO declara nada tiene que salir con los cuatro campos vacíos. Sin
    esto, una implementación que rellenara `raw_tipo` con cualquier cosa pasaría
    los tres tests anteriores."""
    s, con = _monta(tmp_path, monkeypatch)
    assert _filas(con)["SIN"] == (None, None, None, None)


HUELLA_ESPERADA = "e7f6c011776e8db7"      # SCHEMA_V = 6


def test_la_huella_de_esquema_sigue_siendo_la_misma():
    """EL GUARDA DE VERDAD, y nació de que el anterior era teatro.

    Escribí primero un test que arrancaba el servicio dos veces contra la misma
    base y comprobaba que el cursor sobrevivía. Pasaba con el mutante «sube
    SCHEMA_V» puesto — porque sube en LAS DOS arrancadas, así que nunca hay
    transición vieja→nueva, que es exactamente lo que sí ocurre al desplegar.
    Medía «dos arranques de la misma versión», no «versión nueva sobre base
    existente». Cazado corriendo el mutante, no leyéndolo.

    Lo que decide de verdad si a los 20 agentes se les borra la posición de
    lectura es UN valor: `huella_esquema()`. Así que se fija.

    FALSADOR: subir `SCHEMA_V` o meter una columna en `SCHEMA` pone esto rojo.
    Si eso es lo que quieres, súbelo aquí a la vez — pero entonces estás
    decidiendo, con nombre y apellidos, tirar `cursors` en el próximo despliegue.
    """
    import servicio
    assert servicio.huella_esquema() == HUELLA_ESPERADA, (
        "la huella de esquema cambió: el próximo arranque TIRA `cursors` y los 20 "
        "agentes ven su bandeja llena otra vez. Si la columna es aditiva, va en "
        "COLUMNAS_ANADIDAS (no toca la huella). Si de verdad cambia la FORMA de "
        "una tabla, actualiza HUELLA_ESPERADA a propósito.")


def test_una_huella_distinta_si_borra_los_cursores(tmp_path, monkeypatch):
    """CONTROL del anterior: prueba que la huella guarda algo REAL. Con la base
    sellada a una huella vieja, el arranque tira `cursors` — comportamiento
    documentado y correcto. Sin este control, el pin de arriba podría estar
    fijando un número que no gobierna nada."""
    s = construir(tmp_path, monkeypatch)
    with TestClient(s.app) as c:
        s.barrido()
        c.headers.update({"X-Llminbox-Token": "test-token"})
        c.post("/inbox/backend/leido", json={"hasta": {"demo-ledger": 1}})
    con = db_directa(s)
    assert con.execute("SELECT COUNT(*) c FROM cursors").fetchone()["c"] > 0
    con.execute("INSERT OR REPLACE INTO meta VALUES ('schema_v', 'huella-vieja')")
    con.commit()

    s2 = construir(tmp_path, monkeypatch)
    with TestClient(s2.app) as c2:
        s2.barrido()
    assert db_directa(s2).execute(
        "SELECT COUNT(*) c FROM cursors").fetchone()["c"] == 0, (
        "la huella no gobierna nada: el pin de arriba no protege de nada")


def test_las_tres_columnas_existen_tras_reiniciar(tmp_path, monkeypatch):
    """Que la vía aditiva llegue de verdad a la tabla: `executescript(SCHEMA)`
    con `IF NOT EXISTS` NO añade columnas a una tabla que ya existe — es la
    cicatriz de `coste.maximo`. El ALTER tiene que correr en cada arranque."""
    s = construir(tmp_path, monkeypatch)
    with TestClient(s.app) as c:
        s.barrido()
    s2 = construir(tmp_path, monkeypatch)
    with TestClient(s2.app) as c2:
        s2.barrido()
    cols = {r[1] for r in db_directa(s2).execute("PRAGMA table_info(entries)")}
    assert {"raw_tipo", "canonical_kind", "kind_registry_rev"} <= cols, cols


def test_lint_separa_no_declarar_de_declarar_algo_que_no_entiendo(tmp_path, monkeypatch):
    """Son dos deudas distintas y hoy se cuentan como una. «No declara nada» se
    arregla enseñando a escribir; «declara algo que no entiendo» se arregla
    ampliando el registro — o cerrando el camino por el que entró.

    FALSADOR: con el `tipo IS NULL` de antes, las dos filas caen en el mismo saco
    y el desglose no existe."""
    s, _ = _monta(tmp_path, monkeypatch)
    with TestClient(s.app) as c:
        c.headers.update({"X-Llminbox-Token": "test-token"})
        txt = c.get("/lint").text
    assert "declara un tipo que no entiendo" in txt, txt
    linea = next(l for l in txt.splitlines() if "no entiendo" in l)
    assert "2" in linea, linea            # MEDIDO y ADJUDICADO
    sin = next(l for l in txt.splitlines() if "sin tipo declarado" in l)
    assert "1" in sin, sin                # sólo la que no declara nada
