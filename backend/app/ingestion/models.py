"""Core ingestion record types."""

from dataclasses import dataclass
from datetime import datetime

from app.schemas import Pollutant


@dataclass(frozen=True, slots=True)
class Measurement:
    """One cleaned, hour-aligned pollutant reading (UTC)."""

    station_id: str
    pollutant: Pollutant
    ts: datetime
    value: float
    unit: str
    source: str
    interpolated: bool = False


@dataclass(frozen=True, slots=True)
class QuarantinedRow:
    """A rejected reading kept for audit — never silently dropped (HL3 / G1)."""

    station_id: str
    pollutant: str
    ts: datetime | None
    value: float | None
    source: str
    reason: str
