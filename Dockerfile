# ── etapa 1: la interfaz ──────────────────────────────────────────────────────
# Se compila DENTRO de la imagen, así que quien la usa sigue haciendo
# `docker compose up` y nada más — no necesita Node, ni pnpm, ni saber que esto
# es React. El autohospedaje no se pierde por tener una etapa de compilación:
# se perdería por depender de un CDN en tiempo de ejecución, y no hay ninguno.
FROM node:24-slim AS web
WORKDIR /web
RUN corepack enable
COPY web/package.json web/pnpm-lock.yaml web/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY web/ ./
RUN pnpm build

# ── etapa 2: el servicio ──────────────────────────────────────────────────────
FROM python:3.13-slim

# Sin compilador ni ruedas nativas: fastapi + uvicorn + pydantic bastan, y el
# índice va sobre el sqlite3 de la stdlib. Imagen pequeña = arranque rápido =
# el servicio se puede matar y levantar sin ceremonia (propiedad T5).
RUN pip install --no-cache-dir "fastapi==0.121.*" "uvicorn[standard]==0.39.*" "pydantic==2.*"

WORKDIR /app
COPY ledger_parse.py servicio.py ui.html /app/
# La interfaz compilada en la etapa anterior. `ui.html` se conserva como
# respaldo sin build — si algún día la etapa de Node falla, el servicio sigue
# sirviendo una interfaz usable en vez de una página en blanco.
COPY --from=web /static /app/static

# No corre como root: el bind-mount de los ledgers es de escritura y un servicio
# que puede reescribir el canon de la flota no necesita además ser root.
RUN useradd -u 1000 -m llmi && mkdir -p /data && chown llmi /data /app
USER llmi

EXPOSE 8077
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s \
  CMD python3 -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8077/health',timeout=2).status==200 else 1)"

CMD ["uvicorn", "servicio:app", "--host", "0.0.0.0", "--port", "8077", "--log-level", "warning"]
