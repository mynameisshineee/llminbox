"""⑤ del doctor: el instrumento tiene que decir si la PUERTA está puesta.

Por qué existe este fichero: ⑤ nació como un medidor de PRE-VUELO —«¿se puede ya
encender `LLMINBOX_CARRIL_OBLIGATORIO`?»— y se envió sin un solo test. El 2026-08-16
la puerta se encendió; el 2026-08-18 ⑤ seguía diciendo «se puede plantear encender»
y contando 1390 «consumo(s) SIN carril» que en realidad eran 1390 **rechazos 422**.

El detalle que lo causa está en `servicio.py`: `anota_consumo()` se llama ANTES del
`raise` de la puerta, así que con el gate puesto la columna «SIN» cuenta intentos que
rebotaron. Un instrumento que llama «consumo» a un rechazo, y que aconseja encender lo
que ya lleva dos días encendido, no es un adorno roto: es la única fuente que tiene la
flota para saber si la puerta está puesta (uvicorn corre sin log de acceso).
"""
from __future__ import annotations

from conftest import construir

PUERTA = {"LLMINBOX_CARRIL_OBLIGATORIO": "1"}


def _cliente(tmp_path, monkeypatch, extra_env=None):
    from fastapi.testclient import TestClient
    tmp_path.mkdir(parents=True, exist_ok=True)
    if not (extra_env or {}).get("LLMINBOX_CARRIL_OBLIGATORIO"):
        # Un test construye DOS servicios (con puerta y sin ella). `monkeypatch.setenv`
        # del primero sobrevive al segundo: sin este delenv, el caso «PUERTA ABIERTA»
        # se mediría con la puerta puesta y el test pasaría por el motivo equivocado.
        monkeypatch.delenv("LLMINBOX_CARRIL_OBLIGATORIO", raising=False)
    s = construir(tmp_path, monkeypatch, extra_env=extra_env)
    c = TestClient(s.app)
    c.__enter__()
    s.barrido()
    c.headers.update({"X-Llminbox-Token": "test-token"})
    return s, c


def _consumir(c, agente, carril=None):
    h = {"X-Llminbox-Carril": carril} if carril else {}
    return c.post(f"/inbox/{agente}/leido", json={"hasta": {}}, headers=h)


def test_la_puerta_puesta_se_nombra_en_el_informe(tmp_path, monkeypatch):
    """FALSADOR: si ⑤ no lee `CARRIL_OBLIGATORIO`, uno de los dos casos falla.

    No basta con que el texto sea distinto: con la puerta puesta NO puede seguir
    apareciendo el consejo de encenderla.
    """
    s, c = _cliente(tmp_path, monkeypatch, PUERTA)
    puesta = c.get("/doctor").text
    assert "PUERTA PUESTA" in puesta
    assert "se puede plantear encender" not in puesta

    s2, c2 = _cliente(tmp_path / "b", monkeypatch)      # misma construcción, sin la puerta
    abierta = c2.get("/doctor").text
    assert "PUERTA ABIERTA" in abierta


def test_con_la_puerta_puesta_un_sin_carril_es_rechazo_y_no_consumo(tmp_path, monkeypatch):
    """FALSADOR: hoy ese intento sale contado como «consumo SIN carril».

    Control positivo incluido: el consumo CON carril sí es un consumo, y se cuenta
    aparte — si el arreglo se pasara de listo y dejara de contar nada, esto lo caza.
    """
    s, c = _cliente(tmp_path, monkeypatch, PUERTA)
    assert _consumir(c, "backend").status_code == 422           # rebota en la puerta
    assert _consumir(c, "backend", "demo").status_code == 200    # control positivo

    t = c.get("/doctor").text
    assert "1 consumo(s) CON carril" in t
    assert "RECHAZADO" in t
    # el rechazo NO se cuenta como consumo: la forma vieja del agregado era
    # «… CON carril · N SIN · …» y con la puerta puesta no puede reaparecer.
    assert " 1 SIN " not in t


def test_un_rol_siempre_rechazado_es_alarma_de_ahora_no_pronostico(tmp_path, monkeypatch):
    """FALSADOR: hoy el aviso dice «encender el gate HOY los dejaría mudos» —
    futuro condicional— cuando el gate ya está puesto y el rol ya está mudo.

    `cto-A` sólo consume sin carril ⇒ no drena nada. `backend` manda carril ⇒ no
    debe aparecer en la alarma (control negativo: si el arreglo marcara a todos,
    esta línea falla).
    """
    s, c = _cliente(tmp_path, monkeypatch, PUERTA)
    _consumir(c, "cto-A")                       # 422, siempre sin carril
    _consumir(c, "backend", "demo")             # 200, con carril

    t = c.get("/doctor").text
    assert "cto" in t
    assert "dejaría mudos" not in t             # ya no es un pronóstico
    linea = [l for l in t.splitlines() if "RECHAZADO SIEMPRE" in l]
    assert linea, "falta la alarma de rol 100% rechazado"
    assert "be" not in linea[0].split(":")[-1]  # el que manda carril no se denuncia


def test_con_la_puerta_abierta_el_informe_viejo_se_conserva(tmp_path, monkeypatch):
    """FALSADOR: el arreglo no puede romper el modo pre-vuelo, que sigue siendo
    el que se usa en un despliegue sin mapa de carriles."""
    s, c = _cliente(tmp_path, monkeypatch)
    _consumir(c, "cto-A")                       # 200: sin puerta, pasa sin carril
    t = c.get("/doctor").text
    assert "consumo(s) CON carril" in t and " 1 SIN " in t   # aquí SÍ es consumo
    assert "se puede plantear encender" in t or "dejaría mudos" in t


def test_rebotar_no_es_estar_parado_si_el_cursor_esta_fresco(tmp_path, monkeypatch):
    """FALSADOR del arreglo anterior, encontrado EN PRODUCCIÓN dos veces seguidas.

    1ª: ⑤ acusó a `infra` de no drenar 17 min después de que `infra` drenara.
    2ª (el mismo error, ya «arreglado» contra el arranque): acusó a `cpo`, cuyo cursor
    se había movido 11 SEGUNDOS antes de arrancar el proceso.

    La causa común: el contador vive en memoria y su ventana se reinicia con el
    servicio, así que «sin drenar desde el arranque» es cierto para TODO el mundo
    durante los primeros minutos. La pregunta que vale —¿hace mucho que no drena?—
    es una DURACIÓN, y no depende de cuándo se reinició el servicio.
    """
    from datetime import datetime, timedelta, timezone
    from conftest import db_directa

    s, c = _cliente(tmp_path, monkeypatch, PUERTA)
    _consumir(c, "cto-A")        # 422 · le pondremos cursor FRESCO
    _consumir(c, "backend")      # 422 · le pondremos cursor RANCIO
    ahora = datetime.now(timezone.utc)
    con = db_directa(s)
    for rol, cuando in (("cto", ahora - timedelta(minutes=5)),
                        ("be",  ahora - timedelta(hours=9))):
        con.execute("INSERT OR REPLACE INTO cursors VALUES (?,?,?,?)",
                    (rol, "demo-ledger", 1, cuando.isoformat(timespec="seconds")))
    con.commit(); con.close()

    t = c.get("/doctor").text
    roja = [l for l in t.splitlines() if "sin drenar" in l]
    assert roja, "sigue haciendo falta la alarma para quien de verdad no drena"
    assert "be" in roja[0], "lleva 9 h sin drenar y rebotando: eso sí es la alarma"
    assert "cto" not in roja[0], "drenó hace 5 min: rebota, pero NO está parado"
    aviso = [l for l in t.splitlines() if "sin migrar" in l]
    assert aviso and "cto" in aviso[0], "el que rebota y drena se nombra, pero en ⚠️"


def test_la_alarma_no_depende_de_cuando_se_reinicio_el_servicio(tmp_path, monkeypatch):
    """FALSADOR directo del bug de producción: un cursor movido JUSTO ANTES de
    arrancar (11 s, el caso real de `cpo`) no puede leerse como «parado»."""
    from datetime import datetime, timedelta, timezone
    from conftest import db_directa

    s, c = _cliente(tmp_path, monkeypatch, PUERTA)
    _consumir(c, "cto-A")
    antes_de_arrancar = datetime.fromisoformat(s.ARRANQUE) - timedelta(seconds=11)
    con = db_directa(s)
    con.execute("INSERT OR REPLACE INTO cursors VALUES (?,?,?,?)",
                ("cto", "demo-ledger", 1, antes_de_arrancar.isoformat(timespec="seconds")))
    con.commit(); con.close()

    t = c.get("/doctor").text
    roja = [l for l in t.splitlines() if "sin drenar" in l]
    assert not roja or "cto" not in roja[0], "drenó 11 s antes del arranque: no está parado"
