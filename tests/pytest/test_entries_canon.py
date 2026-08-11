"""⑪ /entries canoniza al LEER como el indexador canoniza al ESCRIBIR, y
⑩ la difusión se expande en la entrega de /inbox.

⑪ — hallazgo de db-mig (2026-08-10T08:56Z, con controles ±): `?to=` y
`?actor=` comparaban la cadena CRUDA contra columnas que el parser escribe
CANONIZADAS — `to=albert` daba 0 sobre 182 filas reales, con HTTP 200 y sin
aviso. Es la capa con la que la flota verifica enrutado: un 0 falso ahí
dispara re-trabajo.

⑩ — hallazgo de frontend·cfocockpit: una entrada dirigida sólo a la difusión
(«flota»/«equipo») dependía de que cada agente la reconociera; ahora /inbox
la entrega a cada bandeja como dirigida.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import construir


def test_to_canoniza_al_leer(cliente):
    """`to=BACKEND` (mayúsculas) debe encontrar las filas que el parser indexó
    como 'backend'.

    FALSADOR: con la comparación cruda (`p.append(to)` sin canonico), esto da
    r.json() == [] con HTTP 200 — el 0 silencioso exacto que midió db-mig.
    """
    r = cliente.get("/entries?to=BACKEND")
    assert r.status_code == 200
    assert len(r.json()) >= 2   # las dos entradas de demo-ledger van a 'backend'


def test_actor_canoniza_al_leer(cliente):
    """`actor=CTO-a` (caja revuelta) debe encontrar lo que firmó 'cto-A'."""
    r = cliente.get("/entries?actor=CTO-a")
    assert r.status_code == 200
    assert len(r.json()) >= 3   # cto-A firma las 3 entradas sembradas


def test_actor_crudo_sigue_dando_cero_para_desconocido(cliente):
    """Control negativo: un nombre que no canoniza a nada indexado sigue dando
    0 filas — canonizar no convierte el filtro en una búsqueda difusa."""
    r = cliente.get("/entries?actor=nadie-conocido")
    assert r.status_code == 200
    assert r.json() == []


def test_difusion_se_entrega_en_inbox(tmp_path, monkeypatch):
    """⑩: una entrada dirigida SÓLO a 'equipo' (la difusión del ROSTER de
    prueba) aparece en la bandeja de backend sin que nadie la nombre.

    FALSADOR: sin la expansión en /inbox (nombres = escuchados(agent) a secas),
    esta entrada no casa con ningún nombre escuchado y la bandeja no la trae.
    """
    import json, os
    s = construir(tmp_path, monkeypatch)
    mounts = json.load(open(os.environ["LLMINBOX_MOUNTS_JSON"]))
    with open(mounts["demo-ledger"], "a") as fh:
        fh.write("### [cto-A → equipo · AVISO] para toda la difusion\ncuerpo difusion\n")
    with TestClient(s.app) as c:
        s.barrido()
        c.headers.update({"X-Llminbox-Token": "test-token"})
        r = c.get("/inbox/backend")
        assert r.status_code == 200
        assert "para toda la difusion" in r.text


def test_la_difusion_sobrevive_a_una_rederivacion(tmp_path, monkeypatch):
    """⑩ estaba a medias y su mitad ausente era DESTRUCTIVA: la difusión se
    persistía al indexar una entrada NUEVA, pero no al RE-DERIVAR una ya
    conocida. Y el gate de censo/troceador hace `DELETE FROM recipients` antes
    de re-derivar ⇒ cada arranque con censo o parser nuevo borraba la difusión
    de TODO el histórico y sólo la recreaba para lo que llegara después.

    Destapado por @cto (bikeus): su `/lint` marcaba «sin entregar» una entrada
    que él sí había recibido. Medido: 6.220 entradas del corpus llevan difusión
    y quedaban 32 filas de entrega.

    FALSADOR: sin `for w in e.difusion` en la rama de re-derivación, el segundo
    arranque deja la entrada sin destinatarios y esto se pone rojo.
    """
    import json, os, sqlite3
    from fastapi.testclient import TestClient
    s = construir(tmp_path, monkeypatch)
    mounts = json.load(open(os.environ["LLMINBOX_MOUNTS_JSON"]))
    with open(mounts["demo-ledger"], "a") as fh:
        fh.write("### [cto-A → equipo · AVISO] entrada de difusion\ncuerpo\n")
    with TestClient(s.app) as c:
        s.barrido()
        c.headers.update({"X-Llminbox-Token": "test-token"})
        assert "entrada de difusion" in c.get("/inbox/backend").text

    # SEGUNDO arranque forzando la re-derivación, igual que hace el gate de censo
    con = sqlite3.connect(os.environ["LLMINBOX_DB"])
    con.execute("DELETE FROM recipients")
    con.execute("DELETE FROM files")
    con.execute("UPDATE meta SET v='huella-vieja' WHERE k='roster_v'")
    con.commit(); con.close()

    # ⚠️ `construir()` REESCRIBE los ficheros de ledger, así que hay que volver a
    # sembrar la entrada: si no, el segundo arranque no la encuentra en el fichero
    # y el test mediría «desapareció del markdown», no «se perdió su difusión».
    # (La primera versión de este test fallaba por esto, no por el código.)
    s2 = construir(tmp_path, monkeypatch)
    with open(mounts["demo-ledger"], "a") as fh:
        fh.write("### [cto-A → equipo · AVISO] entrada de difusion\ncuerpo\n")
    with TestClient(s2.app) as c:
        s2.barrido()
        c.headers.update({"X-Llminbox-Token": "test-token"})
        assert "entrada de difusion" in c.get("/inbox/backend").text, (
            "la re-derivación se comió la difusión del histórico")
