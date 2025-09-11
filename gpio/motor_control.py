import time
from threading import Thread, RLock
from .gpio_control import gpio
from system.preferences import prefs, KEY_MOTOR_TIMEOUT
from config.constants import (
    DEBOUNCE_INTERVAL,
    DEFAULT_MOTOR_TIMEOUT,
    BUTTON0_PIN, BUTTON1_PIN,
    BUTTON2_PIN, BUTTON3_PIN,
    MOTOR0_CW_PIN, MOTOR0_CCW_PIN,
    MOTOR1_CW_PIN, MOTOR1_CCW_PIN,
    MOTOR0_LIMIT_PIN, MOTOR1_LIMIT_PIN
)

BUTTONS = [BUTTON0_PIN, BUTTON1_PIN, BUTTON2_PIN, BUTTON3_PIN]

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
        self._state = {
            "0": {"status": "idle", "direction": None},
            "1": {"status": "idle", "direction": None}
        }
        self._lock = {"0": RLock(), "1": RLock()}
        self._threads = {}
        self._last_state = [1, 1, 1, 1]      # last stable levels (1=released, 0=pressed)
        self._last_change = [0, 0, 0, 0]     # timestamps

    def set_timeout(self, seconds):
        self.timeout_sec = int(seconds or DEFAULT_MOTOR_TIMEOUT)

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
        lock = self._lock[motor_id]
        with lock:
            if self._state[motor_id]["status"] == "moving":
                print(f"[WARN] Motor {motor_id} already moving")
                return

            key = f"motor{motor_id}_{direction}"
            if key not in self.pins:
                raise ValueError("Invalid motor or direction")

            if self.is_limit_hit(motor_id, direction):
                print(f"[LIMIT] Motor {motor_id} {direction.upper()} blocked by limit switch.")
                self._state[motor_id] = {"status": "limit", "direction": direction}
                return

            self.stop(motor_id)

            gpio.dispatch(self.pins[key], "set")
            self._state[motor_id] = {"status": "moving", "direction": direction}
            print(f"[MOTOR] Started motor {motor_id} {direction.upper()}")

            t = Thread(target=self._monitor, args=(motor_id, direction), daemon=True)
            t.start()
            self._threads[motor_id] = t

    def stop(self, motor_id: str):
        for dir in ["cw", "ccw"]:
            key = f"motor{motor_id}_{dir}"
            if key in self.pins:
                gpio.dispatch(self.pins[key], "reset")
        if self._state[motor_id]["status"] == "moving":
            direction = self._state[motor_id]["direction"]
            self._state[motor_id] = {"status": "user_stop", "direction": direction}
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
                self._state[motor_id] = {"status": "limit", "direction": direction}
                return
            if self._state[motor_id]["status"] != "moving":
                return
            time.sleep(0.1)
        self.stop(motor_id)
        self._state[motor_id] = {"status": "timeout", "direction": direction}

    def status(self, motor_id: str) -> str:
        state = self._state.get(motor_id)
        if not state:
            return "unknown"
        status = state["status"]
        direction = state["direction"]
        return f"{status} {direction}" if direction else status

    def state(self, motor_id: str) -> dict:
        return self._state.get(motor_id, {"status": "unknown", "direction": None})

    def is_done(self, motor_id: str) -> bool:
        return self._state[motor_id]["status"] in ["limit", "timeout", "user_stop", "idle"]

    def are_both_done(self) -> bool:
        return self.is_done("0") and self.is_done("1")
    
        # --- buttons → motors (debounced) ---

    def _debounce_snapshot(self):
        """Return stable [b0,b1,b2,b3] (0=pressed, 1=released) using DEBOUNCE_INTERVAL (ms)."""
        now_ms = time.time() * 1000.0
        stable = self._last_state[:]  # start with last known stable

        for i, pin in enumerate(BUTTONS):
            raw = gpio.read(pin)  # 0=pressed, 1=released (active-low)
            if raw != self._last_state[i]:
                # edge detected: start/continue timing
                if self._last_change[i] == 0:
                    self._last_change[i] = now_ms
                elif now_ms - self._last_change[i] >= DEBOUNCE_INTERVAL:
                    # accept new stable level
                    self._last_state[i] = raw
                    stable[i] = raw
                    self._last_change[i] = 0
            else:
                # no raw change: clear timer
                self._last_change[i] = 0

        return stable

    def on_button_edge(self):
        """Edge-triggered button handling (called periodically)."""
        prev_state = self._last_state[:]
        stable = self._debounce_snapshot()

        for i in range(4):
            if stable[i] != prev_state[i]:
                # Detect falling edge (press)
                motor_id = "0" if i in [0, 1] else "1"
                direction = "cw" if i in [0, 2] else "ccw"
                if stable[i] == 0:
                    # Button pressed → start motor
                    if not (self._state[motor_id]["status"] == "moving" and self._state[motor_id]["direction"] == direction):
                        self.start(motor_id, direction)
                elif stable[i] == 1:
                    # Button released → stop motor if it's the one started by this button
                    if self._state[motor_id]["status"] == "moving":
                        self.stop(motor_id)

    def button_loop(self, period_s: float = 0.01):
        """Optional helper to run in a thread: debounced polling loop."""
        while True:
            # self.poll_buttons()
            self.on_button_edge()
            time.sleep(period_s)

# lazy singleton instance
motor = MotorController()

from system.preferences import prefs, KEY_MOTOR_TIMEOUT
prefs.register_callback(KEY_MOTOR_TIMEOUT, motor.set_timeout)

# stop both motors on boot
motor.stop_both()

# e.g., start the polling loop in a background thread
Thread(target=motor.button_loop, daemon=True).start()
