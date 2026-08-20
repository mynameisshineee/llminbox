"""`tipo` pasa a ser VERDAD GLOBAL derivada del lexema, sin excepciones históricas.

#15 introdujo el mecanismo y fue estrictamente aditiva: rellenó huecos y no tocó
ninguna fila con valor. Eso dejó la columna a medias — 29.708 filas de 68.822
seguían diciendo algo que su lexema no sostiene, porque el matcher por subcadena
las clasificó desde la PROSA.

Medido antes de escribir el diff:

    tipo → NULL ......... 29.414   HEARTBEAT 21.630 · FYI 4.943 · ACK 1.039 · …
    tipo → OTRO tipo .......  294   FYI→RESP 112 · FYI→ACK 67 · ACK→RESP 29 · …
    NULL → tipo ............... 0   (#15 ya los rellenó)

Las 294 sustituciones son falsos positivos corrigiéndose: `FYI → RESP` son
entradas cuyo lexema real es `RESP` y a las que el matcher puso `FYI` porque la
palabra aparecía en el texto.

LA AUTORIDAD ES `raw_tipo`, aunque eso signifique PERDER clasificación derivada
históricamente. Una entrada sin lexema no tiene tipo, por mucho que alguien se lo
adivinara antes.
"""
from __future__ import annotations


def _sanea(tmp_path, monkeypatch, filas):
    """Siembra (tipo, raw_tipo) a mano y corre el saneamiento. Devuelve el después."""
    from fastapi.testclient import TestClient
    from conftest import construir, db_directa
    s_ = construir(tmp_path, monkeypatch)
    (tmp_path / "DEMO-LEDGER.md").write_text(
        "".join(f"### [cto-A → backend · X{i}] 2026-08-20T10:0{i}:00Z — sembrada {i}\n\ncuerpo\n"
                for i in range(len(filas))))
    with TestClient(s_.app):
        s_.barrido()
    con = db_directa(s_)
    eids = [r["eid"] for r in con.execute("SELECT eid FROM entries ORDER BY seq")]
    assert len(eids) >= len(filas), "no se sembraron suficientes entradas"
    for eid, (tipo, raw) in zip(eids, filas):
        con.execute("UPDATE entries SET tipo=?, raw_tipo=? WHERE eid=?", (tipo, raw, eid))
    con.execute("DELETE FROM meta WHERE k='canon_v'")
    con.commit()
    s_.migrar_canon(con)
    ver = db_directa(s_)
    return [dict(ver.execute("SELECT tipo, raw_tipo FROM entries WHERE eid=?", (e,)).fetchone())
            for e in eids[:len(filas)]]


def test_la_autoridad_es_el_lexema_aunque_se_pierda_clasificacion(tmp_path, monkeypatch):
    """Los cuatro casos que definen el contrato.

    FALSADOR: cualquier `old or new`, o una excepción para HEARTBEAT, rompe uno.
    """
    d = _sanea(tmp_path, monkeypatch, [
        ("FYI", "RESP"),            # ① falso positivo de prosa → se corrige al lexema
        ("ACK", None),              # ② sin lexema NO hay tipo, aunque lo tuviera
        ("HEARTBEAT", "HEARTBEAT"), # ③ fuera del canon → NULL
        ("FYI", "MEDIDO"),          # ④ alias adjudicado
    ])
    assert d[0]["tipo"] == "RESP", d[0]
    assert d[1]["tipo"] is None, f"rescató una clasificación sin evidencia lexical: {d[1]}"
    assert d[2]["tipo"] is None, d[2]
    assert d[3]["tipo"] == "MEASURED", d[3]
    # y el lexema, BYTE-IDÉNTICO en los cuatro
    assert [x["raw_tipo"] for x in d] == ["RESP", None, "HEARTBEAT", "MEDIDO"]


def test_la_invariante_final_no_admite_excepciones(tmp_path, monkeypatch):
    """`tipo IS NULL OR tipo ∈ CANON_TIPOS`, cero filas fuera.

    FALSADOR: preservar cualquier valor histórico deja HEARTBEAT dentro y cae.
    """
    import ledger_parse as lp
    d = _sanea(tmp_path, monkeypatch, [
        ("HEARTBEAT", "HEARTBEAT"), ("DONE", "DONE"), ("CLAIM", "CLAIM"),
        ("MSG", "MSG"), ("FYI", None), ("ACK", "ADJUDICADO"),
    ])
    fuera = [x for x in d if x["tipo"] is not None and x["tipo"] not in lp.CANON_TIPOS]
    assert fuera == [], f"quedaron tipos fuera del canon: {fuera}"


# ── el contrato de la API: `tipo` gobernado, `raw_tipo` legacy ────────────────

def test_un_tipo_no_canonico_FALLA_en_vez_de_devolver_vacio(cliente):
    """`?tipo=HEARTBEAT` devolvía filas; tras el saneamiento devolvería `[]`.

    Y `[]` es la peor respuesta posible: un cliente antiguo lo lee como «no hay
    latidos» cuando significa «tu consulta ya no es válida bajo este contrato».
    Es la rotura silenciosa que llevamos toda la semana quitando de otros sitios.

    Si `tipo` es vocabulario GOBERNADO, el endpoint tiene que hacerlo cumplir.

    FALSADOR: devolver `[]` en vez de 422 hace que las dos aserciones caigan.
    """
    r = cliente.get("/entries?tipo=HEARTBEAT")
    assert r.status_code == 422, f"{r.status_code}: {r.text[:120]}"
    d = r.json()
    assert "raw_tipo" in str(d), d          # dice DÓNDE mirar
    assert "HEARTBEAT" in str(d), d         # y qué valor rechazó


def test_el_alias_se_normaliza_tambien_en_el_filtro(cliente):
    """`?tipo=MEDIDO` → `MEASURED`: un único normalizador gobierna almacenamiento
    Y filtro, o la API contradice a la base.

    FALSADOR: un filtro que compare crudo devuelve 0 para `MEDIDO`, porque en la
    base ya está guardado como `MEASURED`.
    """
    assert cliente.get("/entries?tipo=MEDIDO").status_code == 200
    assert cliente.get("/entries?tipo=medido").status_code == 200   # y sin caja


def test_raw_tipo_es_el_filtro_del_protocolo_legacy(tmp_path, monkeypatch):
    """`?raw_tipo=HEARTBEAT` encuentra los latidos AUNQUE `tipo` sea NULL.

    Es la vía de salida que el 422 recomienda: sin ella, decirle a un cliente «usa
    raw_tipo» sería mandarlo a un parámetro que no existe.

    FALSADOR: sin el filtro nuevo, la primera aserción da 0; si el filtro mirara
    `tipo`, también.
    """
    from fastapi.testclient import TestClient
    from conftest import construir, db_directa
    s_ = construir(tmp_path, monkeypatch)
    (tmp_path / "DEMO-LEDGER.md").write_text(
        "### [HEARTBEAT cto-A] 2026-08-20T10:00:00Z — latido uno\n\ncuerpo\n")
    c = TestClient(s_.app)
    c.headers.update({"X-Llminbox-Token": "test-token"})
    with c:
        s_.barrido()
        con = db_directa(s_)
        assert con.execute("SELECT tipo FROM entries WHERE raw_tipo='HEARTBEAT'").fetchone()["tipo"] is None
        d = c.get("/entries?raw_tipo=HEARTBEAT").json()
        assert len(d) >= 1, "el filtro por lexema no encuentra el latido"
        assert d[0]["raw_tipo"] == "HEARTBEAT"    # devuelve el literal, sin normalizar
        # búsqueda sin caja, pero el valor guardado NO se toca
        assert len(c.get("/entries?raw_tipo=heartbeat").json()) >= 1
