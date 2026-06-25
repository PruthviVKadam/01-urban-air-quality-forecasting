"""Batch data-quality validation (gate G1).

Runs schema, range, duplicate, and gap checks. Bad rows are *quarantined with a reason*,
never silently dropped. Duplicate timestamps are collapsed (last wins). Gaps are detected
and reported so interpolation can decide what is fillable.
"""

import itertools
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.constants import EXPECTED_FREQ_HOURS, PLAUSIBLE_BOUNDS
from app.ingestion.models import Measurement, QuarantinedRow
from app.schemas import Pollutant


@dataclass(frozen=True)
class Gap:
    station_id: str
    pollutant: Pollutant
    start: datetime  # first missing hour
    end: datetime  # last missing hour
    hours: int


@dataclass
class ValidationReport:
    accepted: list[Measurement] = field(default_factory=list)
    quarantined: list[QuarantinedRow] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)
    duplicates_collapsed: int = 0

    @property
    def accepted_count(self) -> int:
        return len(self.accepted)

    @property
    def quarantined_count(self) -> int:
        return len(self.quarantined)


def _series_key(m: Measurement) -> tuple[str, Pollutant]:
    return (m.station_id, m.pollutant)


def _range_reason(m: Measurement, bounds: dict[Pollutant, tuple[float, float]]) -> str | None:
    if m.value is None or not math.isfinite(m.value):
        return "non_finite_value"
    low, high = bounds.get(m.pollutant, (0.0, math.inf))
    if m.value < low:
        return "below_min"
    if m.value > high:
        return "above_max"
    return None


def _collapse_duplicates(records: list[Measurement]) -> tuple[list[Measurement], int]:
    """Keep the last reading per (station, pollutant, ts); count the collapses."""
    by_key: dict[tuple[str, Pollutant, datetime], Measurement] = {}
    collapsed = 0
    for m in records:
        key = (m.station_id, m.pollutant, m.ts)
        if key in by_key:
            collapsed += 1
        by_key[key] = m
    return list(by_key.values()), collapsed


def _detect_gaps(records: list[Measurement]) -> list[Gap]:
    series: dict[tuple[str, Pollutant], list[Measurement]] = {}
    for m in records:
        series.setdefault(_series_key(m), []).append(m)

    step = timedelta(hours=EXPECTED_FREQ_HOURS)
    gaps: list[Gap] = []
    for (station_id, pollutant), points in series.items():
        points.sort(key=lambda m: m.ts)
        for prev, curr in itertools.pairwise(points):
            missing = int((curr.ts - prev.ts) / step) - 1
            if missing >= 1:
                gaps.append(
                    Gap(
                        station_id=station_id,
                        pollutant=pollutant,
                        start=prev.ts + step,
                        end=curr.ts - step,
                        hours=missing,
                    )
                )
    return gaps


def validate_batch(
    records: list[Measurement],
    *,
    bounds: dict[Pollutant, tuple[float, float]] = PLAUSIBLE_BOUNDS,
) -> ValidationReport:
    report = ValidationReport()

    survivors: list[Measurement] = []
    for m in records:
        reason = _range_reason(m, bounds)
        if reason is not None:
            report.quarantined.append(
                QuarantinedRow(
                    station_id=m.station_id,
                    pollutant=str(m.pollutant),
                    ts=m.ts,
                    value=m.value,
                    source=m.source,
                    reason=reason,
                )
            )
        else:
            survivors.append(m)

    deduped, collapsed = _collapse_duplicates(survivors)
    report.duplicates_collapsed = collapsed
    report.gaps = _detect_gaps(deduped)
    report.accepted = sorted(deduped, key=lambda m: (m.station_id, str(m.pollutant), m.ts))
    return report
