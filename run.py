# run.py

from app import app
from waitress import serve

print("[RUN] Serving via Waitress on http://0.0.0.0:5001")
serve(app, host='0.0.0.0', port=5001)
