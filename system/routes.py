from flask import Blueprint, render_template, jsonify, request
from system.info import get_system_info
from system.preferences import prefs

system_bp = Blueprint("system", __name__)

@system_bp.route("/api")
def api_sysinfo():
    return jsonify(get_system_info())

@system_bp.route("/prefs", methods=["GET"])
def get_preferences():
    return jsonify(prefs.as_dict())

@system_bp.route("/prefs", methods=["POST"])
def update_preferences():
    data = request.get_json(force=True)
    try:
        prefs.update_from_dict(data)
        return jsonify({"ok": True, "message": "Preferences updated."})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
