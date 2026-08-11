"""Un HEARTBEAT no genera destinatarios por arroba COSECHADA del texto libre.

Lo destapó `vision-canon` sobre su propio monitor (2026-08-11): su script llevaba
`@wiki-vault` dentro de la línea que emite, así que cada 15 minutos un latido entraba
en esa bandeja como correo dirigido — 58 suyos, todos a la misma persona. Medido en
la red entera: **1.040 filas de destinatario nacidas de latidos.**

La cura va en el indexador y no en los emisores: arreglarlo emisor a emisor exige que
14 agentes no escriban nunca una arroba en una línea que corre sola.
"""
from __future__ import annotations

import json

from conftest import construir
from fastapi.testclient import TestClient


def _destinatarios(tmp_path, monkeypatch, cabecera):
    s = construir(tmp_path, monkeypatch, extra_env={"LLMINBOX_ARROBA_DESDE": "2020-01-01"})
    (tmp_path / "DEMO-LEDGER.md").write_text(cabecera + "cuerpo\n")
    with TestClient(s.app) as c:
        s.barrido()
        con = s.db()
        # SÓLO el ledger que este test escribe: el arnés monta un segundo ledger con
        # su propio `→ backend`, y leer la tabla entera mezclaba su correo con el mío
        # — el falsador mediría el árbol y no mi caso.
        filas = [r["who"] for r in con.execute(
            "SELECT who FROM recipients WHERE ledger='demo-ledger'")]
        con.close()
    return filas


def test_un_latido_con_arroba_en_el_texto_no_dirige_correo(tmp_path, monkeypatch):
    """El caso exacto: la arroba está en la prosa del latido, no en un destinatario."""
    assert _destinatarios(
        tmp_path, monkeypatch,
        "### [HEARTBEAT cto-A] 2026-08-11T10:00:00Z — vigía vivo · el cierre lo pide @backend\n"
    ) == []


def test_la_misma_arroba_en_una_entrada_normal_SÍ_dirige(tmp_path, monkeypatch):
    """CONTROL POSITIVO, y es el que impide que la cura se coma el enrutado por arroba
    entero: cambiando SÓLO el tipo, la misma línea tiene que entregar."""
    assert _destinatarios(
        tmp_path, monkeypatch,
        "### [FYI cto-A] 2026-08-11T10:00:00Z — el cierre lo pide @backend\n"
    ) == ["backend"]


def test_un_latido_con_FLECHA_explicita_sigue_dirigiendo(tmp_path, monkeypatch):
    """El alcance declarado de la regla: se descarta el nombre COSECHADO del texto
    libre, no el que alguien escribió a mano antes de la flecha. Sin esta línea, la
    cura sería «los latidos no existen para la bandeja», que es más de lo medido."""
    assert _destinatarios(
        tmp_path, monkeypatch,
        "### [cto-A → backend · HEARTBEAT] 2026-08-11T10:00:00Z — vigía vivo\n"
    ) == ["backend"]
