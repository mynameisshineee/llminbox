"""⑦a — rename `seq`→`arrival_hasta` en `marcar_leido`: higiene de nombre, CERO
cambio de comportamiento. El propio nombre del parámetro no es observable desde
fuera de la función (el contrato JSON sigue siendo `{"hasta": {ledger: int}}`),
así que el falsador real es: todo lo que ya pasaba en ①/③ sobre `POST /leido`
sigue pasando exactamente igual — mismos valores de `aplicados`/`retrocedidos`/
`sin_cambio`.

FALSADOR: si algún test de ① o ③ EMPEZARA a fallar sólo por este cambio, no era
un rename — alguien cambió semántica además del nombre, y eso no estaba pedido.
"""
from __future__ import annotations

from conftest import db_directa


def test_avanzar_retroceder_sin_cambio_conserva_semantica(cliente, servicio):
    """Recorre las tres ramas (avanza / retrocede / sin cambio) que ya existían
    ANTES del rename y comprueba que el contrato de la respuesta no se movió.
    """
    r1 = cliente.post("/inbox/backend/leido", json={"hasta": {"demo-ledger": 50}})
    assert r1.status_code == 200
    b1 = r1.json()
    assert b1["aplicados"]["demo-ledger"] == {"antes": -1, "ahora": 50}
    assert b1["retrocedidos"] == {}
    assert b1["sin_cambio"] == []

    r2 = cliente.post("/inbox/backend/leido", json={"hasta": {"demo-ledger": 50}})
    b2 = r2.json()
    assert b2["aplicados"]["demo-ledger"] == {"antes": 50, "ahora": 50}
    assert b2["sin_cambio"] == ["demo-ledger"]
    assert b2["retrocedidos"] == {}

    r3 = cliente.post("/inbox/backend/leido", json={"hasta": {"demo-ledger": 10}})
    b3 = r3.json()
    assert b3["aplicados"]["demo-ledger"] == {"antes": 50, "ahora": 10}
    assert b3["retrocedidos"] == {"demo-ledger": {"vuelven_a_verse": 40}}

    con = db_directa(servicio)
    fila = con.execute(
        "SELECT last_arrival FROM cursors WHERE agent='be' AND ledger='demo-ledger'"
    ).fetchone()
    con.close()
    assert fila["last_arrival"] == 10
