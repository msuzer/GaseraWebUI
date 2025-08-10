# storage/ops.py
from __future__ import annotations
from typing import Iterable, Optional, Tuple
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from .models import Gas, MeasurementCycle, MeasurementValue, epoch_to_utc

def get_or_create_gas(session, cas: str, name: Optional[str] = None, unit: str = "ppm") -> Gas:
    gas = session.execute(select(Gas).where(Gas.cas == cas)).scalar_one_or_none()
    if gas:
        if name and not gas.name:
            gas.name = name
            session.flush()
        return gas
    gas = Gas(cas=cas, name=name, unit=unit)
    session.add(gas)
    session.flush()
    return gas

def insert_cycle_with_values(session, device_epoch: int, raw_response: Optional[str],
                             rows: Iterable[Tuple[str, float, Optional[str]]]):
    """
    Insert a cycle and its values.
    rows: iterable of tuples (cas, ppm, name)
    Returns (cycle, created: bool)
    """
    existing = session.execute(
        select(MeasurementCycle).where(MeasurementCycle.device_epoch == device_epoch)
    ).scalar_one_or_none()
    if existing:
        return existing, False

    cycle = MeasurementCycle(
        device_epoch=device_epoch,
        device_ts=epoch_to_utc(device_epoch),
        raw_response=raw_response,
    )
    session.add(cycle)
    session.flush()  # get cycle.id

    for cas, ppm, name in rows:
        gas = get_or_create_gas(session, cas=cas, name=name, unit="ppm")
        session.add(MeasurementValue(cycle_id=cycle.id, gas_id=gas.id, ppm=ppm))

    try:
        session.commit()
        return cycle, True
    except IntegrityError:
        session.rollback()
        # race-safe: someone else inserted same epoch
        existing = session.execute(
            select(MeasurementCycle).where(MeasurementCycle.device_epoch == device_epoch)
        ).scalar_one()
        return existing, False
