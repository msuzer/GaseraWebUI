import time
import threading
import re
from gpio.motor_control import motor
from gpio.gpio_control import gpio
from .controller import gasera
from system.preferences import prefs, KEY_MEASUREMENT_DURATION
from config.constants import (TRIGGER_PIN, DEBOUNCE_INTERVAL, MEASUREMENT_CHECK_INTERVAL, DEFAULT_MEASUREMENT_DURATION)
from .async_timer_bank import AsyncTimerBank
import system.log_utils as log

class MeasurementController:
    class State:
        IDLE = 'idle'
        CHECK_GASERA_STATUS = 'check_gasera_status'
        MOVING_TO_PROBE = 'moving_to_probe'
        MOVING_TO_PROBE_DONE = 'moving_to_probe_done'
        START_MEASUREMENT = 'start_measurement'
        GASERA_MEASURES = 'gasera_measures'
        STOP_MEASUREMENT = 'stop_measurement'
        MOVING_HOME = 'moving_home'
        MOVING_HOME_DONE = 'moving_home_done'
        CLEAN_UP_STATE = 'clean_up_state'

    def __init__(self):
        self.measurement_duration_sec: int = prefs.get_int(KEY_MEASUREMENT_DURATION, DEFAULT_MEASUREMENT_DURATION)
        self.state = self.State.IDLE
        self.last_event = None
        self.wait_seconds: int = 0
        self.task_triggered = False
        self.lock = threading.Lock()
        self.timers = AsyncTimerBank()
        self._last_trigger_time = 0
        self._last_trigger_state = 1  # assume HIGH at rest
        self._status_retry_count = 0

    def set_timeout(self, seconds):
        self.measurement_duration_sec = int(seconds or DEFAULT_MEASUREMENT_DURATION)

    def get_timeout(self):
        return self.measurement_duration_sec

    def check_hw_trigger(self):
        now = time.monotonic()
        current = gpio.read(TRIGGER_PIN)
        if self._last_trigger_state == 1 and current == 0:
            if now - self._last_trigger_time >= DEBOUNCE_INTERVAL:
                self._last_trigger_time = now
                if self.state == self.State.IDLE:
                    self.trigger("HW")
                else:
                    self.set_abort()
        self._last_trigger_state = current

    def trigger(self, source: str = "API"):
        with self.lock:
            if gasera.check_device_connection() is False:
                self.last_event = log.warn("Cannot trigger measurement: Gasera not connected")
                return self.last_event
            if self.state == self.State.IDLE:
                self.task_triggered = True
                msg = f"{source} Trigger Received! Starting measurement sequence..."
                self.last_event = log.info(msg, sound="triggered")
                return self.last_event
            elif self.state == self.State.GASERA_MEASURES:
                self.last_event = log.warn("Measurement already in progress")
                return self.last_event
            else:
                msg = f"Cannot trigger measurement from state {self.state}"
                self.last_event = log.error(msg)
                return self.last_event

    def set_abort(self):
        with self.lock:
            if self.state != self.State.IDLE:
                self.task_triggered = False
                self.last_event = log.warn("Aborting Measurement Sequence!", sound="cancel")
                if self.state in {self.State.START_MEASUREMENT, self.State.GASERA_MEASURES} :
                    self.transition(self.State.STOP_MEASUREMENT, delay=2.0)
                elif self.state in {self.State.MOVING_TO_PROBE, self.State.MOVING_TO_PROBE_DONE}:
                    self.transition(self.State.MOVING_HOME, delay=1.0)
                elif self.state in {self.State.CHECK_GASERA_STATUS}:
                    self.transition(self.State.CLEAN_UP_STATE, delay=1.0)
                return self.last_event
            else:
                self.last_event = log.info("Gasera already IDLE")
                return self.last_event

    def launch_tick_loop(self, interval=0.5):
        if hasattr(self, '_tick_thread') and self._tick_thread.is_alive():
            return  # already running

        def loop():
            while True:
                self.check_hw_trigger()
                self.tick()
                time.sleep(interval)

        self._tick_thread = threading.Thread(target=loop, daemon=True)
        self._tick_thread.start()

    def tick(self):
        if self.state == self.State.IDLE:
            if self.task_triggered:
                self._status_retry_count = 0
                self.transition(self.State.CHECK_GASERA_STATUS, delay=1.0)
                self.last_event = log.info("Checking Gasera status...")
        elif self.state == self.State.CHECK_GASERA_STATUS:
            if self.timers.expired("device_status"):
                status = gasera.get_device_status()
                status_str = status.status_str if status else "No Response"
                if "IDLE" in status_str.upper():
                    self.last_event = log.info("Gasera is IDLE.")
                    self.transition(self.State.MOVING_TO_PROBE, delay=1.0)
                else:
                    self._status_retry_count += 1
                    if self._status_retry_count >= 3:
                        self.last_event = log.error(f"Gasera not ready after multiple attempts: {status_str}. Aborting.")
                        self.state = self.State.CLEAN_UP_STATE
                    else:
                        self.last_event = log.warn(f"Gasera not ready: {status_str}. Retrying...")
                        self.timers.restart("device_status", 2.0)
        elif self.state == self.State.MOVING_TO_PROBE:
            motor.start_both("cw")
            self.last_event = log.info("Moving to probe...")
            self.transition(self.State.MOVING_TO_PROBE_DONE)
        elif self.state == self.State.MOVING_TO_PROBE_DONE:
            if motor.are_both_done():
                self.last_event = log.info("Reached probe position. Starting measurement...")
                self.transition(self.State.START_MEASUREMENT, delay=2.0)
        elif self.state == self.State.START_MEASUREMENT:
            if self.timers.expired("device_status"):
                resp = gasera.start_measurement()
                if resp:
                    self.last_event = log.info("Measurement started.")
                    self.wait_seconds = self.measurement_duration_sec
                    self.transition(self.State.GASERA_MEASURES, delay=MEASUREMENT_CHECK_INTERVAL)
                else:
                    self.last_event = log.error("Measurement start failed")
                    self.transition(self.State.MOVING_HOME, delay=2.0)
        elif self.state == self.State.GASERA_MEASURES:
            if self.timers.expired("measurement_timer"):
                self.wait_seconds -= MEASUREMENT_CHECK_INTERVAL
                if self.wait_seconds > 0:
                    minutes, seconds = divmod(self.wait_seconds, 60)
                    self.last_event = log.info(f"Gasera is Measuring... Remaining Time: {minutes:02}:{seconds:02}")
                    self.timers.restart("measurement_timer", MEASUREMENT_CHECK_INTERVAL)
                else:
                    self.last_event = log.info("Measurement duration complete. Stopping measurement...")
                    self.transition(self.State.STOP_MEASUREMENT, delay=2.0)
        elif self.state == self.State.STOP_MEASUREMENT:
            if self.timers.expired("abort_wait"):
                resp = gasera.stop_measurement()
                if resp:
                    self.last_event = log.info("Measurement stopped.")
                else:
                    self.last_event = log.error("Measurement stop failed!")
                self.last_event = log.info("Returning to home position...")
                self.transition(self.State.MOVING_HOME, delay=1.0)
        elif self.state == self.State.MOVING_HOME:
            motor.start_both("ccw")
            self.transition(self.State.MOVING_HOME_DONE)
        elif self.state == self.State.MOVING_HOME_DONE:
            if motor.are_both_done():
                self.last_event = log.info("Measurement sequence complete!")
                self.transition(self.State.CLEAN_UP_STATE, delay=1.0)
        elif self.state == self.State.CLEAN_UP_STATE:
            self.last_event = log.info("Returning to IDLE.")
            self.task_triggered = False
            self._status_retry_count = 0
            self.state = self.State.IDLE

    def transition(self, new_state, delay=0.0):
        log.verbose(f"Transitioning to: {new_state}", flush=True)
        self.state = new_state
        if new_state == self.State.CHECK_GASERA_STATUS:
            self.timers.start("device_status", delay)
        elif new_state == self.State.START_MEASUREMENT:
            self.timers.start("device_status", delay)
        elif new_state == self.State.GASERA_MEASURES:
            self.timers.start("measurement_timer", delay)
        elif new_state == self.State.STOP_MEASUREMENT:
            self.timers.start("abort_wait", delay)
    
    def get_status(self):
        return {
            "state": clean_text(self.state),
            "last_event": self.last_event
        }

# Utility function to clean text for JSON serialization
def clean_text(s):
    # Replace each special char (_ - + *) with a space
    return re.sub(r'[_\-\+\*]', ' ', s)

# Instantiate and launch measurement controller
measurement = MeasurementController()
measurement.launch_tick_loop()
prefs.register_callback(KEY_MEASUREMENT_DURATION, measurement.set_timeout)
