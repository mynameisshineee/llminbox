"""⑫ vista actor@carril DERIVADA (idea de Albert vía el hub 2026-08-10T18:08Z).

El carril de una entrada NO se teclea ni se censa: se deriva de su ledger. Aquí
se prueba que el campo existe en /entries, que /inbox lo estampa en el actor y
en el rótulo de sección, y —lo importante— que un ledger SIN carril mapeado no
recibe procedencia inventada.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import construir


def test_entries_trae_carril_derivado(cliente):
    """`demo-ledger` está mapeado al carril `demo` en el carriles.tsv de prueba;
    `otro-ledger` NO está mapeado.

    FALSADOR: si el campo se derivara de otra cosa que el ledger (o se copiara
    del actor), `otro-ledger` traería un carril inventado en vez de None.
    """
    filas = cliente.get("/entries?limit=50").json()
    por_ledger = {f["ledger"]: f["carril"] for f in filas}
    assert por_ledger["demo-ledger"] == "demo"
    assert por_ledger["otro-ledger"] is None, "carril inventado para un ledger sin mapear"


def test_inbox_muestra_actor_arroba_carril(cliente):
    """La vista que pidió Albert: `cto-A@demo`, no `cto-A` a secas.

    FALSADOR: sin la derivación, la línea trae el actor pelado y el `@demo` no
    aparece en ninguna parte del cuerpo.
    """
    texto = cliente.get("/inbox/backend").text
    assert "cto-A@demo" in texto


def test_inbox_rotulo_dice_el_carril(cliente):
    """El rótulo de sección lleva el carril además del ledger — la trampa que
    fe·bikeus reportó (tecleó el nombre del LEDGER como carril porque es lo que
    el rótulo enseñaba) se cierra por la vía de enseñar el valor bueno.

    FALSADOR: con el rótulo viejo (`── demo-ledger · …`), el `(carril: demo)`
    no está y quien lea sigue sin saber qué teclear.
    """
    texto = cliente.get("/inbox/backend").text
    assert "── demo-ledger (carril: demo) ·" in texto


def test_ledger_sin_carril_no_inventa_procedencia(cliente):
    """`otro-ledger` no está mapeado: ni sufijo `@` en el actor ni `(carril: …)`
    en su rótulo. Un `@None` o un `@otro-ledger` serían procedencia fabricada.

    FALSADOR: si `actor_arroba_carril` cayera a `str(None)` o al nombre del
    ledger cuando falta el mapeo, esta aserción lo ve.
    """
    texto = cliente.get("/inbox/backend").text
    seccion = texto.split("── otro-ledger", 1)[1]
    assert "@" not in seccion.split("marcar leído", 1)[0]
    assert "(carril:" not in seccion.split("\n", 1)[0]


def test_sin_mapa_de_carriles_ninguna_vista_cambia(tmp_path, monkeypatch):
    """El default real del compose (sin carriles.tsv montado): la vista vuelve
    exactamente a la de antes de ⑫ — actor pelado, rótulo pelado, y el campo
    `carril` presente pero None. Cero cambio de conducta para quien no monte el
    mapa, que es lo que el REQUEST pedía.
    """
    s = construir(tmp_path, monkeypatch,
                  extra_env={"LLMINBOX_CARRILES": "", "LLMINBOX_MOUNTS_JSON": ""})
    assert s.LEDGER_CARRIL == {}
    with TestClient(s.app) as c:
        s.barrido()
        c.headers.update({"X-Llminbox-Token": "test-token"})
        texto = c.get("/inbox/backend").text
        assert "@" not in texto.split("marcar leído", 1)[0]
        assert "(carril:" not in texto
        assert all(f["carril"] is None for f in c.get("/entries?limit=50").json())
