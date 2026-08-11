"""Un índice que no se deja escribir DEGRADA, no mata el arranque.

Hallazgo del arnés de humo de @qa (run 31481815502, 2026-08-11): con el índice
dañado, el servicio se curaba —«base nueva en su sitio · 1 cursores rescatados»—
y moría a continuación escribiendo `meta('parser_v')`:

    sqlite3.OperationalError: attempt to write a readonly database
    ERROR: Application startup failed. Exiting.

⇒ contenedor `exited`, la flota sin bandeja, por no poder escribir un CONTADOR
DE VERSIÓN. La promesa del producto es la contraria: el markdown es el canon y
esto es un atajo que no puede dejar a nadie esperando.
"""
from __future__ import annotations

import os
import stat

import pytest
from fastapi.testclient import TestClient

from conftest import construir


def _solo_lectura(ruta_db: str):
    """Deja la BD y su directorio sin permiso de escritura para el usuario.

    El directorio TAMBIÉN: SQLite necesita crear `-wal`/`-journal` al lado, así
    que sin esto la base sigue siendo escribible por la puerta de al lado y el
    test mediría otra cosa.
    """
    d = os.path.dirname(ruta_db)
    os.chmod(ruta_db, stat.S_IRUSR)
    os.chmod(d, stat.S_IRUSR | stat.S_IXUSR)
    return d


def _restaurar(d: str, ruta_db: str):
    os.chmod(d, stat.S_IRWXU)
    os.chmod(ruta_db, stat.S_IRUSR | stat.S_IWUSR)


@pytest.fixture
def servicio_ro(tmp_path, monkeypatch):
    """Un índice YA construido y poblado, que después se vuelve de sólo lectura."""
    s = construir(tmp_path, monkeypatch)
    with TestClient(s.app) as c:          # arranque normal: crea esquema e indexa
        s.barrido()
        c.headers.update({"X-Llminbox-Token": "test-token"})
        assert c.get("/inbox/backend").status_code == 200
    ruta = os.environ["LLMINBOX_DB"]
    d = _solo_lectura(ruta)
    yield s
    _restaurar(d, ruta)


def test_arranca_con_indice_no_escribible(servicio_ro):
    """EL FALSADOR DEL BUG, tal cual lo vio el humo: el arranque no puede morir.

    Sin la cura, este `with` levanta OperationalError («attempt to write a
    readonly database») desde el lifespan y el test se pone rojo — que es lo que
    en producción se ve como `Application startup failed. Exiting`.
    """
    with TestClient(servicio_ro.app) as c:
        c.headers.update({"X-Llminbox-Token": "test-token"})
        assert c.get("/health").status_code == 200


def test_sigue_sirviendo_las_bandejas(servicio_ro):
    """Y sirve para lo que existe: leer. Arrancar y no servir sería la misma
    indisponibilidad con mejor cara."""
    with TestClient(servicio_ro.app) as c:
        c.headers.update({"X-Llminbox-Token": "test-token"})
        r = c.get("/inbox/backend")
        assert r.status_code == 200
        assert "primera" in r.text, "arrancó pero la bandeja vino vacía"


def test_health_no_da_verde_y_nombra_el_motivo(servicio_ro):
    """Vivo ≠ sano. Quien lea `ok:true` daría por drenado lo que no se drenó.

    FALSADOR: si `ok` siguiera saliendo `true` con el índice en sólo lectura,
    el healthcheck del contenedor diría verde sobre un servicio que no avanza
    cursores — el «verde impecable sobre un servicio ciego» que este repo ya
    documenta como su clase de fallo favorita.
    """
    with TestClient(servicio_ro.app) as c:
        c.headers.update({"X-Llminbox-Token": "test-token"})
        d = c.get("/health").json()
        assert d["ok"] is False
        assert d["solo_lectura"], "no dice el motivo: un rojo mudo no se puede depurar"
        assert "readonly" in d["solo_lectura"].lower() or "read-only" in d["solo_lectura"].lower()
        assert "cursores NO" in d["aviso"]


def test_indice_escribible_no_toca_nada(cliente):
    """Control positivo: en el camino normal la cura NO se enciende sola.

    ⚠️ Aquí NO se puede asertar `ok is True`, y la primera versión de este test lo
    hacía y fallaba por su culpa, no por el producto: `sano` cuelga de que el
    VIGILANTE haya completado un barrido, y el arnés lo sustituye por un no-op
    (`conftest.construir`) para que el indexado sea síncrono y determinista. Lo
    que este control puede afirmar de verdad es que el modo degradado no se
    activa por su cuenta — que es la mitad que la cura podría romper.
    """
    d = cliente.get("/health").json()
    assert d["solo_lectura"] is None
    assert d["aviso"] is None            # ni rastro del aviso de sólo lectura
    assert d["indexador"]["error"] is None
