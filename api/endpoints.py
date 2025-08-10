from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Optional, Tuple
import csv, io

from flask import request, jsonify, Response

from . import api
from storage.db import get_session
from storage.models import (
    Gas, MeasurementCycle, MeasurementValue, DeviceStateLog,
    DeviceStatus, MeasurementPhase
)
from sqlalchemy import select, and_, func, desc, asc

DEVICE_STATUS_MAP = {
    DeviceStatus.INITIALIZING: "Initializing",
    DeviceStatus.INIT_ERROR:   "Initialization error",
    DeviceStatus.IDLE:         "Idle",
    DeviceStatus.SELF_TEST:    "Self-test",
    DeviceStatus.MALFUNCTION:  "Malfunction",
    DeviceStatus.MEASURING:    "Measuring",
    DeviceStatus.CALIBRATING:  "Calibration",
    DeviceStatus.CANCELLING:   "Cancelling",
    DeviceStatus.LASER_SCAN:   "Laser scan",
}

PHASE_MAP = {
    MeasurementPhase.NONE:         "None/Idle",
    MeasurementPhase.GAS_EXCHANGE: "Gas exchange",
    MeasurementPhase.INTEGRATION:  "Integration",
    MeasurementPhase.ANALYSIS:     "Analysis",
    MeasurementPhase.LASER_TUNING: "Laser tuning",
}

def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s: return None
    try:
        if s.isdigit():
            return datetime.fromtimestamp(int(s), tz=timezone.utc)
        # ISO-like; assume UTC if no tz
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None

def _resolve_gases(session, gases_param: Optional[str]) -> List[int]:
    """
    Accepts comma-separated CAS or names; returns gas.id list.
    """
    if not gases_param:
        ids = session.execute(select(Gas.id)).scalars().all()
        return list(ids)
    tokens = [t.strip() for t in gases_param.split(",") if t.strip()]
    if not tokens:
        return []
    rows = session.execute(
        select(Gas.id, Gas.cas, Gas.name)
        .where(func.lower(Gas.cas).in_([t.lower() for t in tokens]) |
               func.lower(Gas.name).in_([t.lower() for t in tokens]))
    ).all()
    return [r[0] for r in rows]

@api.get("/status")
def get_status():
    with get_session() as s:
        st = s.execute(
            select(DeviceStateLog).order_by(desc(DeviceStateLog.ts)).limit(1)
        ).scalar_one_or_none()
        last_cycle = s.execute(
            select(MeasurementCycle).order_by(desc(MeasurementCycle.device_ts)).limit(1)
        ).scalar_one_or_none()

        now = datetime.now(tz=timezone.utc)
        payload = {
            "device": {
                "observed_at": st.ts.isoformat() if st else None,
                "errorstatus": st.errorstatus if st else None,
                "device_status": int(st.device_status) if st else None,
                "device_status_label": DEVICE_STATUS_MAP.get(st.device_status) if st else None,
                "phase": int(st.measurement_status) if (st and st.measurement_status is not None) else None,
                "phase_label": PHASE_MAP.get(st.measurement_status) if st and st.measurement_status is not None else None,
            },
            "last_cycle": {
                "device_ts": last_cycle.device_ts.isoformat() if last_cycle else None,
                "device_epoch": last_cycle.device_epoch if last_cycle else None,
                "ingested_ts": last_cycle.ingested_ts.isoformat() if last_cycle else None,
                "age_seconds": int((now - last_cycle.ingested_ts).total_seconds()) if last_cycle else None,
            }
        }
        return jsonify(payload)

@api.get("/gases")
def list_gases():
    with get_session() as s:
        rows = s.execute(select(Gas.id, Gas.cas, Gas.name, Gas.unit).order_by(func.lower(Gas.name.nullslast()))).all()
        return jsonify([
            {"id": r[0], "cas": r[1], "name": r[2], "unit": r[3]}
        for r in rows])

@api.get("/measurements")
def get_measurements():
    """
    Query params:
      start, end: ISO or epoch seconds (UTC assumed)
      gases: comma-separated CAS or names (default: all)
      order: asc|desc (by device_ts, default asc)
      mode: cycle|flat  (default: cycle)
      limit, offset: pagination for flat mode
    """
    start = _parse_dt(request.args.get("start"))
    end   = _parse_dt(request.args.get("end"))
    order = (request.args.get("order") or "asc").lower()
    mode  = (request.args.get("mode") or "cycle").lower()
    limit = int(request.args.get("limit") or 0)
    offset= int(request.args.get("offset") or 0)
    gases_param = request.args.get("gases")

    with get_session() as s:
        gas_ids = _resolve_gases(s, gases_param)

        # base time filter
        conds = []
        if start: conds.append(MeasurementCycle.device_ts >= start)
        if end:   conds.append(MeasurementCycle.device_ts <= end)

        order_by = asc(MeasurementCycle.device_ts) if order == "asc" else desc(MeasurementCycle.device_ts)

        if mode == "flat":
            q = (
                select(
                    MeasurementCycle.device_ts,
                    MeasurementCycle.device_epoch,
                    Gas.cas, Gas.name, MeasurementValue.ppm
                )
                .join(MeasurementValue, MeasurementValue.cycle_id == MeasurementCycle.id)
                .join(Gas, Gas.id == MeasurementValue.gas_id)
                .where(and_(*(conds or [True]), MeasurementValue.gas_id.in_(gas_ids)))
                .order_by(order_by, Gas.cas)
            )
            if limit: q = q.limit(limit)
            if offset: q = q.offset(offset)

            rows = s.execute(q).all()
            out = [{
                "ts": r[0].isoformat(), "epoch": r[1],
                "cas": r[2], "name": r[3], "ppm": r[4],
            } for r in rows]
            return jsonify(out)

        # mode == "cycle" → nest values by cycle
        q = (
            select(
                MeasurementCycle.id,
                MeasurementCycle.device_ts,
                MeasurementCycle.device_epoch,
                MeasurementCycle.ingested_ts,
            )
            .where(and_(*(conds or [True])))
            .order_by(order_by)
        )
        cycles = s.execute(q).all()
        if not cycles:
            return jsonify([])

        # Fetch values for these cycles & selected gases
        cycle_ids = [c[0] for c in cycles]
        vq = (
            select(
                MeasurementValue.cycle_id, Gas.cas, Gas.name, MeasurementValue.ppm
            )
            .join(Gas, Gas.id == MeasurementValue.gas_id)
            .where(MeasurementValue.cycle_id.in_(cycle_ids) &
                   MeasurementValue.gas_id.in_(gas_ids))
        )
        vals = s.execute(vq).all()
        # group in memory
        by_cycle = {}
        for cid, cas, name, ppm in vals:
            by_cycle.setdefault(cid, []).append((cas, name, ppm))

        out = []
        for cid, ts, epoch, ing_ts in cycles:
            values = by_cycle.get(cid, [])
            out.append({
                "ts": ts.isoformat(), "epoch": epoch, "ingested_ts": ing_ts.isoformat(),
                "values": [{"cas": cas, "name": name, "ppm": ppm} for cas, name, ppm in values]
            })
        return jsonify(out)

@api.get("/measurements/export.csv")
def export_csv():
    start = _parse_dt(request.args.get("start"))
    end   = _parse_dt(request.args.get("end"))
    gases_param = request.args.get("gases")

    def generate():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ts_iso", "epoch", "cas", "name", "ppm"])
        yield output.getvalue(); output.seek(0); output.truncate(0)

        with get_session() as s:
            gas_ids = _resolve_gases(s, gases_param)
            conds = []
            if start: conds.append(MeasurementCycle.device_ts >= start)
            if end:   conds.append(MeasurementCycle.device_ts <= end)
            q = (
                select(
                    MeasurementCycle.device_ts,
                    MeasurementCycle.device_epoch,
                    Gas.cas, Gas.name, MeasurementValue.ppm
                )
                .join(MeasurementValue, MeasurementValue.cycle_id == MeasurementCycle.id)
                .join(Gas, Gas.id == MeasurementValue.gas_id)
                .where(and_(*(conds or [True]), MeasurementValue.gas_id.in_(gas_ids)))
                .order_by(asc(MeasurementCycle.device_ts), Gas.cas)
            )
            for ts, epoch, cas, name, ppm in s.execute(q):
                writer.writerow([ts.isoformat(), epoch, cas, name, ppm])
                yield output.getvalue(); output.seek(0); output.truncate(0)

    return Response(generate(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=gasera_export.csv"})
