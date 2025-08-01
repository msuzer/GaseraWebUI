import json
from pathlib import Path

# --- Preference Keys ---
VALID_PREF_KEYS = [
    "chart_update_interval",
    "measurement_duration",
    "motor_timeout",
    "track_visibility",
]

KEY_CHART_UPDATE_INTERVAL = VALID_PREF_KEYS[0]
KEY_MEASUREMENT_DURATION  = VALID_PREF_KEYS[1]
KEY_MOTOR_TIMEOUT         = VALID_PREF_KEYS[2]
KEY_TRACK_VISIBILITY      = VALID_PREF_KEYS[3]

class Preferences:
    def __init__(self, filename="config/user_prefs.json"):
        self._callbacks = {}
        self.file = Path(filename)
        self.data = {}
        self._load()

    def _load(self):
        if self.file.exists():
            try:
                self.data = json.loads(self.file.read_text())
            except Exception:
                self.data = {}
        else:
            self.data = {}

    def _save(self):
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(self.data, indent=2))

    def register_callback(self, key, callback):
        if key not in self._callbacks:
            self._callbacks[key] = []
        self._callbacks[key].append(callback)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def get_int(self, key, default=0) -> int:
        value = self.data.get(key, default)
        return int(value)

    def get_float(self, key, default=0.0) -> float:
        value = self.data.get(key, default)
        return float(value)

    def get_str(self, key, default="") -> str:
        value = self.data.get(key, default)
        return str(value)

    def get_bool(self, key, default=False) -> bool:
        value = self.data.get(key, default)
        return bool(int(value)) if isinstance(value, str) else bool(value)

    def set(self, key, value):
        self.data[key] = value
        self._save()
        if key in self._callbacks:
            for cb in self._callbacks[key]:
                try:
                    cb(value)
                except Exception as e:
                    print(f"[WARN] Callback for '{key}' failed: {e}")

    def set_int(self, key, value: int):
        self.set(key, int(value))

    def set_float(self, key, value: float):
        self.set(key, float(value))

    def set_str(self, key, value: str):
        self.set(key, str(value))

    def set_bool(self, key, value: bool):
        self.set(key, bool(value))

    def get_dict(self, key, default=None) -> dict:
        value = self.data.get(key, default or {})
        return dict(value) if isinstance(value, dict) else {}

    def all(self):
        return dict(self.data)
    
    def as_dict(self):
        return self.all()

    def update_from_dict(self, updates: dict):
        for key, value in updates.items():
            if key in VALID_PREF_KEYS:
                self.set(key, value)

prefs = Preferences()