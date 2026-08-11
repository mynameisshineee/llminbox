"""⑰ censo en escritura — `POST /append` no escribía `actor`/`to` crudos sin

pasarlos por ningún censo: una firma inventada publicaba y quedaba indexada
con `actor=None` (huérfana), justo el bug que ①/② cerraron en LECTURA.

`_indexable()` es deliberadamente MÁS ESTRECHO que `resolver_o_422`/
`canon_identidad`: éstas resuelven también contra `roles-por-alias.json`
(ROLES_ALIAS), que `RE_AGENTE` —el extractor que re-indexará lo escrito—
NO consulta (ver `ledger_parse.py:165-169`). Un gate basado en
`canon_identidad` dejaría pasar un nombre como `sdet` (dado de alta HOY solo
en `roles-por-alias.json`, ausente de `roster.json`) y aun así indexaría con
`actor=None` — reproduciría el bug con el mismo nombre que lo demuestra en
producción. Por eso estos tests NO usan `resolver_o_422` como referencia: el
censo correcto para esta comprobación es `lp.AGENTES` (roster.json), y
`test_mutante_gate_actor_neutralizado_se_ve` (abajo) prueba justo esa
elección de diseño, no solo que "hay un gate".

Cada test afirmativo va con su falsador (T1) — qué se vería si el gate
NO estuviera cerrado.
"""
from __future__ import annotations

import os

from conftest import construir


def test_append_actor_no_censado_422(cliente, servicio):
    """FALSADOR: si el gate no existiera, esto daría 200 y el fichero crecería
    con una firma que RE_AGENTE nunca reconocerá — la huérfana reproducida
    a mano."""
    path = servicio.LEDGERS["demo-ledger"]
    antes = os.path.getsize(path)

    r = cliente.post("/append", json={
        "ledger": "demo-ledger", "actor": "actor-fantasma-xyz",
        "tipo": "FYI", "to": ["backend"], "head": "no debería escribir",
    })

    assert r.status_code == 422
    assert "actor-fantasma-xyz" in r.json()["detail"]
    assert "censo" in r.json()["detail"]
    despues = os.path.getsize(path)
    assert despues == antes


def test_append_actor_censado_ok(cliente, servicio):
    """Round-trip real: no basta con que el POST no falle — la entrada tiene
    que reaparecer en `/entries` con el actor correcto tras un barrido, o el
    texto se escribió mal formado y el 200 es teatro."""
    r = cliente.post("/append", json={
        "ledger": "demo-ledger", "actor": "cto-A",
        "tipo": "FYI", "to": ["backend"], "head": "ronda de prueba ⑰",
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True

    servicio.barrido()
    r2 = cliente.get("/entries", params={"ledger": "demo-ledger", "actor": "cto-A"})
    assert r2.status_code == 200
    cabeceras = [e["head"] for e in r2.json()]
    assert any("ronda de prueba ⑰" in h for h in cabeceras)


def test_append_to_con_fantasma_422(cliente, servicio):
    """FALSADOR: si solo se validara el PRIMER elemento de `to`, este test
    (con el fantasma en 2ª posición) lo pilla y el anterior no."""
    path = servicio.LEDGERS["demo-ledger"]
    antes = os.path.getsize(path)

    r = cliente.post("/append", json={
        "ledger": "demo-ledger", "actor": "cto-A", "tipo": "FYI",
        "to": ["backend", "actor-fantasma-xyz"], "head": "no debería escribir",
    })

    assert r.status_code == 422
    assert "actor-fantasma-xyz" in r.json()["detail"]
    despues = os.path.getsize(path)
    assert despues == antes


def test_append_to_difusion_ok(tmp_path, monkeypatch):
    """Los tokens de difusión (FLOTA/equipo/todos) no son fantasmas — `AGENTES`
    ya incluye `DIFUSION` (`ledger_parse.py:156`), así que `_indexable()` no
    necesita caso especial. FALSADOR: si `_indexable()` se implementara
    excluyendo `DIFUSION` (p.ej. filtrando solo `d.get("agentes")`), esto
    daría 422 sobre un destino legítimo de difusión."""
    roster = {
        "agentes": [
            {"nombre": "backend", "humano": "albert", "clave": "", "rol": "be"},
            {"nombre": "cto-A", "humano": "albert", "clave": "", "rol": "cto"},
        ],
        "humanos": [{"nombre": "albert", "alias": ["Albert"]}],
        "difusion": ["equipo", "FLOTA"],
    }
    s = construir(tmp_path, monkeypatch, roster=roster)
    from fastapi.testclient import TestClient
    with TestClient(s.app) as c:
        s.barrido()
        c.headers.update({"X-Llminbox-Token": "test-token"})
        r = c.post("/append", json={
            "ledger": "demo-ledger", "actor": "cto-A", "tipo": "FYI",
            "to": ["FLOTA"], "head": "aviso de difusión",
        })
        assert r.status_code == 200


def test_mutante_gate_actor_neutralizado_se_ve(cliente, servicio, monkeypatch):
    """Mutación mínima (§5.3, barata): si `_indexable` dejara pasar TODO, el
    caso central (`test_append_actor_no_censado_422`) tendría que teñirse de
    rojo — se simula con monkeypatch (sin tocar producción) y se confirma
    que, bajo el mutante, la firma fantasma SÍ escribe (mismo patrón que
    `test_fail_closed.py:70`, `test_mutante_resolver_neutralizado_se_ve`)."""
    monkeypatch.setattr(servicio, "_indexable", lambda nombre: True)
    path = servicio.LEDGERS["demo-ledger"]
    antes = os.path.getsize(path)

    r = cliente.post("/append", json={
        "ledger": "demo-ledger", "actor": "actor-fantasma-xyz",
        "tipo": "FYI", "to": ["backend"], "head": "con el mutante SÍ escribe",
    })

    assert r.status_code == 200       # con el mutante, ya no cierra en 422
    despues = os.path.getsize(path)
    assert despues > antes            # y el fantasma queda escrito
