from flask import Blueprint, Response, json, render_template, request, jsonify
from gasera import GaseraCommandDispatcher
from gasera import MeasurementController
from system.preferences import prefs
from system.preferences import (KEY_CHART_UPDATE_INTERVAL, KEY_MEASUREMENT_DURATION, KEY_MOTOR_TIMEOUT)
from .controller import gasera
from .commands import GASERA_COMMANDS
from gpio.motor_control import motor
from datetime import datetime
from config.constants import DEFAULT_CHART_UPDATE_DURATION
import random, time

gasera_bp = Blueprint("gasera", __name__)

# Device setup (customize IP/port)
measurement = MeasurementController(gasera)
dispatcher = GaseraCommandDispatcher(gasera)

from system.preferences import prefs, KEY_MEASUREMENT_DURATION
prefs.register_callback(KEY_MEASUREMENT_DURATION, measurement.set_timeout)

@gasera_bp.route("/command_map.js")
def serve_command_map():
    filtered = {
        k: {kk: vv for kk, vv in v.items() if kk != "handler"}
        for k, v in GASERA_COMMANDS.items()
    }
    return Response(f"const commandMap = {json.dumps(filtered)};", mimetype="application/javascript")

# --- Measurement control (trigger, abort, settings) ---
@gasera_bp.route("/api/measurement/start", methods=["POST"])
def gasera_api_start_measurement():
    try:
        measurement.trigger()
        return jsonify({"status": "started"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@gasera_bp.route("/api/measurement/abort", methods=["POST"])
def gasera_api_abort_measurement():
    measurement.set_abort()
    return jsonify({"ok": True, "message": "Abort signal sent."})

@gasera_bp.route("/api/measurement/state")
def gasera_api_measurement_state():
    return jsonify(measurement.get_status())

@gasera_bp.route("/api/connection_status")
def gasera_api_connection_status():
    return jsonify({"online": gasera.check_device_connection()})

@gasera_bp.route("/api/data/server")
def gasera_api_data_server():
    return jsonify(gasera.acon_proxy())

@gasera_bp.route("/api/data/dummy")
def gasera_api_data_dummy():
    timestamp = int(time.time())
    components = [
        {"cas": "74-82-8",     "name": "CH₄",       "label": "Methane (CH₄)",         "color": "#1f77b4", "ppm": round(random.uniform(0.8, 1.2), 3)},
        {"cas": "124-38-9",    "name": "CO₂",       "label": "Carbon Dioxide (CO₂)",  "color": "#ff7f0e", "ppm": round(random.uniform(400, 430), 2)},
        {"cas": "7732-18-5",   "name": "H₂O",       "label": "Water Vapor (H₂O)",     "color": "#2ca02c", "ppm": round(random.uniform(7000, 7500), 1)},
        {"cas": "630-08-0",    "name": "CO",        "label": "Carbon Monoxide (CO)",  "color": "#d62728", "ppm": round(random.uniform(0.0, 1.0), 3)},
        {"cas": "10024-97-2",  "name": "N₂O",       "label": "Nitrous Oxide (N₂O)",    "color": "#9467bd", "ppm": round(random.uniform(0.0, 0.5), 2)},
        {"cas": "7664-41-7",   "name": "NH₃",       "label": "Ammonia (NH₃)",          "color": "#8c564b", "ppm": round(random.uniform(0.001, 0.01), 4)},
        {"cas": "7446-09-5",   "name": "SO₂",       "label": "Sulfur Dioxide (SO₂)",  "color": "#e377c2", "ppm": round(random.uniform(0.0, 0.5), 2)},
        {"cas": "7782-44-7",   "name": "O₂",        "label": "Oxygen (O₂)",            "color": "#7f7f7f", "ppm": round(random.uniform(200000, 210000), 0)},
        {"cas": "75-07-0",     "name": "CH₃CHO",    "label": "Acetaldehyde (CH₃CHO)", "color": "#bcbd22", "ppm": round(random.uniform(0.0, 0.1), 3)},
        {"cas": "64-17-5",     "name": "C₂H₅OH",    "label": "Ethanol (C₂H₅OH)",       "color": "#17becf", "ppm": round(random.uniform(0.0, 0.5), 2)},
        {"cas": "67-56-1",     "name": "CH₃OH",     "label": "Methanol (CH₃OH)",       "color": "#a05d56", "ppm": round(random.uniform(0.0, 0.5), 2)},
    ]

    return jsonify({
        "timestamp": timestamp,
        "readable": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S"),
        "components": components
    })

@gasera_bp.route("/api/settings/read", methods=["GET"])
def gasera_api_read_settings():
    return jsonify(prefs.as_dict())

@gasera_bp.route("/api/settings/update", methods=["POST"])
def gasera_api_update_settings_all():
    data = request.get_json(force=True)
    try:
        prefs.update_from_dict(data)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# API dispatcher
@gasera_bp.route("/api/dispatch/instruction", methods=["POST"])
def gasera_api_dispatch_instruction():
    try:
        data = request.get_json(force=True)
        cmd = data.get("cmd")
        args = data.get("args", [])
        result = dispatcher.handle(cmd, args)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Optional serial hook
@gasera_bp.route("/api/test/serial")
def gasera_api_test_serial():
    test_line = "get_status"
    result = dispatcher.handle(test_line.strip().split()[0])
    return result.get("string", str(result))
