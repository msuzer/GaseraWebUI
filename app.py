import atexit
import time
from flask import Flask, render_template
from buzzer.buzzer_facade import buzzer

# Power-on tone on import (works for both dev and waitress)
buzzer.play("power_on")

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

def _play_shutdown():
    try:
        buzzer.play("shutdown")
        time.sleep(1.0)  # let the tone sound before loop stops
    except Exception:
        pass

# Register after imports so it runs in both dev and waitress
atexit.register(_play_shutdown)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001)
