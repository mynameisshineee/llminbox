"""③ cursor con ámbito de carril — `X-Llminbox-Carril` filtra qué CONSUME
`POST /leido`; sin cabecera (o con una que no resuelve), consume TODO como hoy.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import construir, db_directa


def test_carril_filtra_solo_su_ledger(cliente, servicio):
    """FALSADOR: si con el header puesto 'otro-ledger' se escribiera IGUAL, el
    filtro sería decorativo. Se comprueba `cursors` directamente, no sólo el
    JSON de respuesta (que podría mentir).
    """
    r = cliente.post(
        "/inbox/backend/leido",
        json={"hasta": {"demo-ledger": 5, "otro-ledger": 9}},
        headers={"X-Llminbox-Carril": "demo"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["aplicados"] == {"demo-ledger": {"antes": -1, "ahora": 5}}
    assert body["fuera_de_carril"] == ["otro-ledger"]
    assert body["aviso"] is None

    con = db_directa(servicio)
    demo = con.execute(
        "SELECT last_arrival FROM cursors WHERE agent='be' AND ledger='demo-ledger'"
    ).fetchone()
    otro = con.execute(
        "SELECT last_arrival FROM cursors WHERE agent='be' AND ledger='otro-ledger'"
    ).fetchone()
    con.close()
    assert demo["last_arrival"] == 5
    assert otro is None            # NO se tocó — es el falsador literal del filtro


def test_sin_carril_consume_todo_y_avisa(cliente):
    """Conducta ACTUAL preservada: sin cabecera, ambos ledgers se aplican."""
    r = cliente.post(
        "/inbox/backend/leido",
        json={"hasta": {"demo-ledger": 5, "otro-ledger": 9}},
    )
    assert r.status_code == 200
    body = r.json()
    assert set(body["aplicados"]) == {"demo-ledger", "otro-ledger"}
    assert body["fuera_de_carril"] == []
    assert body["aviso"] == "sin carril: consumes TODOS los cursores"


def test_carril_sin_mapa_cae_a_permisivo_y_avisa(cliente, servicio):
    """Un carril que NO está en carriles.tsv (o no cruza con .llmi-mounts.json)
    no filtra nada — mismo comportamiento que sin carril — y lo DICE.

    FALSADOR: si sólo se aplicara UNO de los dos ledgers aquí, habría un filtro
    FANTASMA operando sobre un mapa vacío para ese carril.
    """
    assert "noexiste-en-tsv" not in servicio.CARRIL_LEDGER
    r = cliente.post(
        "/inbox/backend/leido",
        json={"hasta": {"demo-ledger": 5, "otro-ledger": 9}},
        headers={"X-Llminbox-Carril": "noexiste-en-tsv"},
    )
    assert r.status_code == 200
    body = r.json()
    assert set(body["aplicados"]) == {"demo-ledger", "otro-ledger"}
    assert body["fuera_de_carril"] == []
    assert "noexiste-en-tsv" in body["aviso"]


def test_carril_ledger_se_resuelve_de_verdad(servicio):
    """Verify-before-build del propio mapa: 'demo' (definido en el carriles.tsv
    de prueba, cruzado con mounts.json por ruta de host) SÍ resuelve a
    'demo-ledger' — si esto no resolviera, los tres tests de arriba estarían
    probando la rama de fallback permisivo sin saberlo.
    """
    assert servicio.CARRIL_LEDGER.get("demo") == "demo-ledger"


def test_carril_ledger_vacio_por_defecto_sin_mapa(tmp_path, monkeypatch):
    """(F) Camino DEFAULT real del compose: `LLMINBOX_CARRILES=""` y
    `LLMINBOX_MOUNTS_JSON=""` (docker-compose.yml sin override — ver ese
    fichero) ⇒ `CARRIL_LEDGER == {}` y el servicio arranca igual, sin ámbito
    de carril activado en silencio ni excepción al importar.

    FALSADOR: si `_cargar_carriles()` no tolerara las dos rutas vacías (p.ej.
    intentando abrir "" como fichero en vez de cortar por el `if not ruta_*`
    de antes), el import de `servicio` reventaría antes de llegar aquí, o
    `CARRIL_LEDGER` saldría con un mapa fantasma en vez de vacío.
    """
    s = construir(tmp_path, monkeypatch,
                  extra_env={"LLMINBOX_CARRILES": "", "LLMINBOX_MOUNTS_JSON": ""})
    assert s.CARRIL_LEDGER == {}
    with TestClient(s.app) as c:
        s.barrido()
        c.headers.update({"X-Llminbox-Token": "test-token"})
        r = c.get("/inbox/backend")
        assert r.status_code == 200
