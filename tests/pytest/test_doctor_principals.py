"""⑥ — identidades que el servicio autentica y el organigrama no gobierna.

Medido el 2026-08-18: `roles-por-alias.json` (organigrama firmado) declara 16
roles; `roster.json` (censo de identidad) declara 31; y `canon_identidad()`
resuelve por la UNIÓN de los dos. Resultado: **16 nombres que pasan la puerta
fail-closed, reciben correo, y no tienen jefe, ni gate, ni humano responsable.**
El sistema permite que exista una identidad operativa reconocida sin saber qué
clase de entidad es ni quién responde por ella.

**Esta sección ENCUENTRA; no adjudica.** El tipo sale `UNCLASSIFIED` y se queda
así hasta que el operador lo decida. Inferirlo por el nombre —«`destilador` suena
a servicio»— sería que el software se invente el organigrama, que es exactamente
lo que este informe existe para impedir. Lo que sí enseña son HECHOS
comprobables: si está en el censo, si está en el organigrama, cuántos alias
tiene, si alguien ha consumido por él y si recibe correo.
"""
from __future__ import annotations

import json

from conftest import construir
from fastapi.testclient import TestClient

ORG = {                                   # organigrama firmado: sólo `be` y `cto`
    "rol_por_alias": {"backend": "be", "cto-A": "cto"},
    "jerarquia": {"cto": {"reporta_a": "ALBERT", "capa": "c-suite"},
                  "be": {"reporta_a": "cto", "capa": "ejecucion"},
                  # EL CASO INVERSO, medido en producción: existe en el
                  # organigrama y NO tiene identidad. Hoy `/inbox/engineering-
                  # manager` da 422 — un rol que no puede recibir trabajo.
                  "engineering-manager": {"reporta_a": "cto", "capa": "ejecucion"}},
}
ROSTER = {                                # censo: además, dos que NADIE gobierna
    "agentes": [
        {"nombre": "backend", "humano": "albert", "clave": "", "rol": "be"},
        {"nombre": "cto-A", "humano": "albert", "clave": "", "rol": "cto"},
        {"nombre": "destilador", "humano": "albert", "clave": "", "rol": "destilador"},
        {"nombre": "harness-x", "humano": "albert", "clave": "", "rol": "harness-x"},
    ],
    "humanos": [{"nombre": "albert", "alias": ["Albert"]}],
    "difusion": ["equipo"],
}


def _monta(tmp_path, monkeypatch):
    (tmp_path / "org.json").write_text(json.dumps(ORG))
    s = construir(tmp_path, monkeypatch, roster=ROSTER,
                  extra_env={"LLMINBOX_ROLES_ALIAS": str(tmp_path / "org.json")})
    (tmp_path / "DEMO-LEDGER.md").write_text(
        "### [cto-A → backend · FYI] gobernado\ncuerpo\n"
        "### [cto-A → destilador · FYI] a un huérfano\ncuerpo\n")
    return s


def _seis(txt):
    ini = txt.index("⑥ ")
    resto = txt[ini:]
    for otra in ("\n① ", "\n② ", "\n③ ", "\n── ④", "\n── ⑤"):
        if otra in resto:
            resto = resto[: resto.index(otra)]
    return resto


def _doctor(s):
    with TestClient(s.app) as c:
        s.barrido()
        c.headers.update({"X-Llminbox-Token": "test-token"})
        return c.get("/doctor").text


def test_encuentra_las_identidades_que_nadie_gobierna(tmp_path, monkeypatch):
    """Los dos que están en el censo y no en el organigrama, y sólo ésos.

    FALSADOR: sin la sección no hay nada que leer; y si listara TODO el censo,
    `be` y `cto` saldrían y el control de abajo caería."""
    sec = _seis(_doctor(_monta(tmp_path, monkeypatch)))
    assert "3 " in sec.splitlines()[0], sec.splitlines()[0]
    assert "destilador" in sec and "harness-x" in sec, sec
    # Y el inverso: en el organigrama, sin identidad. Es el que rompe de verdad —
    # se le puede asignar trabajo y su bandeja contesta 422.
    assert "engineering-manager" in sec, sec


def test_no_acusa_a_quien_si_esta_en_el_organigrama(tmp_path, monkeypatch):
    """CONTROL NEGATIVO, y va aquí porque sin él lo de arriba no prueba nada: un
    informe que liste a todo el censo «encuentra» a los huérfanos por acumulación,
    no por detección."""
    sec = _seis(_doctor(_monta(tmp_path, monkeypatch)))
    filas = [ln for ln in sec.splitlines() if ln.startswith("   ")]
    nombres = {ln.split()[0] for ln in filas if ln.strip() and not ln.strip().startswith(("principal", "El ", "ⓘ"))}
    assert "be" not in nombres and "cto" not in nombres, nombres


def test_no_inventa_el_tipo_de_nadie(tmp_path, monkeypatch):
    """LA LÍNEA QUE NO SE CRUZA. `destilador` suena a servicio y `harness-x` a
    herramienta, y aun así el informe NO lo dice: adjudicar el tipo es del
    operador. Un software que se inventa el organigrama es el problema que esta
    sección denuncia, no su solución.

    FALSADOR: cualquier inferencia por nombre mete `SERVICE`/`ROLE`/`ALIAS` en la
    salida y esto se pone rojo."""
    sec = _seis(_doctor(_monta(tmp_path, monkeypatch)))
    assert sec.count("UNCLASSIFIED") == 3, sec
    for inventado in ("SERVICE", "ALIAS", "GROUP", "LEGACY", "PROJECT"):
        assert inventado not in sec, f"infirió {inventado}: {sec}"


def test_enseña_hechos_comprobables_no_opiniones(tmp_path, monkeypatch):
    """Las columnas son hechos que el servicio puede sostener: censo, organigrama,
    alias, cursor y correo. `destilador` RECIBE correo en el arnés y no tiene
    cursor — las dos cosas tienen que verse, porque juntas son el caso que
    importa: le llega trabajo y nadie lo drena."""
    sec = _seis(_doctor(_monta(tmp_path, monkeypatch)))
    # La línea de COLUMNAS, no la cabecera de la sección: ésta también
    # contiene «principal(es)» y el `in` suelto la cazaba a ella.
    cab = next(ln for ln in sec.splitlines() if ln.strip().startswith("principal "))
    for col in ("censo", "organigrama", "alias", "cursor", "correo", "tipo"):
        assert col in cab, f"falta la columna {col}: {cab}"
    fila = next(ln for ln in sec.splitlines() if ln.strip().startswith("destilador"))
    assert "sí" in fila, fila


def test_sin_organigrama_montado_no_acusa_a_todo_el_mundo(tmp_path, monkeypatch):
    """CONTROL del caso degradado, y es el que evita un informe catastrofista: sin
    la fuente firmada montada, `JERARQUIA` está vacía y comparar contra ella diría
    que NADIE está gobernado — 31 acusaciones falsas de golpe.

    FALSADOR: quitar la guarda de «no montada» hace que esta sección liste al
    censo entero."""
    s = construir(tmp_path, monkeypatch, roster=ROSTER)   # sin LLMINBOX_ROLES_ALIAS
    txt = _doctor(s)
    sec = _seis(txt)
    assert "destilador" not in sec, sec
    assert "organigrama NO montado" in sec, sec
