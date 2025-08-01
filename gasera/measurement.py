import time
import threading
from gpio.motor_control import motor
from gpio.gpio_control import gpio
from system.preferences import prefs
from system.preferences import KEY_MEASUREMENT_DURATION
from config.constants import (TRIGGER_PIN, BUZZER_PIN, DEBOUNCE_INTERVAL, MEASUREMENT_CHECK_INTERVAL, DEFAULT_MEASUREMENT_DURATION)
from .async_timer_bank import AsyncTimerBank
from .controller import GaseraController

class MeasurementController:
    class State:
        IDLE = 'idle'
        QUERY_STATUS = 'query_status'
        MOVING_TO_PROBE = 'moving_to_probe'
        START_MEASUREMENT = 'start_measurement'
        WAIT_FOR_MEASUREMENT = 'wait_for_measurement'
        STOP_MEASUREMENT = 'stop_measurement'
        MOVING_HOME = 'moving_home'
        ABORTED = 'aborted'

    def __init__(self, gasera: GaseraController):
        self.measurement_duration_sec: int = prefs.get_int(KEY_MEASUREMENT_DURATION, DEFAULT_MEASUREMENT_DURATION)
        self.gasera = gasera
        self.state = self.State.IDLE
        self.last_event = None
        self.abort_flag = False
        self.wait_seconds: int = 0
        self.task_triggered = False
        self.lock = threading.Lock()
        self.timers = AsyncTimerBank()
        self._last_trigger_time = 0
        self._last_trigger_state = 1  # assume HIGH at rest

    def set_timeout(self, seconds):
        self.measurement_duration_sec = int(seconds or DEFAULT_MEASUREMENT_DURATION)

    def get_timeout(self):
        return self.measurement_duration_sec

    def check_trigger(self):
        now = time.monotonic()
        current = gpio.read(TRIGGER_PIN)
        if self._last_trigger_state == 1 and current == 0:
            if now - self._last_trigger_time >= DEBOUNCE_INTERVAL:
                self.log("[TRIGGER] Falling edge with debounce passed.")
                self._last_trigger_time = now
                self.trigger()
        self._last_trigger_state = current

    def trigger(self):
        with self.lock:
            if self.state == self.State.IDLE:
                self.log("[INFO] Trigger received. Scheduling measurement.")
                self.task_triggered = True
                return True
            else:
                self.log("[WARN] Measurement already in progress.")
                return False

    def set_abort(self):
        with self.lock:
            self.abort_flag = self.state != self.State.IDLE

    def launch_tick_loop(self, interval=0.2):
        if hasattr(self, '_tick_thread') and self._tick_thread.is_alive():
            return  # already running

        def loop():
            while True:
                self.check_trigger()
                self.tick()
                time.sleep(interval)

        self._tick_thread = threading.Thread(target=loop, daemon=True)
        self._tick_thread.start()

    def tick(self):
        if self.state == self.State.IDLE:
            if self.task_triggered:
                self.task_triggered = False
                self.transition(self.State.QUERY_STATUS, delay=0.1)
        elif self.state == self.State.QUERY_STATUS:
            if self.timers.expired("device_status"):
                status = self.gasera.get_device_status()
                if status and "IDLE" in status.status_str.upper():
                    motor.start_both("cw")
                    self.state = self.State.MOVING_TO_PROBE
                else:
                    self.log("[INFO] Waiting for Gasera to become idle...")
                    self.timers.restart("device_status", 1.0)
        elif self.state == self.State.MOVING_TO_PROBE:
            if motor.are_both_done():
                self.transition(self.State.START_MEASUREMENT, delay=1.0)
        elif self.state == self.State.START_MEASUREMENT:
            if self.timers.expired("device_status"):
                resp = self.gasera.start_measurement()
                if resp:
                    self.wait_seconds = self.measurement_duration_sec
                    self.transition(self.State.WAIT_FOR_MEASUREMENT, delay=10.0)
                else:
                    self.notify_error("Measurement start failed")
                    self.transition(self.State.STOP_MEASUREMENT, delay=2.0)
        elif self.state == self.State.WAIT_FOR_MEASUREMENT:
            if self.abort_flag:
                self.transition(self.State.STOP_MEASUREMENT, delay=1.0)
                return
            if self.timers.expired("measurement_timer"):
                self.wait_seconds -= MEASUREMENT_CHECK_INTERVAL
                if self.wait_seconds > 0:
                    minutes, seconds = divmod(self.wait_seconds, 60)
                    self.log(f"[INFO] Measuring... remaining: {minutes:02}:{seconds:02}")
                    self.timers.restart("measurement_timer", MEASUREMENT_CHECK_INTERVAL)
                else:
                    self.transition(self.State.STOP_MEASUREMENT, delay=1.0)
        elif self.state == self.State.STOP_MEASUREMENT:
            if self.timers.expired("abort_wait"):
                self.gasera.stop_measurement()
                motor.start_both("ccw")
                self.state = self.State.MOVING_HOME
        elif self.state == self.State.MOVING_HOME:
            if motor.are_both_done():
                self.log("[INFO] Measurement complete.")
                self.state = self.State.IDLE
                self.abort_flag = False

    def transition(self, new_state, delay=0.0):
        self.log(f"[STATE] Transitioning to: {new_state}")
        self.state = new_state
        if new_state == self.State.QUERY_STATUS:
            self.timers.start("device_status", delay)
        elif new_state == self.State.START_MEASUREMENT:
            self.timers.start("device_status", delay)
        elif new_state == self.State.WAIT_FOR_MEASUREMENT:
            self.timers.start("measurement_timer", delay)
        elif new_state == self.State.STOP_MEASUREMENT:
            self.timers.start("abort_wait", delay)

    def notify_error(self, msg):
        gpio.dispatch(BUZZER_PIN, "set")
        time.sleep(0.5)
        gpio.dispatch(BUZZER_PIN, "reset")
        self.log(f"[ERROR] {msg}")

    def log(self, msg):
        self.last_event = f"{msg}"
        print(self.last_event)

    def get_status(self):
        return {
            "state": self.state,
            "last_event": self.last_event
        }
