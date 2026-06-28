"""Gate G1 end-to-end + reproducibility, proven on the synthetic backfill.

These tests drive the *real* validation → quarantine → interpolation transforms with the
deterministic synthetic generator, so the data-quality guarantees are exercised by the same
code that runs in production — not a mock.
"""

from app.constants import MAX_INTERPOLATION_GAP_HOURS
from app.ingestion.interpolation import interpolate_series
from app.ingestion.validation import _detect_gaps, validate_batch
from app.modeling import synthetic


def _small() -> synthetic.SyntheticData:
    """A small slice (3 stations, 15 days): fast, but still triggers every injected
    corruption (3 bad rows, short + long gaps)."""
    return synthetic.generate(days=15, profiles=synthetic.STATION_PROFILES[:3])


def test_generator_is_deterministic() -> None:
    a = _small()
    b = _small()
    assert len(a.measurements) == len(b.measurements)
    assert [(m.station_id, m.pollutant, m.ts, m.value) for m in a.measurements] == [
        (m.station_id, m.pollutant, m.ts, m.value) for m in b.measurements
    ]


def test_g1_quarantine_catches_injected_bad_batch() -> None:
    data = _small()
    assert data.injected_bad >= 1

    report = validate_batch(data.measurements)
    # Every injected out-of-range value is quarantined, never silently dropped.
    assert report.quarantined_count == data.injected_bad
    assert all(q.reason in {"below_min", "above_max", "non_finite_value"} for q in report.quarantined)
    # Accepted values are all within plausible physical bounds.
    assert all(m.value >= 0 for m in report.accepted)


def test_g1_interpolation_flags_survive_and_long_gaps_stay_gaps() -> None:
    data = _small()
    report = validate_batch(data.measurements)
    filled = interpolate_series(report.accepted)

    interpolated = [m for m in filled if m.interpolated]
    # Short gaps (and the 1h holes left by quarantining bad rows) were filled and flagged (HL3).
    assert len(interpolated) >= data.dropped_short_gap_hours >= 1
    # Real (measured) points are never marked interpolated.
    measured = [m for m in filled if not m.interpolated]
    assert len(measured) == len(report.accepted)

    # The 6h gap (> MAX_INTERPOLATION_GAP_HOURS) is left as a gap, never invented: a gap longer
    # than the fill limit still exists in the filled series.
    assert MAX_INTERPOLATION_GAP_HOURS < 6
    remaining_long_gaps = [g for g in _detect_gaps(filled) if g.hours > MAX_INTERPOLATION_GAP_HOURS]
    assert remaining_long_gaps, "the long gap must survive interpolation as a real gap"
