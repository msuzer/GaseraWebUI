from flask import Blueprint, Response, json, request, jsonify
from gasera import GaseraCommandDispatcher
from gasera import MeasurementController
from system.preferences import prefs
from system.preferences import KEY_MEASUREMENT_DURATION
from .controller import gasera
from .commands import GASERA_COMMANDS
from datetime import datetime
from .config import get_cas_details
import random, time

gasera_bp = Blueprint("gasera", __name__)

# Device setup (customize IP/port)
measurement = MeasurementController(gasera)
measurement.launch_tick_loop()
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
        msg = measurement.trigger()
        return jsonify({"message": msg}), 200
    except Exception as e:
        return jsonify({"message": f"Trigger error: {e}"}), 500

@gasera_bp.route("/api/measurement/abort", methods=["POST"])
def gasera_api_abort_measurement():
    try:
        msg = measurement.set_abort()
        return jsonify({"message": msg}), 200
    except Exception as e:
        return jsonify({"message": f"[ERROR] Abort failed: {e}"}), 500

@gasera_bp.route("/api/measurement/state")
def gasera_api_measurement_state():
    return jsonify(measurement.get_status())

@gasera_bp.route("/api/connection_status")
def gasera_api_connection_status():
    return jsonify({"online": gasera.check_device_connection()})

@gasera_bp.route("/api/data/dummy")
def gasera_api_data_dummy():
    timestamp = int(time.time())
    # choose some CAS you like; keep your existing set if you want
    dummy_specs = [
        ("74-82-8",  round(random.uniform(0.8, 1.2), 4)),      # CH₄
        ("124-38-9", round(random.uniform(400, 430), 4)),      # CO₂
        ("7732-18-5",round(random.uniform(7000, 7500), 4)),    # H₂O
        ("10024-97-2",round(random.uniform(0.0, 0.5), 4)),     # N₂O
        ("7664-41-7",round(random.uniform(0.001, 0.01), 4)),   # NH₃
    ]

    components = []
    lines = []
    readable = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

    for cas, ppm in dummy_specs:
        d = get_cas_details(cas) or {}
        symbol = d.get("symbol") or cas
        label  = d.get("label") or cas
        color  = d.get("color") or "#999999"
        components.append({
            "cas": cas,
            "name": symbol,   # e.g., "CH₄"
            "label": label,   # e.g., "Methane (CH₄, 74-82-8)"
            "color": color,
            "ppm": float(f"{ppm:.4f}"),
        })
        # build the pretty line exactly like ACONResult.as_string()
        lines.append(f"{label}: {ppm:.4f} ppm")

    pretty = "Measurement Results (" + readable + "):\n" + "\n".join(lines)

    return jsonify({
        "timestamp": timestamp,
        "readable": readable,
        "string": pretty,        # ← identical shape/format to real endpoint
        "components": components
    })

@gasera_bp.route("/api/data/live")
def gasera_api_data_live():
    result = gasera.acon_proxy()

    # Success path: dict, no error, has components
    if isinstance(result, dict) and not result.get("error") and result.get("components"):
        if "string" not in result:
            lines = [f"{c['label']}: {float(c['ppm']):.4f} ppm" for c in result["components"]]
            result["string"] = f"Measurement Results ({result['readable']}):\n" + "\n".join(lines)
        return jsonify(result), 200

    # Any non-data case → return a single-line message (200)
    msg = "No measurement data yet"
    if isinstance(result, dict) and result.get("error"):
        msg = str(result["error"])
    elif result is None:
        msg = "No response from device"
    elif not isinstance(result, dict):
        msg = "Unexpected upstream response"

    return jsonify({"message": msg}), 200

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
