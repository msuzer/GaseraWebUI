# run.py
import os
import logging
from waitress import serve
from app import app  # triggers DB create_all() via app.py

# Basic logging to stdout (systemd will capture)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

host = os.getenv("FLASK_HOST", "0.0.0.0")
port = int(os.getenv("FLASK_PORT", "5001"))

# Tuning knobs (safe defaults for OPiZ3)
threads = int(os.getenv("WAITRESS_THREADS", "6"))          # 4–8 is fine on OPiZ3
backlog = int(os.getenv("WAITRESS_BACKLOG", "128"))
inbuf  = int(os.getenv("WAITRESS_INBUF", "1048576"))       # 1 MB
outbuf = int(os.getenv("WAITRESS_OUTBUF", "1048576"))      # 1 MB
conn_timeout = int(os.getenv("WAITRESS_CONNECTION_TIMEOUT", "30"))

print(f"[RUN] Waitress on http://{host}:{port} (threads={threads})")
serve(
    app,
    host=host,
    port=port,
    threads=threads,
    backlog=backlog,
    inbuf_overflow=inbuf,
    outbuf_overflow=outbuf,
    connection_limit=1000,
    channel_timeout=conn_timeout,
)
