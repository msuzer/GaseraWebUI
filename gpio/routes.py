from flask import Blueprint, request, jsonify
from .gpio_control import gpio
from .motor_control import motor

gpio_bp = Blueprint("control", __name__)

@gpio_bp.route("/api/gpio", methods=["GET", "POST"])
def api_gpio():
    try:
        result = gpio.dispatch(request.args["pin"], request.args["action"])
        return jsonify({"pin": request.args["pin"], "value": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# motor state: idle, moving, timeout, limit, user_stop, unknown
@gpio_bp.route("/motor/status", methods=["GET"])
def motor_status():
    return jsonify({
        "0": motor.state("0"),
        "1": motor.state("1")
    })

@gpio_bp.route("/motor/jog/<action>", methods=["POST"])
def motor_jog(action):
    motor_id = request.form.get("motor_id")
    direction = request.form.get("direction")

    if motor_id not in {"0", "1"} or direction not in {"cw", "ccw"}:
        return jsonify({"error": "Invalid motor or direction"}), 400

    try:
        if action == "start":
            motor.start(motor_id, direction)
        elif action == "stop":
            motor.stop(motor_id)
        else:
            return jsonify({"error": "Unknown action"}), 400
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

