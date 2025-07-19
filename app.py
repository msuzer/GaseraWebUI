from flask import Flask, render_template
import os

app = Flask(__name__)

from gpio.routes import gpio_bp
from system.routes import system_bp
from gasera.routes import gasera_bp

app.register_blueprint(gasera_bp, url_prefix="/gasera")
app.register_blueprint(system_bp, url_prefix="/system")
app.register_blueprint(gpio_bp, url_prefix="/gpio")

@app.route('/')
def index():
    return render_template('index.html')

# Shared launch instructions
def print_usage():
    print("\n--- GaseraWebUI Launcher ---")
    print(f"GASERA_MODE: {os.getenv('GASERA_MODE', 'dev')}")
    print("Run options:")
    print("  python run.py               # Flask dev server")
    print("  GASERA_MODE=prod run.py     # Production via Waitress")
    print("-----------------------------\n")

if __name__ == '__main__':
    print_usage()
    app.run(host='127.0.0.1', port=5001)
