# run.py

import os
from app import app, print_usage

print_usage()

MODE = os.getenv("GASERA_MODE", "dev")

if MODE == "prod":
    from waitress import serve
    print("[RUN] Serving via Waitress on http://0.0.0.0:5001")
    serve(app, host='0.0.0.0', port=5001)
else:
    print("[RUN] Serving Flask dev server on http://127.0.0.1:5001")
    app.run(host='127.0.0.1', port=5001)
