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
    """Las columnas son hechos que el servicio puede sostener, uno por proyección
    más la pregunta derivada. `destilador` RECIBE correo en el arnés y no tiene
    cursor — las dos cosas tienen que verse, porque juntas son el caso que
    importa: le llega trabajo y nadie lo drena."""
    sec = _seis(_doctor(_monta(tmp_path, monkeypatch)))
    # La línea de COLUMNAS, no la cabecera de la sección: ésta también
    # contiene «principal(es)» y el `in` suelto la cazaba a ella.
    cab = next(ln for ln in sec.splitlines() if ln.strip().startswith("principal "))
    for col in ("roster", "org_alias", "jerarquia", "resuelve", "cursor",
                "correo", "tipo"):
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


# ── ⑥ refresca su PROPIA fuente, y distingue cuatro realidades ────────────────
# Corrección del operador: `censo | organigrama` mezclaba tres cosas distintas.
# Hay tres proyecciones (roster.json · rol_por_alias · jerarquía) y una pregunta
# derivada (¿resuelve la identidad?), y cada combinación es una patología
# diferente:
#
#   resolvable=sí + hierarchy=no  → identidad operativa SIN GOBIERNO
#   hierarchy=sí + resolvable=no  → rol organizativo IMPOSIBLE DE EJECUTAR
#   roster ≠ org_alias            → DERIVA entre proyecciones legacy
#
# La tercera no bloquea nada mientras la unión sea el mecanismo transitorio, pero
# no puede desaparecer del diagnóstico: es el caso vivo de `engineering-manager`.

def _monta_em(tmp_path, monkeypatch):
    """El estado REAL de producción: el EM está en el organigrama (con alias) y
    NO está en el roster; su bandeja resuelve por la unión."""
    org = json.loads(json.dumps(ORG))
    org["rol_por_alias"]["engineering-manager"] = "engineering-manager"
    org["rol_por_alias"]["em-bikeus"] = "engineering-manager"
    # Y la SEGUNDA patología, que hoy tiene cero casos en producción y por eso hay
    # que fabricarla aquí: un rol declarado en la jerarquía SIN ningún alias que
    # lo resuelva. Está en el organigrama y no puede recibir trabajo.
    org["jerarquia"]["rol-inejecutable"] = {"reporta_a": "cto", "capa": "ejecucion"}
    (tmp_path / "org.json").write_text(json.dumps(org))
    s = construir(tmp_path, monkeypatch, roster=ROSTER,
                  extra_env={"LLMINBOX_ROLES_ALIAS": str(tmp_path / "org.json")})
    (tmp_path / "DEMO-LEDGER.md").write_text(
        "### [cto-A → backend · FYI] gobernado\ncuerpo\n")
    return s, tmp_path / "org.json"


def test_distingue_las_tres_patologias(tmp_path, monkeypatch):
    """`engineering-manager` no está en el roster, sí en el organigrama con dos
    alias, y su bandeja responde. Con dos columnas eso se leía como «no está en
    el censo» — que es falso y llevaría a darlo de alta sin necesidad, pagando un
    reindex completo por nada.

    FALSADOR: colapsar `org_alias` y `hierarchy` en una sola columna hace
    indistinguible esta fila de un rol que NO puede recibir trabajo."""
    s, _ = _monta_em(tmp_path, monkeypatch)
    sec = _seis(_doctor(s))
    cab = next(ln for ln in sec.splitlines() if ln.strip().startswith("principal "))
    for col in ("roster", "org_alias", "jerarquia", "resuelve", "cursor", "correo", "tipo"):
        assert col in cab, f"falta la columna {col}: {cab}"
    fila = next(ln for ln in sec.splitlines() if ln.strip().startswith("engineering-manager"))
    campos = fila.split()
    assert campos[1] == "no", f"roster debería ser no: {fila}"
    assert campos[2] == "sí" and campos[3] == "sí", f"org_alias/jerarquia: {fila}"
    assert campos[4] == "sí", f"tiene que constar que RESUELVE: {fila}"


def test_F_DOC_1_ve_el_cambio_sin_que_nadie_llame_a_organigrama(tmp_path, monkeypatch):
    """⑥ no puede depender de que otro endpoint haya refrescado antes. Si la
    fuente cambia y sólo se llama a `/doctor`, el diagnóstico tiene que ser sobre
    la fuente ACTUAL — o no ser un diagnóstico.

    FALSADOR: leer `lp.JERARQUIA` sin refrescar deja fuera al rol nuevo y ⑥
    informa de una organización que ya no existe."""
    s, ruta = _monta_em(tmp_path, monkeypatch)
    assert "sdet" not in _seis(_doctor(s))
    org = json.loads(ruta.read_text())
    org["jerarquia"]["sdet"] = {"reporta_a": "cto", "capa": "gate"}
    ruta.write_text(json.dumps(org))
    assert "sdet" in _seis(_doctor(s)), "⑥ no vio el cambio: diagnostica el pasado"


def test_F_DOC_2_con_la_fuente_rota_no_afirma_huerfanos_actuales(tmp_path, monkeypatch):
    """La precisión semántica del operador: el último-bueno vale como información
    sobre FRESCURA, no como base de una afirmación de gobierno.

    «Hay 17 principales divergentes» es una afirmación sobre AHORA. Con la fuente
    ilegible no se puede sostener, y emitirla igual convertiría un diagnóstico en
    una invención — el defecto que ⑥ existe para denunciar.

    FALSADOR: seguir calculando con el last-good imprime la lista como si fuera
    contemporánea y esto se pone rojo."""
    s, ruta = _monta_em(tmp_path, monkeypatch)
    assert "engineering-manager" in _seis(_doctor(s))
    ruta.unlink()
    sec = _seis(_doctor(s))
    assert "engineering-manager" not in sec, sec
    assert "NO VERIFICABLE" in sec, sec
    assert "ranci" in sec.lower(), sec        # «rancia o ilegible»


def test_no_se_lee_un_cero_como_SoT_resuelto(tmp_path, monkeypatch):
    """⑥ en cero demuestra que las proyecciones COINCIDEN en ese instante. No
    demuestra que haya una fuente única, ni compilador, ni gate de deriva.

    Sin esta línea, dentro de seis meses alguien lee un cero como una garantía
    que el sistema todavía no da — y es la misma clase de error que todo lo que
    ⑥ denuncia, cometido por quien lo lee."""
    s, _ = _monta_em(tmp_path, monkeypatch)
    sec = _seis(_doctor(s))
    assert "no sustituye" in sec.lower(), sec


def test_un_rol_de_la_jerarquia_sin_alias_no_puede_ejecutar(tmp_path, monkeypatch):
    """La segunda patología, y el falsador que faltaba: `org_alias` y `jerarquia`
    son proyecciones DISTINTAS del mismo fichero, y colapsarlas en una columna se
    lleva por delante este caso.

    `rol-inejecutable` está en la jerarquía y no lo resuelve ningún alias: se le
    puede asignar trabajo sobre el papel y su bandeja contesta 422. Es el defecto
    que medí en producción con `engineering-manager` antes de que el harness le
    diera alias.

    FALSADOR (el que sobrevivía): imprimir `jerarquia` en la columna de
    `org_alias` hace que esta fila salga `org_alias=sí` y esto se pone rojo."""
    s, _ = _monta_em(tmp_path, monkeypatch)
    sec = _seis(_doctor(s))
    fila = next(ln for ln in sec.splitlines() if ln.strip().startswith("rol-inejecutable"))
    campos = fila.split()
    assert campos[1] == "no", f"roster: {fila}"
    assert campos[2] == "no", f"org_alias debería ser NO: {fila}"
    assert campos[3] == "sí", f"jerarquia debería ser SÍ: {fila}"
    assert campos[4] == "no", f"NO resuelve — no puede recibir trabajo: {fila}"
    assert "1 rol(es) sin identidad" in sec, sec


def test_la_caja_de_una_letra_no_fabrica_una_divergencia(tmp_path, monkeypatch):
    """`roles_alias` y `jerarquia` vienen en minúsculas de sus cargadores, pero
    `ROL_DE` conserva lo que declara `roster.json` — que lo edita un humano a
    mano. Un `"rol": "CTO"` fabricaría `CTO ≠ cto` y ⑥ acusaría de deriva a un rol
    perfectamente alineado.

    Un informe de gobierno que inventa una discrepancia por una mayúscula es peor
    que no tenerlo: quema la confianza en las filas que sí son verdad.

    FALSADOR: quitar la normalización mete `CTO` en la lista y esto se pone
    rojo."""
    roster = json.loads(json.dumps(ROSTER))
    for a in roster["agentes"]:
        if a["rol"] == "cto":
            a["rol"] = "CTO"                  # el humano escribió en mayúsculas
    (tmp_path / "org.json").write_text(json.dumps(ORG))
    s = construir(tmp_path, monkeypatch, roster=roster,
                  extra_env={"LLMINBOX_ROLES_ALIAS": str(tmp_path / "org.json")})
    (tmp_path / "DEMO-LEDGER.md").write_text("### [cto-A → backend · FYI] x\ncuerpo\n")
    sec = _seis(_doctor(s))
    assert "CTO" not in sec, f"la caja fabricó una divergencia:\n{sec}"
    assert not any(ln.strip().startswith("cto ") for ln in sec.splitlines()), sec


def test_resuelve_pero_no_enrutable_se_declara(tmp_path, monkeypatch):
    """LA PATOLOGÍA NUEVA, y tiene un caso vivo medido, no es una abstracción.

    `em-bikeus` resuelve como identidad —`/inbox` contesta 200— y NO es una
    dirección de correo: el vocabulario del parser son los NOMBRES del roster, así
    que `→ em-bikeus` parsea a lista vacía y esa entrada no llega a nadie. Medido
    en producción: los 5 nombres que sólo existen en el organigrama no aparecen ni
    una vez en `recipients`, sobre 54 destinatarios distintos.

    Es blocker de piloto: el CTO delegaría con `→ em-bikeus`, la entrada quedaría
    huérfana y nadie vería un error.

    FALSADOR: calcular `enrutable` como copia de `roster` da el mismo resultado
    HOY —coinciden— pero deja de ser cierto en cuanto el parser cambie de fuente;
    y quitar la línea 🔴 esconde la patología entera."""
    s, _ = _monta_em(tmp_path, monkeypatch)
    sec = _seis(_doctor(s))
    fila = next(ln for ln in sec.splitlines()
                if ln.strip().startswith("engineering-manager"))
    campos = fila.split()
    assert campos[4] == "sí", f"debería RESOLVER: {fila}"
    assert campos[5] == "no", f"NO debería ser enrutable: {fila}"
    assert "RESUELVEN PERO NO SON ENRUTABLES" in sec, sec
    assert "se PIERDE" in sec, sec


def test_un_principal_del_roster_si_es_enrutable(tmp_path, monkeypatch):
    """CONTROL: sin él, un `enrutable` constante a «no» pasaría el test de arriba
    sin medir nada. `destilador` está en el roster, luego su nombre ES vocabulario
    del parser y `→ destilador` sí entrega."""
    s, _ = _monta_em(tmp_path, monkeypatch)
    sec = _seis(_doctor(s))
    fila = next(ln for ln in sec.splitlines() if ln.strip().startswith("destilador"))
    assert fila.split()[5] == "sí", f"un nombre del roster tiene que ser enrutable: {fila}"


def test_un_rol_del_organigrama_con_nombre_del_roster_SI_es_enrutable(tmp_path, monkeypatch):
    """El caso donde la unión de nombres deja de ser cosmética, y es exactamente
    la deriva que ⑥ existe para ver: el organigrama reasigna un nombre que YA
    existe en el roster (`backend`) a un rol nuevo que el roster no declara.

    Ese rol es enrutable —`→ backend` sí entrega, porque `backend` es vocabulario
    del parser— y recibe correo de verdad. Calcular sus nombres sólo desde el
    roster lo daría por mudo y sin correo: dos columnas mintiendo a la vez.

    FALSADOR (el mutante que sobrevivía): quitar la segunda pasada que añade los
    nombres de `rol_por_alias` deja este rol con `enrutable=no` y `correo=no`."""
    org = json.loads(json.dumps(ORG))
    org["rol_por_alias"]["backend"] = "plataforma"      # reasignado por el organigrama
    org["jerarquia"]["plataforma"] = {"reporta_a": "cto", "capa": "ejecucion"}
    (tmp_path / "org.json").write_text(json.dumps(org))
    s = construir(tmp_path, monkeypatch, roster=ROSTER,
                  extra_env={"LLMINBOX_ROLES_ALIAS": str(tmp_path / "org.json")})
    (tmp_path / "DEMO-LEDGER.md").write_text(
        "### [cto-A → backend · FYI] correo real a ese nombre\ncuerpo\n")
    sec = _seis(_doctor(s))
    fila = next(ln for ln in sec.splitlines() if ln.strip().startswith("plataforma"))
    campos = fila.split()
    assert campos[5] == "sí", f"enrutable: su nombre SÍ es vocabulario del parser: {fila}"
    assert campos[7] == "sí", f"correo: hay una entrada dirigida a `backend`: {fila}"
