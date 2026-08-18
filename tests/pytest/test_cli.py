"""C — el CLI `llmi`, ejecutado DE VERDAD (subprocess), contra un stub HTTP.

El review×3 lo dejó escrito: toda la lógica nueva del CLI (①  exit 4 vía
`_get_inbox_o_422`, ③ `--carril`/`BIK_CARRIL`) estaba sin ningún test, y el
falsador era directo — «revertir el caso `422)` a la rama `*)` y nada lo
detecta». Estos tests corren el script real por `LLMINBOX_API` (env var que el
propio `llmi` respeta desde su línea 18), no una reimplementación en Python:
un test del CLI que no ejecuta el CLI es teatro.

`HOME` apunta al tmp del test: el token real de `~/.llminbox.token` no se lee
ni viaja — el stub no valida credencial.
"""
from __future__ import annotations

import http.server
import json
import os
import subprocess
import threading
from pathlib import Path

import pytest

LLMI = str(Path(__file__).resolve().parents[2] / "llmi")

# Formato EXACTO del pie de producción (servicio.py, final de inbox()):
# `marcar leído — pega esto tal cual:` + POST + una línea JSON. La primera
# versión de este stub inventó un formato propio (`marcar leído: … → k:v`)
# que casaba con el sed VIEJO del CLI — el test pasaba mientras producción
# no avanzaba un solo cursor. Un stub que no habla como el servidor real
# certifica un CLI que no funciona: cazado por el falsador vivo de ③.
CUERPO_OK = (
    "── demo-ledger · 1 de 1 para ti ──\n"
    "  abc123 #5 L10 2026-08-10T12:00:00 cto-A [REQUEST]\n"
    "    ### [cto-A → backend · REQUEST] primera\n"
    "\n\nmarcar leído — pega esto tal cual:\n"
    "  POST /inbox/ok/leido\n"
    '  {"hasta":{"demo-ledger":5,"otro-ledger":9}}\n'
)


class _Stub(http.server.BaseHTTPRequestHandler):
    """200 para 'ok', 422 para 'malo' — las dos ramas que el CLI debe DISTINGUIR.
    Los POST de /leido se graban en `server.posts` para poder afirmar cabeceras."""

    def _json(self, cod, obj):
        cuerpo = json.dumps(obj).encode()
        self.send_response(cod)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        if self.path == "/health":
            return self._json(200, {"ok": True})
        if self.path.startswith("/inbox/malo"):
            return self._json(422, {"detail": "'malo' no resuelve en el censo — date de alta o revisa el nombre"})
        if self.path.startswith("/inbox/malcarril"):
            cuerpo = CUERPO_OK.replace("/inbox/ok/leido", "/inbox/malcarril/leido").encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)
            return
        if self.path.startswith("/inbox/ok"):
            cuerpo = CUERPO_OK.encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)
            return
        self._json(404, {"detail": "?"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        self.server.posts.append({"path": self.path, "headers": dict(self.headers),
                                  "body": self.rfile.read(n).decode()})
        if self.path.startswith("/inbox/malcarril/"):
            # El 422 de carril del servidor real (fail-closed de ③), para probar
            # que el CLI lo DICE en vez de tragárselo.
            return self._json(422, {"detail": "carril 'novale' no resuelve a ningún ledger de este servicio (válidos: ['demo'])"})
        self._json(200, {"ok": True})

    def log_message(self, *a):  # silencio: el ruido del stub no es del test
        pass


@pytest.fixture
def stub():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Stub)
    srv.posts = []
    hilo = threading.Thread(target=srv.serve_forever, daemon=True)
    hilo.start()
    yield srv
    srv.shutdown()


def _llmi(args, tmp_path, api, extra_env=None):
    env = {"HOME": str(tmp_path), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
           "LLMINBOX_API": api}
    if extra_env:
        env.update(extra_env)
    return subprocess.run([LLMI, *args], capture_output=True, text=True,
                          timeout=30, env=env)


def test_peek_200_exit_0(stub, tmp_path):
    """FALSADOR: si `_get_inbox_o_422` perdiera el cuerpo (p.ej. borrando el
    tmp antes del cat), stdout saldría vacío con rc=0 y esto lo vería."""
    r = _llmi(["peek", "ok"], tmp_path, f"http://127.0.0.1:{stub.server_port}")
    assert r.returncode == 0
    assert "demo-ledger" in r.stdout


def test_peek_422_exit_4_con_mensaje(stub, tmp_path):
    """El falsador literal del review×3: revertir el caso `422)` a la rama `*)`
    colapsa esto en rc=3 «servicio ausente» — y este test se pone rojo."""
    r = _llmi(["peek", "malo"], tmp_path, f"http://127.0.0.1:{stub.server_port}")
    assert r.returncode == 4
    assert "malo" in r.stderr
    assert "no responde" not in r.stderr   # 422 NO es «servicio caído»


def test_servicio_caido_exit_3(tmp_path):
    """La otra dirección de la misma bifurcación: sin nadie escuchando, rc=3 y
    el mensaje de siempre — no un 4 que culparía al censo de una caída."""
    r = _llmi(["peek", "ok"], tmp_path, "http://127.0.0.1:1")   # puerto reservado, nadie escucha
    assert r.returncode == 3
    assert "no responde" in r.stderr


def test_carril_se_propaga_al_leido(stub, tmp_path):
    """③ de punta a punta por el CLI real: `--carril demo` debe llegar como
    cabecera `X-Llminbox-Carril` en el POST /leido — que es el ÚNICO sitio
    donde el carril decide algo (el GET muestra todo por diseño). El body es
    el `hasta` COMPLETO del pie del servicio, con los ledgers de fuera del
    carril incluidos: el recorte lo hace el SERVIDOR por la cabecera (probado
    en test_carril.py), no este script.

    FALSADOR doble: sin la rama `--carril` del parseo, el POST llega sin
    cabecera; y con la extracción del pie rota (el sed viejo que buscaba un
    formato inexistente), el POST no llega — `leidos` vacío lo delata."""
    r = _llmi(["inbox", "ok", "--carril", "demo"], tmp_path,
              f"http://127.0.0.1:{stub.server_port}")
    assert r.returncode == 0
    leidos = [p for p in stub.posts if p["path"].endswith("/leido")]
    assert leidos, "el CLI no llegó a marcar leído — la extracción del pie está rota"
    assert leidos[0]["headers"].get("X-Llminbox-Carril") == "demo"
    assert json.loads(leidos[0]["body"]) == {"hasta": {"demo-ledger": 5, "otro-ledger": 9}}
    assert "cursor avanzado" in r.stdout


def test_bik_carril_equivale_al_flag(stub, tmp_path):
    """`BIK_CARRIL` (el banner de sesión) debe pesar lo mismo que `--carril`."""
    r = _llmi(["inbox", "ok"], tmp_path, f"http://127.0.0.1:{stub.server_port}",
              extra_env={"BIK_CARRIL": "demo"})
    assert r.returncode == 0
    leidos = [p for p in stub.posts if p["path"].endswith("/leido")]
    assert leidos and leidos[0]["headers"].get("X-Llminbox-Carril") == "demo"


def test_carril_sin_valor_uso_limpio_exit_2(tmp_path):
    """El bug encontrado por el review×3: `--carril` como último token hacía
    `carril="$2"` con `$2` sin asignar — bajo `set -u`, un error crudo de bash.
    Debe ser mal-uso normal: rc=2 y mensaje que diga qué falta.

    FALSADOR: revertir el guard `[ $# -ge 2 ]` devuelve el «unbound variable»
    y el rc≠2, y las dos aserciones caen."""
    r = _llmi(["inbox", "ok", "--carril"], tmp_path, "http://127.0.0.1:1")
    assert r.returncode == 2
    assert "--carril necesita un valor" in r.stderr
    assert "unbound" not in r.stderr


def test_carril_invalido_el_cli_lo_dice_y_exit_4(stub, tmp_path):
    """El 422 del POST /leido (carril que no resuelve) llega al operador: detail
    a stderr y exit 4 — ni el ok:true de antes del fix del servidor, ni el
    silencio del `curl -sf` de después.

    FALSADOR: con el `curl -sf` mudo anterior, esto salía rc=0 sin una palabra."""
    r = _llmi(["inbox", "malcarril", "--carril", "novale"], tmp_path,
              f"http://127.0.0.1:{stub.server_port}")
    assert r.returncode == 4
    assert "novale" in r.stderr


# ── identidad derivada de la sesión tmux ─────────────────────────────────────
# Las 45 sesiones de la flota se llaman `<rol>-<carril>` (`backend-64bis`,
# `cfo-guardian-PM`…). Es la identidad ESTABLE: sobrevive al reinicio de Claude,
# al contrario que la dirección de peer (`cto-biklabs-97`), cuyo sufijo cambia.
# Todo error de identidad de la semana nació de TECLEAR; esto lo deriva.

def _yo_y_carril(sesion, carriles=("64bis", "PM", "cfocockpit", "bikeus",
                                   "biklabs-landing", "llminbox")):
    """Réplica EXACTA del corte del CLI, para poder falsarlo aquí: el sufijo se
    casa contra los carriles conocidos, NO por el primer guión — hay roles con
    guión (`cfo-guardian-64bis`, `db-migrations-PM`) y cortar por el primero
    devolvería rol='cfo' carril='guardian-64bis'."""
    for c in carriles:
        if sesion.endswith("-" + c):
            return sesion[: -len(c) - 1], c
    return None


@pytest.mark.parametrize("sesion,rol,carril", [
    ("backend-64bis", "backend", "64bis"),
    ("cfo-guardian-PM", "cfo-guardian", "PM"),          # rol CON guión
    ("db-migrations-64bis", "db-migrations", "64bis"),  # rol con guión, otro carril
    ("wiki-vault-bikeus", "wiki-vault", "bikeus"),
    ("sdet-PM", "sdet", "PM"),
])
def test_la_sesion_da_rol_y_carril(sesion, rol, carril):
    """Los cinco casos son nombres REALES de `tmux list-sessions` (2026-08-16).

    FALSADOR: cortar por el primer guión da `cfo`/`guardian-PM` y este test lo ve.
    """
    assert _yo_y_carril(sesion) == (rol, carril)


def test_una_sesion_que_no_es_de_carril_no_resuelve():
    """CONTROL NEGATIVO: si el nombre no acaba en un carril conocido, NO se
    inventa identidad — se devuelve nada y el CLI pide el argumento de siempre.
    Adivinar la identidad es exactamente lo que produce huérfanas."""
    assert _yo_y_carril("una-sesion-cualquiera") is None
    assert _yo_y_carril("64bis") is None          # sin rol delante


def test_sin_tmux_el_cli_no_cambia_de_conducta(stub, tmp_path):
    """Fuera de tmux (cron, `claude --bg`, un shell suelto) la derivación no
    aplica y `peek` sin argumento sigue dando uso + rc=2, como siempre.

    FALSADOR: si la derivación se colara con `$TMUX` vacío, esto daría rc≠2."""
    env = dict(os.environ)
    env.pop("TMUX", None)
    r = subprocess.run([LLMI, "peek"], capture_output=True, text=True, timeout=30,
                       env={**env, "HOME": str(tmp_path), "PATH": "/usr/bin:/bin",
                            "LLMINBOX_API": f"http://127.0.0.1:{stub.server_port}"})
    assert r.returncode == 2


# ── la forma GNU: pedir ayuda es un uso CORRECTO ─────────────────────────────
# `llmi --help` salía con rc=2 («mal uso») y la ayuda por stdout, y el mal uso
# TAMBIÉN por stdout. Las dos mitades del contrato estaban cruzadas, y no es
# cosmética: `llmi --help || die` mataba el script en el caso bueno, y
# `llmi inbox 2>/dev/null | procesa` se comía la pantalla de uso como si fuera
# datos. La prueba de que dolió está en la propia BD de producción: entre los
# 101 nombres FUERA DEL CENSO con bandeja hay uno llamado `--help` — alguien
# escribió `llmi inbox --help` y el CLI lo tomó por el nombre de un agente.

def test_ayuda_pedida_sale_por_stdout_con_rc_0(tmp_path):
    """FALSADOR: hoy `--help` sale rc=2. Y el puerto muerto prueba lo segundo —
    si la ayuda tocara la red, esto sería rc=3."""
    r = _llmi(["--help"], tmp_path, "http://127.0.0.1:1")
    assert r.returncode == 0
    assert "llmi — consulta la red de ledgers" in r.stdout
    assert r.stderr == ""


def test_sin_comando_es_mal_uso_y_no_ensucia_stdout(tmp_path):
    """La otra mitad: invocar sin comando SÍ es mal uso — rc=2 y la pantalla por
    stderr, para que un `llmi ... | procesa` no la lea como datos.

    FALSADOR: hoy la misma llamada imprime el uso por STDOUT; la aserción de
    stdout vacío cae."""
    r = _llmi([], tmp_path, "http://127.0.0.1:1")
    assert r.returncode == 2
    assert r.stdout == ""
    assert "llmi — consulta la red de ledgers" in r.stderr


def test_comando_desconocido_tambien_por_stderr(tmp_path):
    """Control de que lo anterior no es un caso suelto: TODO mal uso va a stderr."""
    r = _llmi(["nombre-que-no-existe"], tmp_path, "http://127.0.0.1:1")
    assert r.returncode == 2
    assert r.stdout == ""
    assert "comando desconocido" in r.stderr


def test_ayuda_de_subcomando_no_se_toma_por_un_nombre_de_agente(tmp_path):
    """El mecanismo que metió `--help` en el censo de producción: `llmi inbox
    --help` caía en el bucle de argumentos, `--help` acababa en `args` y salía
    pedido como `/inbox/--help`.

    FALSADOR con puerto muerto: si `--help` volviera a tratarse como nombre, el
    CLI intentaría hablar con el servicio y saldría rc=3 «no responde». rc=0 sin
    tocar la red es la única forma de pasar."""
    for sub in ("inbox", "peek", "to"):
        r = _llmi([sub, "--help"], tmp_path, "http://127.0.0.1:1")
        assert r.returncode == 0, f"{sub} --help → rc={r.returncode}: {r.stderr}"
        assert "llmi — consulta la red de ledgers" in r.stdout
        assert "no responde" not in r.stderr


def test_peek_mal_uso_no_se_disfraza_de_servicio_caido(tmp_path):
    """`peek` comprobaba que el servicio estaba vivo ANTES de mirar sus propios
    argumentos, al revés que `inbox`. Con el servicio caído, `peek --carril` (sin
    valor) contestaba rc=3 «no responde»: culpaba al contenedor de un error de
    teclado, y el rc=2 que este PR acaba de fijar no llegaba a existir.

    FALSADOR: devolver el `vivo` a su sitio anterior da rc=3 y las dos
    aserciones de abajo caen a la vez."""
    r = _llmi(["peek", "--carril"], tmp_path, "http://127.0.0.1:1")
    assert r.returncode == 2
    assert "--carril necesita un valor" in r.stderr
    assert "no responde" not in r.stderr
