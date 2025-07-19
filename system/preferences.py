import json
from pathlib import Path

# --- Preference Keys ---
KEY_CHART_UPDATE_INTERVAL = "chart_update_interval"
KEY_MEASUREMENT_DURATION = "measurement_duration"
KEY_MOTOR_TIMEOUT = "motor_timeout"

class Preferences:
    def __init__(self, filename="config/user_prefs.json"):
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

    def set_int(self, key, value: int):
        self.set(key, int(value))

    def set_float(self, key, value: float):
        self.set(key, float(value))

    def set_str(self, key, value: str):
        self.set(key, str(value))

    def set_bool(self, key, value: bool):
        self.set(key, bool(value))

    def all(self):
        return dict(self.data)

    def as_dict(self):
        return self.all()

    def update_from_dict(self, updates: dict):
        for key, value in updates.items():
            if key in [KEY_MEASUREMENT_DURATION, KEY_MOTOR_TIMEOUT, KEY_CHART_UPDATE_INTERVAL]:
                self.set(key, value)

prefs = Preferences()