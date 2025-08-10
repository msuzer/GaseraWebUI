from flask import Flask, render_template
import os

from api import api as api_bp
from storage.db import engine, remove_session
from storage.models import create_all

app = Flask(__name__)

from gpio.routes import gpio_bp
from system.routes import system_bp
from gasera.routes import gasera_bp

# Ensure DB tables exist when the web app starts (safe if already created)
create_all(engine)

# Blueprints
app.register_blueprint(gasera_bp, url_prefix="/gasera")
app.register_blueprint(system_bp, url_prefix="/system")
app.register_blueprint(gpio_bp, url_prefix="/gpio")
app.register_blueprint(api_bp, url_prefix="/api")

# Clean up SQLAlchemy scoped_session per request
@app.teardown_appcontext
def _shutdown_session(exception=None):
    remove_session()

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    host = os.getenv("FLASK_HOST", "0.0.0.0")  # 0.0.0.0 is convenient on OPiZ3
    port = int(os.getenv("FLASK_PORT", "5001"))
    app.run(host=host, port=port)
