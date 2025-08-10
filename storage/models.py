# storage/models.py
from __future__ import annotations
from datetime import datetime, timezone
from enum import IntEnum
from typing import Optional
from sqlalchemy import (
    DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

# Mirrors ASTS/AMST maps in protocol.py
class DeviceStatus(IntEnum):
    INITIALIZING = 0
    INIT_ERROR   = 1
    IDLE         = 2
    SELF_TEST    = 3
    MALFUNCTION  = 4
    MEASURING    = 5
    CALIBRATING  = 6
    CANCELLING   = 7
    LASER_SCAN   = 8

class MeasurementPhase(IntEnum):
    NONE         = 0
    GAS_EXCHANGE = 1
    INTEGRATION  = 2
    ANALYSIS     = 3
    LASER_TUNING = 4

class Gas(Base):
    __tablename__ = "gas"
    id:   Mapped[int]  = mapped_column(Integer, primary_key=True)
    cas:  Mapped[str]  = mapped_column(String(32), unique=True, index=True)  # e.g. "74-82-8"
    name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    unit: Mapped[str]  = mapped_column(String(16), default="ppm")

    values: Mapped[list["MeasurementValue"]] = relationship(back_populates="gas", cascade="all, delete-orphan")

class MeasurementCycle(Base):
    __tablename__ = "measurement_cycle"
    id:           Mapped[int]       = mapped_column(Integer, primary_key=True)
    device_ts:    Mapped[datetime]  = mapped_column(DateTime(timezone=True), index=True)  # UTC
    device_epoch: Mapped[int]       = mapped_column(Integer, index=True)                  # from ACON
    ingested_ts:  Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    source:       Mapped[str]       = mapped_column(String(16), default="ACON")
    raw_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    values: Mapped[list["MeasurementValue"]] = relationship(back_populates="cycle", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("device_epoch", name="uq_cycle_device_epoch"),
        Index("ix_cycle_ingested_ts", "ingested_ts"),
    )

class MeasurementValue(Base):
    __tablename__ = "measurement_value"
    id:       Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("measurement_cycle.id", ondelete="CASCADE"), index=True)
    gas_id:   Mapped[int] = mapped_column(ForeignKey("gas.id", ondelete="CASCADE"), index=True)
    ppm:      Mapped[float] = mapped_column(Float)

    cycle: Mapped["MeasurementCycle"] = relationship(back_populates="values")
    gas:   Mapped["Gas"]              = relationship(back_populates="values")

    __table_args__ = (
        UniqueConstraint("cycle_id", "gas_id", name="uq_value_cycle_gas"),
        Index("ix_value_gas_cycle", "gas_id", "cycle_id"),
    )

class DeviceStateLog(Base):
    __tablename__ = "device_state_log"
    id:   Mapped[int]      = mapped_column(Integer, primary_key=True)
    ts:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    errorstatus:        Mapped[int]                  = mapped_column(Integer, default=0)
    device_status:      Mapped[DeviceStatus]         = mapped_column(Enum(DeviceStatus), index=True)
    measurement_status: Mapped[Optional[MeasurementPhase]] = mapped_column(Enum(MeasurementPhase), nullable=True, index=True)

def epoch_to_utc(epoch: int) -> datetime:
    return datetime.fromtimestamp(epoch, tz=timezone.utc)

def create_all(engine) -> None:
    Base.metadata.create_all(bind=engine)
