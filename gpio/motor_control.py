import time
from threading import Thread, Lock
from .gpio_control import gpio
from system.preferences import prefs, KEY_MOTOR_TIMEOUT
from config.constants import (
    DEFAULT_MOTOR_TIMEOUT,
    MOTOR0_CW_PIN, MOTOR0_CCW_PIN,
    MOTOR1_CW_PIN, MOTOR1_CCW_PIN,
    MOTOR0_LIMIT_PIN, MOTOR1_LIMIT_PIN
)

class MotorController:
    def __init__(self):
        self.timeout_sec = prefs.get_int(KEY_MOTOR_TIMEOUT, DEFAULT_MOTOR_TIMEOUT)
        self.pins = {
            "motor0_cw": MOTOR0_CW_PIN,
            "motor0_ccw": MOTOR0_CCW_PIN,
            "motor1_cw": MOTOR1_CW_PIN,
            "motor1_ccw": MOTOR1_CCW_PIN,
        }
        self.limit_switches = {
            "0": MOTOR0_LIMIT_PIN,
            "1": MOTOR1_LIMIT_PIN,
        }
        self._state = { "0": "idle", "1": "idle" }
        self._lock = Lock()
        self._threads = {}

    def set_timeout(self, seconds):
        self.timeout_sec = float(seconds or DEFAULT_MOTOR_TIMEOUT)
        prefs.set(KEY_MOTOR_TIMEOUT, self.timeout_sec)

    def get_timeout(self):
        return self.timeout_sec

    def is_limit_hit(self, motor_id, direction):
        pin = self.limit_switches.get(motor_id)
        if not pin:
            return False
        if motor_id == "0" and direction == "cw" and gpio.read(pin) == 0:
            return True
        if motor_id == "1" and direction == "ccw" and gpio.read(pin) == 0:
            return True
        return False

    def start(self, motor_id: str, direction: str):
        if self._state[motor_id] == "moving":
            print(f"[WARN] Motor {motor_id} already moving")
            return

        key = f"motor{motor_id}_{direction}"
        if key not in self.pins:
            raise ValueError("Invalid motor or direction")

        if self.is_limit_hit(motor_id, direction):
            print(f"[LIMIT] Motor {motor_id} {direction.upper()} blocked by limit switch.")
            self._state[motor_id] = "limit"
            return

        self.stop(motor_id)

        gpio.dispatch(self.pins[key], "set")
        self._state[motor_id] = "moving"
        print(f"[MOTOR] Started motor {motor_id} {direction.upper()}")

        t = Thread(target=self._monitor, args=(motor_id, direction), daemon=True)
        t.start()
        self._threads[motor_id] = t

    def stop(self, motor_id: str):
        for dir in ["cw", "ccw"]:
            key = f"motor{motor_id}_{dir}"
            if key in self.pins:
                gpio.dispatch(self.pins[key], "reset")
        if self._state[motor_id] == "moving":
            self._state[motor_id] = "user_stop"
            print(f"[MOTOR] Stopped motor {motor_id} manually.")

    def start_both(self, direction: str):
        self.start("0", direction)
        self.start("1", direction)

    def stop_both(self):
        self.stop("0")
        self.stop("1")

    def _monitor(self, motor_id: str, direction: str):
        pin = self.limit_switches.get(motor_id)
        start = time.time()
        while time.time() - start < self.timeout_sec:
            if gpio.read(pin) == 0:
                self.stop(motor_id)
                self._state[motor_id] = "limit"
                return
            if self._state[motor_id] != "moving":
                return
            time.sleep(0.1)
        self.stop(motor_id)
        self._state[motor_id] = "timeout"

    def status(self, motor_id: str) -> str:
        return self._state.get(motor_id, "unknown")

    def is_done(self, motor_id: str) -> bool:
        return self._state[motor_id] in ["limit", "timeout", "user_stop", "idle"]

    def are_both_done(self) -> bool:
        return self.is_done("0") and self.is_done("1")

# lazy singleton instance
motor = MotorController()

# stop both motors on boot
motor.stop_both()