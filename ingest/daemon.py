# ingest/daemon.py
from __future__ import annotations
import os, time, signal, logging, threading
from datetime import datetime, timezone
from typing import Optional, Tuple

# Reuse your protocol + TCP stack
from gasera.protocol import GaseraProtocol
try:
    # if your repo exposes a simple function as earlier examples
    from gasera import tcp_client
    send_cmd = tcp_client.send_command
except Exception:
    # fallback path if wrapped differently
    from gasera.tcp_client import send_command as send_cmd  # type: ignore

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
GASERA_HOST = os.environ.get("GASERA_HOST", "192.168.100.2")
GASERA_PORT = int(os.environ.get("GASERA_PORT", "10000"))

POLL_MEASURING_SEC = int(os.environ.get("POLL_MEASURING_SEC", "10"))   # 10–15s recommended
POLL_IDLE_SEC      = int(os.environ.get("POLL_IDLE_SEC", "20"))
POLL_ERROR_SEC     = int(os.environ.get("POLL_ERROR_SEC", "30"))
MAX_BACKOFF_SEC    = int(os.environ.get("MAX_BACKOFF_SEC", "120"))

LOG_LEVEL = os.environ.get("INGEST_LOG_LEVEL", "INFO").upper()
LOG_PATH  = os.environ.get("INGEST_LOG_PATH", "")  # empty → stdout

# ------------ Logging ------------
logger = logging.getLogger("gasera.ingest")
logger.setLevel(LOG_LEVEL)
if LOG_PATH:
    fh = logging.FileHandler(LOG_PATH)
    fh.setLevel(LOG_LEVEL)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)
else:
    ch = logging.StreamHandler()
    ch.setLevel(LOG_LEVEL)
    ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(ch)

# ------------ Main ------------
# INGEST_LOG_LEVEL=DEBUG GASERA_HOST=192.168.100.10 GASERA_PORT=8888 python3 -m ingest.daemon

class GaseraIngester:
    def __init__(self) -> None:
        create_all(engine)  # ensure tables exist
        self.proto = GaseraProtocol()
        self._stop = threading.Event()
        self._backoff = 0

    def stop(self):  # for graceful shutdown
        self._stop.set()

    def run(self):
        logger.info("Gasera ingester started")
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
                acon_resp = send_cmd(self.proto.get_last_measurement_results())
                acon = self.proto.parse_acon(acon_resp)
                if acon.error or not acon.records:
                    logger.debug("ACON returned no data or error.")
                    self._sleep(POLL_MEASURING_SEC)
                    continue

                epoch = acon.timestamp  # uses your property (records[0].timestamp)
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
                            # your config typically returns dict; prefer label/name if present
                            label = d.get("label") or d.get("name")
                        except Exception:
                            pass
                    rows.append((rec.cas, rec.ppm, label))

                with get_session() as s:
                    _, created = insert_cycle_with_values(
                        s, device_epoch=epoch, raw_response=acon_resp, rows=rows
                    )
                    if created:
                        self._backoff = 0  # reset connection backoff on success
                        logger.info(f"Stored cycle @ epoch={epoch} ({datetime.fromtimestamp(epoch, tz=timezone.utc)}) "
                                    f"with {len(rows)} values.")
                    else:
                        logger.debug(f"Duplicate cycle @ epoch={epoch}; ignored.")

                self._sleep(POLL_MEASURING_SEC)
            except Exception as ex:
                # network/device issues etc.
                self._backoff = min(MAX_BACKOFF_SEC, (self._backoff or 5) * 2)
                logger.warning(f"Ingest loop error: {ex!r}. Backing off {self._backoff}s.")
                self._sleep(self._backoff)

        logger.info("Gasera ingester stopped")

    # ---------- helpers ----------
    def _read_status(self) -> Tuple[int, DeviceStatus, Optional[MeasurementPhase]]:
        # ASTS
        asts_resp = send_cmd(self.proto.ask_current_status())
        asts = self.proto.parse_asts(asts_resp)
        errorstatus = asts.errorstatus
        dev_status = DeviceStatus(asts.device_status)  # map exact integer values

        # AMST (phase) may error when idle → ignore safely
        phase = None
        try:
            amst_resp = send_cmd(self.proto.get_measurement_status())
            amst = self.proto.parse_amst(amst_resp)
            if not amst.error:
                phase = MeasurementPhase(amst.measurement_status)
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
        # allow graceful shutdown
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
