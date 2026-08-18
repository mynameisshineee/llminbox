"""`/organigrama` no puede servir una verdad organizativa caducada en silencio.

Medido en producción el 2026-08-18: el bind-mount de FICHERO ÚNICO quedó apuntando
a un inodo borrado cuando el host reemplazó el fichero por rename. Resultado: el
endpoint servía 15 roles de hacía dos días —le faltaba `engineering-manager`— y
**el aviso no saltaba**, porque el fichero SÍ se había leído al arrancar: se leyó
el viejo. Todo agente que preguntó «¿a quién reporto?» recibió una realidad vieja.

Dos causas, las dos aquí:
  · `JERARQUIA`/`ROLES_ALIAS` se calculan al IMPORTAR y no se vuelven a mirar.
  · el aviso cubría «ilegible», no «rancio», que son estados distintos.

La invariante que estos tests fijan: **`stale=false` sólo es posible habiendo
leído la fuente en ESA petición y coincidiendo el hash.** Cualquier otro caso
—ilegible, distinta, no montada— es `stale=true`. No hay TTL: un fichero de 6 KB
se hashea por petición y eso cuesta menos que mentir.
"""
from __future__ import annotations

import hashlib
import json

from conftest import construir
from fastapi.testclient import TestClient

ORG_INICIAL = {
    "rol_por_alias": {"backend": "be", "cto-A": "cto"},
    "jerarquia": {
        "cto": {"reporta_a": "ALBERT", "capa": "c-suite"},
        "be": {"reporta_a": "cto", "capa": "ejecucion"},
    },
}


def _monta(tmp_path, monkeypatch, org=None):
    ruta = tmp_path / "roles-por-alias.json"
    ruta.write_text(json.dumps(org if org is not None else ORG_INICIAL))
    s = construir(tmp_path, monkeypatch, extra_env={"LLMINBOX_ROLES_ALIAS": str(ruta)})
    return s, ruta


def _sha(ruta):
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def _org(c):
    r = c.get("/organigrama")
    assert r.status_code == 200, r.text
    return r.json()


def _cliente(s):
    c = TestClient(s.app)
    c.headers.update({"X-Llminbox-Token": "test-token"})
    return c


def test_declara_de_que_bytes_esta_hablando(tmp_path, monkeypatch):
    """Una respuesta organizativa que no dice qué contenido sirve no es
    verificable. El hash servido tiene que ser el del fichero de verdad.

    FALSADOR: sin `loaded_sha256`, no hay forma de distinguir esta respuesta de
    una servida desde memoria hace dos días — que es justo lo que pasó."""
    s, ruta = _monta(tmp_path, monkeypatch)
    with _cliente(s) as c:
        d = _org(c)
    assert d["loaded_sha256"] == _sha(ruta)
    assert d["source_sha256"] == _sha(ruta)
    assert d["stale"] is False
    assert d["cargado_en"]          # nombre ya existente en el contrato


def test_cambiar_la_fuente_se_refleja_sin_reiniciar(tmp_path, monkeypatch):
    """El fallo de producción, exacto: la fuente gana un rol y el endpoint tiene
    que enterarse SIN reinicio.

    FALSADOR: con `JERARQUIA` calculada al importar, el rol nuevo no aparece
    nunca y esta aserción cae — que es el estado de hoy."""
    s, ruta = _monta(tmp_path, monkeypatch)
    with _cliente(s) as c:
        antes = _org(c)
        assert "engineering-manager" not in antes["jerarquia"]

        nuevo = json.loads(json.dumps(ORG_INICIAL))
        nuevo["jerarquia"]["engineering-manager"] = {
            "reporta_a": "cto", "capa": "ejecucion", "estado": "pendiente_arranque"}
        ruta.write_text(json.dumps(nuevo))

        despues = _org(c)
    assert "engineering-manager" in despues["jerarquia"], despues
    assert despues["loaded_sha256"] == _sha(ruta)
    assert despues["loaded_sha256"] != antes["loaded_sha256"]
    assert despues["stale"] is False


def test_reemplazo_por_rename_tambien_se_ve(tmp_path, monkeypatch):
    """La forma EXACTA del fallo: el host no edita en sitio, escribe un fichero
    nuevo y lo renombra encima. Eso cambia el inodo, que es lo que rompió el
    bind-mount y congeló la lectura.

    FALSADOR: una implementación que cachee por inodo o por descriptor abierto
    pasa el test anterior y falla éste."""
    s, ruta = _monta(tmp_path, monkeypatch)
    with _cliente(s) as c:
        _org(c)
        nuevo = json.loads(json.dumps(ORG_INICIAL))
        nuevo["jerarquia"]["sdet"] = {"reporta_a": "cto", "capa": "gate"}
        tmp = ruta.with_suffix(".nuevo")
        tmp.write_text(json.dumps(nuevo))
        tmp.replace(ruta)                      # rename encima: inodo distinto
        d = _org(c)
    assert "sdet" in d["jerarquia"], d
    assert d["stale"] is False


def test_fuente_ilegible_no_puede_decir_stale_false(tmp_path, monkeypatch):
    """La invariante del operador: **nunca** «la fuente cambió · sirvo viejo ·
    stale=false». Si no se puede leer la fuente, no se puede afirmar frescura.

    Se sigue sirviendo lo último bueno —una jerarquía vacía sería peor, el agente
    leería «no reporto a nadie»— pero marcado y con aviso.

    FALSADOR: si `stale` se calculara como «lo cargué alguna vez», aquí saldría
    False y el endpoint estaría afirmando frescura que no puede sostener."""
    s, ruta = _monta(tmp_path, monkeypatch)
    with _cliente(s) as c:
        assert _org(c)["stale"] is False
        ruta.unlink()                          # el mount roto, en su forma pura
        d = _org(c)
    assert d["stale"] is True, d
    assert d["source_sha256"] is None
    assert d["jerarquia"], "se tira la jerarquía buena: peor que servirla marcada"
    assert d["aviso"] and "rancio" in d["aviso"].lower()


def test_la_identidad_se_refresca_con_la_misma_fuente(tmp_path, monkeypatch):
    """El otro lado del mismo fichero, y el que decide de verdad: un alta firmada
    en la fuente debe dejar de dar 422 sin reiniciar el servicio.

    Es el caso `engineering-manager` medido en producción — existía en el
    organigrama y NO tenía identidad: se podía crear un rol incapaz de recibir
    trabajo.

    FALSADOR: `ROLES_ALIAS` congelado al importar mantiene el 422 para siempre."""
    s, ruta = _monta(tmp_path, monkeypatch)
    with _cliente(s) as c:
        assert c.get("/inbox/engineering-manager").status_code == 422

        nuevo = json.loads(json.dumps(ORG_INICIAL))
        nuevo["rol_por_alias"]["engineering-manager"] = "engineering-manager"
        nuevo["jerarquia"]["engineering-manager"] = {"reporta_a": "cto", "capa": "ejecucion"}
        ruta.write_text(json.dumps(nuevo))

        _org(c)                                # la petición que refresca
        assert c.get("/inbox/engineering-manager").status_code != 422


def test_sin_fuente_montada_no_se_finge_frescura(tmp_path, monkeypatch):
    """CONTROL: sin fichero montado el endpoint ya avisaba, y debe seguir
    haciéndolo. Sin este control, un `stale=True` constante pasaría los tests de
    arriba sin medir nada."""
    s = construir(tmp_path, monkeypatch)       # sin LLMINBOX_ROLES_ALIAS
    with _cliente(s) as c:
        d = _org(c)
    assert d["roles"] == 0
    assert d["jerarquia"] == {}
    assert d["aviso"] and "NO montada" in d["aviso"]
    assert d["stale"] is True
