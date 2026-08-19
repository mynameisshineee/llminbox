"""Ningún bind-mount de FICHERO ÚNICO en la composición de Docker.

Nace de un fallo de producción del 2026-08-18 y de su repetición evitada:

`roles-por-alias.json` estaba montado como fichero suelto. El host lo reemplazó
por rename —que es como se DEBE escribir un fichero de forma atómica: tmp + mv—,
el bind-mount se quedó clavado al INODO borrado, y `/organigrama` sirvió DOS DÍAS
un organigrama viejo sin avisar. Nadie lo notó porque el fallo no da error: da
datos, y son plausibles.

Un mount de DIRECTORIO no tiene el problema: la resolución del nombre se rehace en
cada `open()`, así que un rename encima se ve inmediatamente.

Esto es la invariante, no el recordatorio. Un comentario pide que alguien se
acuerde; un test falla solo cuando alguien no se acuerda.

⛔ LO QUE ESTE GUARDA NO CUBRE, dicho aquí para que su nombre no prometa de más:
   un fichero SIN EXTENSIÓN montado a un destino SIN EXTENSIÓN es indistinguible
   de un directorio mirando sólo la sintaxis, y mirar el disco no vale — en CI las
   rutas del host no existen y un guarda que sólo funciona en una máquina no
   guarda nada. Cubre las dos formas de Compose (corta y larga) y cualquier
   extremo con extensión conocida. El hueco queda escrito, no tapado.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
# SÓLO lo versionado. `docker-compose.override.yml` es GENERADO y está en
# `.gitignore` junto a `roster.json` y `.llmi-mounts.json`: en un checkout limpio
# no existe, así que exigirle propiedades desde aquí hacía que el test demostrase
# localmente algo que en CI no podía demostrar — verde en mi máquina, rojo en el
# runner, y la propiedad sin verificar en ninguno de los dos.
#
# Tres contratos distintos, tres niveles (el CI los encontró mezclados):
#
#   ① el PARSER y los canarios  → fixtures sintéticos, herméticos
#   ② la composición PUBLICADA  → docker-compose.yml y nada más
#   ③ el override GENERADO      → se ejecuta el generador en un tmp y se mira
#                                  su salida; así una regresión de `llmi init`
#                                  también se pone roja
COMPOSES = ("docker-compose.yml",)

# Extensiones que delatan un FICHERO. Se miran los DOS extremos: un `source` sin
# extensión con `target: /censo.json` sigue siendo un mount de fichero.
EXT_DE_FICHERO = (".json", ".tsv", ".md", ".yml", ".yaml", ".txt", ".env",
                  ".sqlite", ".db", ".sh", ".py", ".token", ".log", ".csv")

# ── RIESGO ACEPTADO TEMPORALMENTE ────────────────────────────────────────────
# No es «exento = seguro». Es un riesgo vivo con su ficha:
#
#   single-file mount ................ sí
#   protección mecánica contra rename . NO
#   invariante operativa ............. el ledger es append-only y se escribe con
#                                      `>>` en sitio, nunca con tmp+mv
#   consecuencia si se viola ......... inodo rancio en silencio, sin un error
#
# No se arregla montando su directorio: cada ledger vive en la raíz de un repo
# distinto y expondría nueve proyectos dentro del contenedor. La excepción se
# apoya en una DISCIPLINA, no en un mecanismo — y por eso v0.3.1 debe ligarla
# formalmente al guarda que sostiene esa disciplina (`guard-ledger-append-only`):
# si ese guarda se desactiva o deja de cubrir tmp+mv, ESTA excepción debería
# ponerse roja. Hoy sólo está documentada; esa dependencia no es demostrable
# desde aquí, y decir lo contrario sería el mismo defecto que el guarda persigue.
#
# Casa ORIGEN y DESTINO, no un prefijo suelto: `/ledgers/` a secas perdonaría
# cualquier fichero futuro que alguien meta ahí.
RIESGO_ACEPTADO = (
    (re.compile(r"/LEDGER[\w.-]*\.md$"),
     re.compile(r"^/ledgers/[\w.-]+\.md$"),
     "ledgers: append-only en sitio (disciplina, no mecanismo) — ver v0.3.1"),
)


def _aceptado(origen: str, destino: str) -> str | None:
    return next((m for o, d, m in RIESGO_ACEPTADO
                 if o.search(origen) and d.match(destino)), None)


def _montajes(texto: str):
    """(origen, destino) de cada volumen, en las DOS formas de Compose.

    La forma larga es Compose perfectamente válido:

        - type: bind
          source: ./roster.json
          target: /censo.json

    Un guarda que sólo mira la forma corta se puede rodear sin querer, y entonces
    su nombre promete una clase que no cubre. Ignora volúmenes nombrados.
    """
    lineas = texto.splitlines()
    i = 0
    while i < len(lineas):
        ln = lineas[i]
        m = re.match(r"(\s*)-\s*(.*)$", ln)
        if not m:
            i += 1
            continue
        sangria, resto = len(m.group(1)), m.group(2)
        # ── forma larga: el item abre un MAPA. Se acepta cualquier clave y
        #    cualquier ORDEN — exigir que empiece por `type:` hacía que un
        #    montaje perfectamente válido con las claves en otro orden fuera
        #    invisible, y un guarda que se rodea sin querer da permiso.
        if re.match(r"[A-Za-z_][\w-]*\s*:", resto):
            bloque = [resto]
            j = i + 1
            while j < len(lineas):
                sig = lineas[j]
                if not sig.strip():
                    j += 1
                    continue
                sang_sig = len(sig) - len(sig.lstrip())
                if sang_sig <= sangria and re.match(r"\s*-\s", sig):
                    break
                if sang_sig <= sangria:
                    break
                bloque.append(sig.strip())
                j += 1
            texto_bloque = "\n".join(bloque)
            src = re.search(r"source\s*:\s*[\"\']?([^\"\'\n]+)", texto_bloque)
            dst = re.search(r"target\s*:\s*[\"\']?([^\"\'\n]+)", texto_bloque)
            if src and dst:
                yield src.group(1).strip(), dst.group(1).strip()
            i = j
            continue
        # ── forma corta ──
        c = re.match(r'"?([^":]+):([^":]+?)(?::(ro|rw))?"?\s*$', resto)
        if c:
            origen, destino = c.group(1).strip(), c.group(2).strip()
            if "/" in origen or "." in origen:      # no es un volumen nombrado
                yield origen, destino
        i += 1


def _es_fichero(origen: str, destino: str) -> bool:
    return (origen.lower().endswith(EXT_DE_FICHERO)
            or destino.lower().endswith(EXT_DE_FICHERO))


def test_ningun_bind_mount_de_fichero_unico():
    """② La composición PUBLICADA — sólo lo que está en Git.

    FALSADOR: devolver `- ./roster.json:/censo.json:ro` —en cualquiera de las dos
    formas— pone esto rojo con el nombre del fichero."""
    culpables = []
    for nombre in COMPOSES:
        ruta = RAIZ / nombre
        if not ruta.exists():
            continue                      # el override es local, puede no estar
        for origen, destino in _montajes(ruta.read_text()):
            if _es_fichero(origen, destino) and not _aceptado(origen, destino):
                culpables.append(f"{nombre}: {origen} → {destino}")
    assert not culpables, (
        "bind-mount de FICHERO ÚNICO — se ata al inodo y el host puede jubilarlo "
        "con un rename, dejando al contenedor leyendo bytes muertos para siempre "
        "(pasó el 2026-08-18 con roles-por-alias.json: 2 días sirviendo un "
        "organigrama viejo, sin error). Monta el DIRECTORIO y apunta la ruta "
        "dentro:\n  " + "\n  ".join(culpables))


FIXTURE = """services:
  x:
    volumes:
      - llminbox-data:/data
      - "./algo:/repo:ro"
      - "/host/roles.json:/shared/roles.json:ro"
      - type: bind
        source: ./roster.json
        target: /censo.json
        read_only: true
"""


def test_el_parser_ve_las_dos_formas_y_no_confunde_volumenes_nombrados():
    """CONTROL del parser, sobre un fixture SINTÉTICO — no sobre ficheros que en
    CI pueden no existir. Si el parser no reconociera ningún volumen, el guarda
    pasaría siempre: verde por no mirar, que es el modo de fallo más caro de este
    repo y tiene su propia cicatriz.

    Antes este control leía la composición real, incluido el override GENERADO.
    En CI ese fichero no existe (`.gitignore`), así que el test demostraba
    localmente una propiedad que en el runner no podía demostrar. Lo cazó el CI,
    no yo."""
    vistos = list(_montajes(FIXTURE))
    assert ("llminbox-data", "/data") not in vistos, "cuenta un volumen NOMBRADO"
    assert ("./algo", "/repo") in vistos, f"pierde la forma corta: {vistos}"
    assert ("/host/roles.json", "/shared/roles.json") in vistos, vistos
    assert ("./roster.json", "/censo.json") in vistos, f"pierde la forma larga: {vistos}"
    assert any(not _es_fichero(o, d) for o, d in vistos), "no ve ningún directorio"


CANARIO_CORTO = '      - "./roster.json:/censo.json:ro"\n'
# Origen SIN extensión, destino con ella: sigue siendo un mount de fichero, y
# mirar sólo el origen lo dejaba pasar. El mutante que quitaba el destino de la
# comprobación sobrevivía porque en las composiciones de hoy los dos extremos
# tienen extensión — el hueco existía y no había forma de verlo.
CANARIO_SIN_EXT_EN_ORIGEN = '      - "./censo:/censo.json:ro"\n'
CANARIO_LARGO = """      - type: bind
        source: ./roster.json
        target: /censo.json
        read_only: true
"""
# El MISMO montaje con las claves en otro orden. Es Compose igual de válido, y el
# parser anterior no lo veía porque exigía que el item empezara por `type:`.
CANARIO_LARGO_DESORDENADO = """      - read_only: true
        target: /censo.json
        source: ./roster.json
        type: bind
"""


def test_el_canario_se_caza_en_LAS_DOS_formas():
    """El guarda de la lista de excepciones Y del parser, que son los dos sitios
    donde un guarda se muere en silencio.

    · Una excepción puede ensancharse hasta tragárselo todo.
    · Un parser que sólo entiende la forma corta deja pasar la larga, que es
      Compose igual de válido. El mutante existía: reescribir el canario en forma
      larga sobrevivía al guarda anterior.
    · Mirar sólo el ORIGEN deja pasar `./censo:/censo.json`, que es un mount de
      fichero con el origen disfrazado. Ese mutante también sobrevivía, porque en
      las composiciones de hoy los dos extremos llevan extensión.
    · Y exigir que el mapa empiece por `type:` hacía invisible el MISMO montaje
      con las claves en otro orden. El orden de las claves de un mapa YAML no
      significa nada; que decidiera si el guarda mira, sí.

    El canario es el montaje EXACTO que rompió el organigrama. Si deja de cazarse
    en cualquiera de las dos formas, el guarda ya no protege de la clase que su
    nombre promete."""
    for etiqueta, texto in (("corta", CANARIO_CORTO), ("larga", CANARIO_LARGO),
                            ("larga desordenada", CANARIO_LARGO_DESORDENADO),
                            ("sin extensión en el origen", CANARIO_SIN_EXT_EN_ORIGEN)):
        montajes = list(_montajes(texto))
        assert montajes, f"el parser no ve la forma {etiqueta}: {texto!r}"
        origen, destino = montajes[0]
        assert _es_fichero(origen, destino), f"forma {etiqueta}: {origen} → {destino}"
        assert _aceptado(origen, destino) is None, (
            f"un riesgo aceptado se tragó el canario en forma {etiqueta} "
            f"({origen} → {destino}): el guarda ya no protege de nada")


# ── ③ el override GENERADO ───────────────────────────────────────────────────

def test_el_generador_no_introduce_mounts_de_fichero_de_CONFIG(tmp_path):
    """El tercer contrato, y el único que puede hablar del override: no una copia
    estática, sino EJECUTAR el generador y mirar lo que produce. Así una regresión
    de `llmi init` —volver a montar un fichero de configuración suelto— también se
    pone roja.

    Corre hermético: se copia `llmi` a un tmp (su `DIR` sale de su propia ruta) y
    se le da un `HOME` propio, así que no toca el repo ni la máquina. Verificado
    antes de escribirlo, porque `llmi init` está marcado ⛔ en este repo por lo que
    destruye si se ejecuta en el sitio equivocado.

    FALSADOR: que el generador emita `- ./roster.json:/censo.json:ro` pone esto
    rojo — y ése es exactamente el montaje que rompió el organigrama."""
    import shutil
    import subprocess
    repo, casa = tmp_path / "repo", tmp_path / "home"
    repo.mkdir()
    casa.mkdir()
    for f in ("llmi", "docker-compose.yml", "roster.example.json"):
        shutil.copy(RAIZ / f, repo / f)
    (casa / "LEDGER.md").write_text("### [cto-A → backend · FYI] uno\ncuerpo\n")

    r = subprocess.run([str(repo / "llmi"), "init", "--demo"], cwd=repo,
                       env={"HOME": str(casa), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
                       capture_output=True, text=True, timeout=180, check=False)
    # EL CÓDIGO DE SALIDA, no sólo que el fichero exista. `check=False` calla a
    # Ruff y no demuestra nada: un generador que escribe el override y luego falla
    # dejaría este test en verde con el proceso roto.
    assert r.returncode == 0, f"`llmi init` salió {r.returncode}:\n{r.stdout}\n{r.stderr}"
    override = repo / "docker-compose.override.yml"
    assert override.exists(), f"el generador no produjo override:\n{r.stdout}{r.stderr}"

    montajes = list(_montajes(override.read_text()))
    assert montajes, "el override generado no trae volúmenes reconocibles"
    ficheros = [(o, d) for o, d in montajes if _es_fichero(o, d)]
    # Los ledgers SÍ salen como fichero — es el riesgo aceptado y documentado.
    # Cualquier OTRO fichero suelto es una regresión del generador.
    fuera = [f"{o} → {d}" for o, d in ficheros if not _aceptado(o, d)]
    assert not fuera, (
        "`llmi init` genera bind-mounts de FICHERO fuera del riesgo aceptado:\n  "
        + "\n  ".join(fuera))
    assert ficheros, "no generó NINGÚN mount de fichero: el control no mide nada"


def test_el_riesgo_aceptado_sigue_cubriendo_algo_real(tmp_path):
    """CONTROL del riesgo aceptado, y vive AQUÍ y no arriba: sólo se puede
    comprobar contra un override de verdad, y el único que este test puede exigir
    es el que él mismo genera.

    Un riesgo aceptado que ya no casa con nada es deuda invisible: parece cubrir
    algo, no cubre nada, y tapará el día que alguien reintroduzca ese montaje.

    FALSADOR: cuando los ledgers dejen de montarse como fichero —que es el
    objetivo— esto se pone rojo y obliga a RETIRAR la entrada."""
    import shutil
    import subprocess
    repo, casa = tmp_path / "repo", tmp_path / "home"
    repo.mkdir()
    casa.mkdir()
    for f in ("llmi", "docker-compose.yml", "roster.example.json"):
        shutil.copy(RAIZ / f, repo / f)
    (casa / "LEDGER.md").write_text("### [cto-A → backend · FYI] uno\ncuerpo\n")
    r = subprocess.run([str(repo / "llmi"), "init", "--demo"], cwd=repo,
                       env={"HOME": str(casa), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
                       capture_output=True, text=True, timeout=180, check=False)
    assert r.returncode == 0, f"`llmi init` salió {r.returncode}:\n{r.stdout}\n{r.stderr}"
    usados = {_aceptado(o, d) for o, d in _montajes(
        (repo / "docker-compose.override.yml").read_text()) if _es_fichero(o, d)}
    huerfanos = {m for _, _, m in RIESGO_ACEPTADO} - usados
    assert not huerfanos, (
        f"riesgos aceptados que ya no cubren nada: {sorted(huerfanos)} — retíralos "
        "en vez de dejarlos tapando algo que ya no existe")


def test_la_composicion_publicada_no_monta_el_checkout():
    """El perímetro de lectura del proceso, como propiedad y no como comentario.

    Mi primer intento montaba `.` entero para llegar a dos ficheros de estado. Eso
    da acceso a `.git` —historial completo, que puede contener secretos retirados
    en commits posteriores—, a los backups `*.bak-*` y al override con las rutas
    reales de nueve repos. `:ro` limita la escritura, no la lectura: un path
    traversal pasaría de alcanzar un fichero a alcanzar el checkout entero.

    FALSADOR: devolver `- .:/repo:ro` pone esto rojo. El directorio dedicado
    (`.llminbox-state/`, que `llmi up` rellena) cubre el mismo caso sin exponer
    el resto."""
    raiz = {".", "./", "..", "../"}
    culpables = [f"{o} → {d}" for o, d in _montajes((RAIZ / "docker-compose.yml").read_text())
                 if o.strip() in raiz]
    assert not culpables, (
        "la composición publicada monta el CHECKOUT ENTERO en el contenedor: "
        + ", ".join(culpables))


# Estado que produce `llmi up` DENTRO del repo. Estas variables no pueden quedar
# a merced del override: si el propio `up` deja el fichero, la composición
# publicada tiene que saber dónde está. Las demás (p. ej. `LLMINBOX_CARRILES`,
# que apunta a una ruta del host fuera del repo) sí son externas y se interpolan.
#
# La distinción no se puede inferir del texto — se declara aquí, que es donde se
# puede discutir.
ESTADO_INTERNO = ("LLMINBOX_ROSTER", "LLMINBOX_MOUNTS_JSON")


def _env_publicado(texto: str):
    """`CLAVE: valor` del bloque `environment:` de la composición publicada."""
    dentro = False
    for ln in texto.splitlines():
        if re.match(r"\s*environment\s*:\s*$", ln):
            dentro = True
            continue
        if dentro:
            if ln.strip() and not ln.startswith(" " * 6):
                dentro = False
                continue
            m = re.match(r'\s+([A-Z_][A-Z0-9_]*)\s*:\s*"?([^"\n#]*)"?\s*$', ln)
            if m:
                yield m.group(1), m.group(2).strip()


def test_ninguna_ruta_de_entorno_apunta_donde_no_hay_nada_montado():
    """El guarda de la clase, no del caso.

    `llmi up` empezó a dejar el mapa de montajes en `/state/mounts.json` y la
    composición publicada seguía con `LLMINBOX_MOUNTS_JSON` vacío por defecto:
    `_cargar_carriles()` devolvía {} aunque el fichero estuviera ahí. La variable
    no señalaba a ninguna parte y **nadie lo veía**, porque un mapa de carriles
    vacío degrada en silencio.

    La propiedad general: toda ruta ABSOLUTA fijada en la composición publicada
    tiene que caer dentro de algún destino montado. Las interpolaciones
    (`${VAR:-}`) se saltan: su valor lo pone el override, que no está versionado.

    FALSADOR: dejar `LLMINBOX_MOUNTS_JSON` vacío, o apuntarlo a `/mounts.json`
    sin montar nada ahí, pone esto rojo con el nombre de la variable."""
    texto = (RAIZ / "docker-compose.yml").read_text()
    destinos = [d for _, d in _montajes(texto)] + ["/data"]
    huerfanas = []
    for clave, valor in _env_publicado(texto):
        if not valor.startswith("/") or "${" in valor:
            continue
        if not any(valor == d or valor.startswith(d.rstrip("/") + "/") for d in destinos):
            huerfanas.append(f"{clave}={valor}")
    assert not huerfanas, (
        "variables de entorno que apuntan donde no hay nada montado — el servicio "
        f"degrada en silencio: {huerfanas}  (destinos montados: {sorted(set(destinos))})")


def test_el_lector_de_entorno_ve_de_verdad():
    """CONTROL: si `_env_publicado` no leyera nada, el test de arriba pasaría
    siempre. Verde por no mirar, otra vez."""
    claves = dict(_env_publicado((RAIZ / "docker-compose.yml").read_text()))
    assert "LLMINBOX_ROSTER" in claves, claves
    assert claves["LLMINBOX_ROSTER"].startswith("/"), claves


def test_el_estado_que_produce_llmi_up_no_queda_a_merced_del_override():
    """El agujero que dejó vivo el guarda anterior, y que CodeRabbit encontró:
    `llmi up` empezó a dejar el mapa de montajes en `/state/mounts.json` y la
    composición publicada seguía con `LLMINBOX_MOUNTS_JSON: "${...:-}"`. Una
    interpolación VACÍA apunta a ninguna parte, así que `_cargar_carriles()`
    devolvía {} con el fichero montado delante — y un mapa de carriles vacío
    degrada en SILENCIO.

    El guarda de rutas huérfanas no lo veía porque salta las interpolaciones, y
    saltarlas es correcto para las variables genuinamente externas. La diferencia
    hay que DECLARARLA: lo que `llmi up` produce dentro del repo no puede depender
    de un fichero que no está versionado.

    FALSADOR: devolver cualquiera de las dos a `"${VAR:-}"` pone esto rojo."""
    valores = dict(_env_publicado((RAIZ / "docker-compose.yml").read_text()))
    for clave in ESTADO_INTERNO:
        v = valores.get(clave, "")
        assert v and not v.startswith("${") and v.startswith("/"), (
            f"{clave}={v!r} — `llmi up` produce ese fichero dentro del repo, así que "
            "la composición PUBLICADA tiene que decir dónde está. Con una "
            "interpolación vacía el servicio degrada sin un solo error.")


def test_si_el_estado_no_se_puede_preparar_NO_se_levanta_el_contenedor(tmp_path):
    """FAIL-CLOSED de `llmi up`, con Docker falso para poder demostrarlo.

    El script lleva `set -uo pipefail`, **no** `set -e`: sin `|| exit` explícito,
    un `mkdir`/`cp` que falle sigue adelante y levanta el contenedor con el estado
    a medias — censo ausente, mapa de carriles vacío, todo degradando en silencio.
    Arrancar con el estado roto es peor que no arrancar.

    Se fuerza el fallo de la forma más simple y menos mágica: `.llminbox-state`
    existe como FICHERO, así que `mkdir -p` no puede crear el directorio.

    Y se pone un `docker` FALSO delante en el PATH que deja una marca al ser
    invocado. Comprobar sólo el código de salida no bastaría: lo que importa es
    que NO se llegue a Docker.

    FALSADOR: quitar los `|| exit 1` deja rc=0 (o el de docker) y, sobre todo,
    hace aparecer la marca — el contenedor se habría levantado."""
    import shutil
    import subprocess
    repo, casa, binfalso = tmp_path / "repo", tmp_path / "home", tmp_path / "bin"
    for d in (repo, casa, binfalso):
        d.mkdir()
    for f in ("llmi", "docker-compose.yml", "roster.example.json"):
        shutil.copy(RAIZ / f, repo / f)
    (repo / "roster.json").write_text('{"agentes": [], "humanos": [], "difusion": []}')
    (repo / ".llmi-mounts.json").write_text("{}")
    (casa / ".llminbox.token").write_text("token-de-prueba")
    marca = tmp_path / "docker-fue-invocado"
    (binfalso / "docker").write_text(f'#!/bin/sh\ntouch "{marca}"\nexit 0\n')
    (binfalso / "docker").chmod(0o755)
    # El estado NO se puede preparar: ya hay un fichero con ese nombre.
    (repo / ".llminbox-state").write_text("soy un fichero, no un directorio")

    r = subprocess.run([str(repo / "llmi"), "up"], cwd=repo,
                       env={"HOME": str(casa),
                            "PATH": f"{binfalso}:/usr/bin:/bin:/usr/sbin:/sbin"},
                       capture_output=True, text=True, timeout=120, check=False)
    assert r.returncode != 0, f"siguió adelante con el estado roto:\n{r.stdout}\n{r.stderr}"
    assert not marca.exists(), (
        "se invocó a Docker con el estado sin preparar: el contenedor habría "
        "arrancado con censo ausente y mapa de carriles vacío, degradando en "
        "silencio")
