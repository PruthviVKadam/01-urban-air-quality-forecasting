"""Gap interpolation with honest flags (HL3).

Internal gaps up to ``max_gap_hours`` are linearly interpolated and every synthesized
point is flagged ``interpolated=True`` — a flag that survives to the API and UI. Gaps
longer than the limit are left as gaps (shown as gaps, never invented).
"""

from datetime import timedelta

from app.constants import EXPECTED_FREQ_HOURS, MAX_INTERPOLATION_GAP_HOURS
from app.ingestion.models import Measurement
from app.schemas import Pollutant


def interpolate_series(
    measurements: list[Measurement],
    *,
    max_gap_hours: int = MAX_INTERPOLATION_GAP_HOURS,
) -> list[Measurement]:
    series: dict[tuple[str, Pollutant], list[Measurement]] = {}
    for m in measurements:
        series.setdefault((m.station_id, m.pollutant), []).append(m)

    step = timedelta(hours=EXPECTED_FREQ_HOURS)
    out: list[Measurement] = []
    for points in series.values():
        points.sort(key=lambda m: m.ts)
        out.extend(points)
        for prev, curr in zip(points, points[1:], strict=False):
            missing = int((curr.ts - prev.ts) / step) - 1
            if missing < 1 or missing > max_gap_hours:
                continue  # contiguous, or too long to fill — leave the gap
            for k in range(1, missing + 1):
                fraction = k / (missing + 1)
                value = prev.value + (curr.value - prev.value) * fraction
                out.append(
                    Measurement(
                        station_id=prev.station_id,
                        pollutant=prev.pollutant,
                        ts=prev.ts + step * k,
                        value=round(value, 3),
                        unit=prev.unit,
                        source=prev.source,
                        interpolated=True,
                    )
                )

    out.sort(key=lambda m: (m.station_id, str(m.pollutant), m.ts))
    return out
