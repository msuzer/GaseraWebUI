from flask import Flask, render_template
import system.log_utils as log

log.info("starting service", version="1.0.0", sound="power_on")

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

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001)
