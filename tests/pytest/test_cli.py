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
import subprocess
import threading
from pathlib import Path

import pytest

LLMI = str(Path(__file__).resolve().parents[2] / "llmi")

CUERPO_OK = (
    "── demo-ledger · 1 de 1 para ti ──\n"
    "  abc123 #5 L10 2026-08-10T12:00:00 cto-A [REQUEST]\n"
    "    ### [cto-A → backend · REQUEST] primera\n"
    "· marcar leído: POST → demo-ledger:5\n"
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
    donde el carril decide algo (el GET muestra todo por diseño).

    FALSADOR: si el parseo de `--carril` se tragara el flag sin propagarlo
    (args+=() sin la rama), el POST llegaría sin cabecera y esto lo vería."""
    r = _llmi(["inbox", "ok", "--carril", "demo"], tmp_path,
              f"http://127.0.0.1:{stub.server_port}")
    assert r.returncode == 0
    leidos = [p for p in stub.posts if p["path"].endswith("/leido")]
    assert leidos, "el CLI no llegó a marcar leído"
    assert leidos[0]["headers"].get("X-Llminbox-Carril") == "demo"
    assert json.loads(leidos[0]["body"]) == {"hasta": {"demo-ledger": 5}}


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
