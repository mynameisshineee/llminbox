FROM python:3.13-slim

# Sin compilador ni ruedas nativas: fastapi + uvicorn + pydantic bastan, y el
# índice va sobre el sqlite3 de la stdlib. Imagen pequeña = arranque rápido =
# el servicio se puede matar y levantar sin ceremonia (propiedad T5).
RUN pip install --no-cache-dir "fastapi==0.121.*" "uvicorn[standard]==0.39.*" "pydantic==2.*"

WORKDIR /app
COPY ledger_parse.py servicio.py ui.html /app/

# No corre como root: el bind-mount de los ledgers es de escritura y un servicio
# que puede reescribir el canon de la flota no necesita además ser root.
RUN useradd -u 1000 -m llmi && mkdir -p /data && chown llmi /data /app
USER llmi

EXPOSE 8077
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s \
  CMD python3 -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8077/health',timeout=2).status==200 else 1)"

CMD ["uvicorn", "servicio:app", "--host", "0.0.0.0", "--port", "8077", "--log-level", "warning"]
