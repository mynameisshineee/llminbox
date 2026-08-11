"""`/doctor` — las tres higienes del canal que nadie miraba.

No prueba que el servicio funcione: prueba que **sabe señalar el mal uso**, que es
distinto y es lo que hace útil al endpoint. Cada sección con su control positivo Y
su negativo, porque un doctor que diagnostica a todo el mundo no diagnostica.

Ojo al orden de los controles: primero se comprueba que la sección se QUEDA CALLADA
cuando no hay nada que decir. Si eso no se cumple, el hallazgo de después no prueba
nada — sería una sección que se queja siempre.
"""
from __future__ import annotations

from conftest import construir


def _texto(cliente, **params):
    r = cliente.get("/doctor", params=params)
    assert r.status_code == 200, r.text
    return r.text


def _seccion(txt, num):
    """El bloque de una sección: de su cabecera «① …» a la línea en blanco de antes
    de la siguiente. Se corta por el número y no por el título — el título es prosa
    y se reescribe; el número es el contrato."""
    marca = {1: "① ", 2: "② ", 3: "③ "}[num]
    ini = txt.index(marca)
    resto = txt[ini:]
    for otra in ("\n① ", "\n② ", "\n③ "):
        if otra in resto:
            resto = resto[: resto.index(otra)]
    return resto


# ── ① mira y no drena ────────────────────────────────────────────────────────

def test_sin_lecturas_nadie_aparece_como_moroso(cliente):
    """CONTROL NEGATIVO, y va primero: con el correo sin entregar a nadie que haya
    mirado, la sección ① tiene que estar VACÍA. Si aquí saliera gente, el test de
    abajo pasaría por acumulación de ruido, no por detección."""
    s = _seccion(_texto(cliente), 1)
    assert "0 agente(s)" in s
    assert "nadie tiene correo dirigido sin consumir" in s


def test_mirar_sin_drenar_sale_con_su_cuenta(cliente, servicio):
    """Mirar la bandeja NO consume (es la propiedad que este repo defiende). Así que
    tras mirar, el pendiente sigue ahí y ① tiene que decirlo, con el número."""
    cliente.get("/inbox/backend")          # mira, no consume
    servicio.barrido()                     # el barrido es el que persiste `lecturas`
    s = _seccion(_texto(cliente), 1)
    assert "1 agente(s)" in s
    # Sale por su ROL (`be`), no por el nombre con que miró (`backend`): la clave
    # del cursor es el rol, y mezclarlos duplicaba a la misma persona en el informe.
    # 3 entradas dirigidas a `backend` en el arnés (2 en demo-ledger, 1 en otro).
    linea = next(l for l in s.splitlines() if l.strip().startswith("be "))
    assert linea.split()[1] == "3", linea
    assert "nunca" in s                    # no ha consumido: último consumo «nunca»


def test_al_drenar_desaparece_de_la_lista(cliente, servicio):
    """FALSADOR del anterior: si ① contara «lecturas» en vez de PENDIENTES, drenar
    no cambiaría nada y el agente seguiría en la lista para siempre."""
    cliente.get("/inbox/backend")
    servicio.barrido()
    assert "1 agente(s)" in _seccion(_texto(cliente), 1)
    cliente.post("/inbox/backend/leido", json={"hasta": {"demo-ledger": 99, "otro-ledger": 99}})
    assert "0 agente(s)" in _seccion(_texto(cliente), 1)


# ── ② publica y no dirige ────────────────────────────────────────────────────

def test_todo_dirigido_no_acusa_a_nadie(cliente):
    """CONTROL NEGATIVO: el arnés tiene las 3 entradas con `→ backend`. Si ② marcara
    algo aquí, estaría contando entradas y no entradas HUÉRFANAS."""
    s = _seccion(_texto(cliente), 2)
    assert "0 de 3" in s
    assert "todo lo publicado en la ventana nombra a alguien" in s


def test_entrada_sin_destinatario_se_atribuye_a_su_autor(tmp_path, monkeypatch):
    """El caso real: 54 de 56 entradas de la flota no nombraban a nadie. Se cuenta
    POR AUTOR a propósito — un porcentaje global no le dice a nadie qué cambiar."""
    from fastapi.testclient import TestClient
    s = construir(tmp_path, monkeypatch)
    # Sin flecha y sin @nombre: no cae en ninguna bandeja.
    (tmp_path / "DEMO-LEDGER.md").write_text(
        "### [cto-A → backend · REQUEST] primera\ncuerpo uno\n"
        "### [cto-A · FYI] huerfana una\ncuerpo\n"
        "### [cto-A · FYI] huerfana dos\ncuerpo\n"
    )
    with TestClient(s.app) as c:
        s.barrido()
        c.headers.update({"X-Llminbox-Token": "test-token"})
        sec = _seccion(_texto(c), 2)
    assert "cto" in sec
    # 2 huérfanas de las 4 suyas: 3 en demo-ledger + 1 en otro-ledger, que el arnés
    # también le atribuye. La cuenta es por AUTOR y cruza ledgers a propósito.
    linea = next(l for l in sec.splitlines() if l.strip().startswith("cto"))
    assert linea.split()[1:3] == ["2", "4"], linea


def test_la_ventana_de_dias_se_respeta(tmp_path, monkeypatch):
    """FALSADOR del parámetro: si `dias` fuera decorativo, una huérfana ANTIGUA
    seguiría contando con `dias=1` y el informe hablaría de deuda ya resuelta."""
    from fastapi.testclient import TestClient
    s = construir(tmp_path, monkeypatch)
    (tmp_path / "DEMO-LEDGER.md").write_text(
        "### [cto-A · FYI] 2020-01-01T00:00:00Z vieja y huerfana\ncuerpo\n"
    )
    with TestClient(s.app) as c:
        s.barrido()
        c.headers.update({"X-Llminbox-Token": "test-token"})
        sec = _seccion(_texto(c, dias=1), 2)
        assert "todo lo publicado en la ventana nombra a alguien" in sec
        # 0 huérfanas de 1: la vieja (2020) cae fuera de la ventana; la que queda es
        # la de `otro-ledger`, que NO lleva sello de hora y por eso se incluye —
        # excluirlas escondía justo el caso que esta sección cuenta.
        assert "0 de 1" in sec and "1 sin sello de hora" in sec


# ── ③ claims pasados de TTL ──────────────────────────────────────────────────

def test_claim_recien_cogido_no_se_denuncia(cliente):
    """CONTROL NEGATIVO: un claim de hace un segundo no está pasado de plazo. Sin
    esto, la sección ③ podría estar listando TODOS los abiertos."""
    cliente.post("/claim", json={"tema": "algo", "rol": "ejecuta", "agent": "backend"})
    s = _seccion(_texto(cliente), 3)
    assert "0 sin cerrar" in s
    assert "ninguno pasado de plazo" in s


def test_claim_viejo_aparece_con_sus_horas(cliente, servicio):
    """El caso que me pasó a mí: `qa` llevaba 45 h con un claim y nadie lo veía.
    Se falsifica moviendo el `abierto` hacia atrás en la tabla — el TTL es tiempo
    real, así que no hay forma de esperarlo en un test."""
    cliente.post("/claim", json={"tema": "algo", "rol": "ejecuta", "agent": "backend"})
    con = servicio.db()
    con.execute("UPDATE claims SET abierto='2020-01-01T00:00:00+00:00' WHERE tema='algo'")
    con.commit()
    con.close()
    s = _seccion(_texto(cliente), 3)
    assert "1 sin cerrar" in s
    assert "algo" in s and "ejecuta" in s


def test_el_doctor_no_escribe_nada(cliente, servicio):
    """`/inbox` fue un GET que mutaba estado y tumbó bandejas. Un informe de
    diagnóstico que escriba repite esa avería con otro nombre: se comprueban las
    tablas ANTES y DESPUÉS."""
    def foto():
        con = servicio.db()
        f = {t: con.execute(f"SELECT COUNT(*) n FROM {t}").fetchone()["n"]
             for t in ("cursors", "claims", "lecturas", "entries", "recipients")}
        con.close()
        return f
    antes = foto()
    _texto(cliente)
    assert foto() == antes


def test_los_nombres_fuera_del_censo_no_compiten_con_los_de_dentro(tmp_path, monkeypatch):
    """La primera corrida contra la flota real sacó 11 `zzz-*` entre los 20 primeros,
    cada uno con 433 pendientes, empujando fuera a los agentes de verdad: `lecturas`
    apunta a CUALQUIER nombre que alguien consulte, y la difusión le da bandeja a
    cualquiera, así que los fantasmas acumulan deuda por diseño. Van aparte y
    CONTADOS, no listados — enumerarlos les devolvería el sitio que se les quita.
    """
    from fastapi.testclient import TestClient
    s_mod = construir(tmp_path, monkeypatch)
    # Una difusión: le llega a todo el mundo, censado o no. Es lo que le daba 433
    # pendientes a cada `zzz-*` en la flota real.
    (tmp_path / "DEMO-LEDGER.md").write_text(
        "### [cto-A → equipo · FYI] para todos\ncuerpo\n"
    )
    con = __import__("sqlite3").connect(str(tmp_path / "llminbox.sqlite"))
    with TestClient(s_mod.app) as c:
        s_mod.barrido()
        c.headers.update({"X-Llminbox-Token": "test-token"})
        c.get("/inbox/backend")          # uno del censo
        # El fantasma se SIEMBRA en `lecturas`, no se pide por HTTP: hoy la puerta de
        # identidad es fail-closed y `/inbox/zzz-fantasma` da 422. Los 11 `zzz-*` de
        # la flota real son residuo ANTERIOR a esa puerta — la tabla los conserva y
        # el informe se los encontraba delante.
        con2 = s_mod.db()
        con2.execute("INSERT OR REPLACE INTO lecturas(agent,primera,ultima,veces) "
                     "VALUES('zzz-fantasma','2020-01-01','2020-01-01',1)")
        con2.commit(); con2.close()
        s_mod.barrido()
        sec = _seccion(_texto(c), 1)
    con.close()
    assert "1 agente(s) del censo" in sec       # sólo `be`; el fantasma no compite
    assert "FUERA DEL CENSO" in sec and "zzz-fantasma" in sec
    # FALSADOR: si el fantasma entrara en el ranking sería una FILA con su columna de
    # pendientes. Sólo puede salir en la nota de abajo, y sin número propio.
    assert not any(l.strip().startswith("zzz-fantasma ") for l in sec.splitlines())


def test_un_alias_de_difusion_va_marcado(tmp_path, monkeypatch):
    """Los tres primeros puestos de la primera corrida real eran un humano y dos
    alias de difusión. Nadie drena esas bandejas, así que su deuda no es deuda de
    nadie — y sin la marca, quien lee empieza a arreglar por arriba lo que no existe.
    FALSADOR: si la marca se pusiera a todos, no distinguiría; `be` no puede llevarla.
    """
    from fastapi.testclient import TestClient
    s_mod = construir(tmp_path, monkeypatch)
    (tmp_path / "DEMO-LEDGER.md").write_text(
        "### [cto-A -> equipo · FYI] para todos\ncuerpo\n".replace("->", "\u2192")
    )
    with TestClient(s_mod.app) as c:
        s_mod.barrido()
        c.headers.update({"X-Llminbox-Token": "test-token"})
        c.get("/inbox/backend")
        con = s_mod.db()
        con.execute("INSERT OR REPLACE INTO lecturas(agent,primera,ultima,veces) "
                    "VALUES('equipo','2020-01-01','2020-01-01',1)")
        con.commit(); con.close()
        s_mod.barrido()
        sec = _seccion(_texto(c), 1)
    equipo = next(l for l in sec.splitlines() if l.strip().startswith("equipo "))
    assert "alias de difusión" in equipo
    be = next(l for l in sec.splitlines() if l.strip().startswith("be "))
    assert "alias de difusión" not in be and "humano" not in be
