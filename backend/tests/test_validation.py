from datetime import UTC, datetime, timedelta

from app.ingestion.interpolation import interpolate_series
from app.ingestion.models import Measurement
from app.ingestion.validation import validate_batch
from app.schemas import Pollutant

BASE = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)


def m(hour: int, value: float, *, pollutant: Pollutant = Pollutant.pm25) -> Measurement:
    return Measurement("s1", pollutant, BASE + timedelta(hours=hour), value, "µg/m³", "openaq")


def test_quarantines_out_of_range_never_drops() -> None:
    records = [m(0, 10.0), m(1, -5.0), m(2, 99999.0)]
    report = validate_batch(records)
    assert report.accepted_count == 1
    assert report.quarantined_count == 2
    reasons = {q.reason for q in report.quarantined}
    assert reasons == {"below_min", "above_max"}
    # quarantined rows retain their data for audit
    assert all(q.value is not None for q in report.quarantined)


def test_collapses_duplicate_timestamps() -> None:
    records = [m(0, 10.0), m(0, 12.0), m(1, 11.0)]
    report = validate_batch(records)
    assert report.duplicates_collapsed == 1
    assert report.accepted_count == 2
    # last write wins
    assert next(x for x in report.accepted if x.ts == BASE).value == 12.0


def test_detects_gaps() -> None:
    records = [m(0, 10.0), m(3, 16.0)]  # hours 1 and 2 missing
    report = validate_batch(records)
    assert len(report.gaps) == 1
    assert report.gaps[0].hours == 2


def test_interpolates_short_gap_with_flags() -> None:
    filled = interpolate_series([m(0, 10.0), m(3, 16.0)], max_gap_hours=3)
    interpolated = [x for x in filled if x.interpolated]
    assert len(interpolated) == 2  # hours 1 and 2
    assert [x.value for x in interpolated] == [12.0, 14.0]  # linear
    assert all(x.interpolated for x in interpolated)


def test_leaves_long_gap_unfilled() -> None:
    filled = interpolate_series([m(0, 10.0), m(6, 22.0)], max_gap_hours=3)  # 5-hour gap
    assert not any(x.interpolated for x in filled)
    assert len(filled) == 2
