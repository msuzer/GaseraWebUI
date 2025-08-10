from __future__ import annotations
import os, time, signal, logging, threading
from datetime import datetime, timezone
from typing import Optional, Tuple

# Use your high-level controller
from gasera.controller import GaseraController

# Storage layer
from storage.db import get_session, engine
from storage.models import create_all, DeviceStateLog, DeviceStatus, MeasurementPhase
from storage.ops import insert_cycle_with_values

# Optional CAS metadata helper
try:
    from gasera.config import get_cas_details
except Exception:
    get_cas_details = None

# ------------ Config ------------
POLL_MEASURING_SEC = int(os.environ.get("POLL_MEASURING_SEC", "10"))   # 10–15s recommended
POLL_IDLE_SEC      = int(os.environ.get("POLL_IDLE_SEC", "20"))
POLL_ERROR_SEC     = int(os.environ.get("POLL_ERROR_SEC", "30"))
MAX_BACKOFF_SEC    = int(os.environ.get("MAX_BACKOFF_SEC", "120"))

LOG_LEVEL = os.environ.get("INGEST_LOG_LEVEL", "INFO").upper()
LOG_PATH  = os.environ.get("INGEST_LOG_PATH", "")

# ------------ Logging ------------
logger = logging.getLogger("gasera.ingest")
logger.setLevel(LOG_LEVEL)
handler = logging.FileHandler(LOG_PATH) if LOG_PATH else logging.StreamHandler()
handler.setLevel(LOG_LEVEL)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(handler)

# ------------ Main ------------
class GaseraIngester:
    def __init__(self) -> None:
        create_all(engine)  # ensure tables exist
        self.ctrl = GaseraController()  # <-- use your controller
        self._stop = threading.Event()
        self._backoff = 0

    def stop(self):
        self._stop.set()

    def run(self):
        logger.info("Gasera ingester started (controller-backed)")
        while not self._stop.is_set():
            try:
                errorstatus, dev_status, phase = self._read_status()
                self._record_state(errorstatus, dev_status, phase)

                if errorstatus == 1:
                    logger.warning(f"Device reported errorstatus=1; dev_status={dev_status.name}")
                    self._sleep(POLL_ERROR_SEC)
                    continue

                if dev_status != DeviceStatus.MEASURING:
                    self._sleep(POLL_IDLE_SEC)
                    continue

                # Measuring → fetch latest ACON and store if new
                acon = self.ctrl.get_last_results()
                if not acon or acon.error or not acon.records:
                    logger.debug("ACON returned no data or error.")
                    self._sleep(POLL_MEASURING_SEC)
                    continue

                epoch = acon.timestamp  # property from your class
                if epoch is None:
                    logger.debug("ACON has no timestamp; skipping.")
                    self._sleep(POLL_MEASURING_SEC)
                    continue

                rows = []
                for rec in acon.records:
                    label = None
                    if get_cas_details:
                        try:
                            d = get_cas_details(rec.cas)
                            label = d.get("label") or d.get("name")
                        except Exception:
                            pass
                    rows.append((rec.cas, rec.ppm, label))

                # We don't have the raw line here (controller parses internally),
                # so pass None; if you want raw, return it from controller later.
                with get_session() as s:
                    _, created = insert_cycle_with_values(
                        s, device_epoch=epoch, raw_response=None, rows=rows
                    )
                    if created:
                        self._backoff = 0
                        logger.info(f"Stored cycle @ epoch={epoch} "
                                    f"({datetime.fromtimestamp(epoch, tz=timezone.utc)}) "
                                    f"with {len(rows)} values.")
                    else:
                        logger.debug(f"Duplicate cycle @ epoch={epoch}; ignored.")

                self._sleep(POLL_MEASURING_SEC)

            except Exception as ex:
                # e.g., controller/tcp exceptions
                self._backoff = min(MAX_BACKOFF_SEC, (self._backoff or 5) * 2)
                logger.warning(f"Ingest loop error: {ex!r}. Backing off {self._backoff}s.")
                self._sleep(self._backoff)

        logger.info("Gasera ingester stopped")

    # ---------- helpers ----------
    def _read_status(self) -> Tuple[int, DeviceStatus, Optional[MeasurementPhase]]:
        asts = self.ctrl.get_device_status()
        if not asts:
            # Treat as offline/unreachable → map to 'MALFUNCTION' with error
            return 1, DeviceStatus.MALFUNCTION, None

        # Map to the DB enums using the numeric codes your parser returns
        errorstatus = int(getattr(asts, "errorstatus", 0))
        dev_status_code = int(getattr(asts, "device_status", 2))  # default IDLE
        dev_status = DeviceStatus(dev_status_code)

        phase = None
        try:
            amst = self.ctrl.get_measurement_status()
            if amst and not getattr(amst, "error", False):
                phase_code = int(getattr(amst, "measurement_status", 0))
                phase = MeasurementPhase(phase_code)
        except Exception:
            pass

        return errorstatus, dev_status, phase

    def _record_state(self, errorstatus: int, dev_status: DeviceStatus, phase: Optional[MeasurementPhase]):
        try:
            with get_session() as s:
                s.add(DeviceStateLog(
                    errorstatus=errorstatus,
                    device_status=dev_status,
                    measurement_status=phase,
                ))
                s.commit()
        except Exception as ex:
            logger.debug(f"Failed to write DeviceStateLog: {ex!r}")

    def _sleep(self, seconds: int):
        end = time.time() + seconds
        while time.time() < end and not self._stop.is_set():
            time.sleep(0.2)

def main():
    ing = GaseraIngester()
    def _sigterm(_sig, _frm): ing.stop()
    signal.signal(signal.SIGINT, _sigterm)
    signal.signal(signal.SIGTERM, _sigterm)
    ing.run()

if __name__ == "__main__":
    main()
