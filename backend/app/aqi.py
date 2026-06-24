"""US EPA Air Quality Index helpers.

Reusable by both the seed provider (Phase 0) and the real pipeline (Phase 1+).
PM2.5 uses the official piecewise-linear breakpoints; O3/NO2 use a documented linear
proxy adequate for category/coloring (refined against official tables in Phase 1).
"""

from app.schemas import AQICategory, Pollutant

# (conc_low, conc_high, aqi_low, aqi_high) — EPA PM2.5 (24-hr, µg/m³).
_PM25_BREAKPOINTS: list[tuple[float, float, int, int]] = [
    (0.0, 12.0, 0, 50),
    (12.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 150.4, 151, 200),
    (150.5, 250.4, 201, 300),
    (250.5, 500.4, 301, 500),
]

# Linear proxy scales (ppb) keyed to the same AQI bands for O3 (8-hr) and NO2 (1-hr).
_O3_BREAKPOINTS: list[tuple[float, float, int, int]] = [
    (0, 54, 0, 50),
    (55, 70, 51, 100),
    (71, 85, 101, 150),
    (86, 105, 151, 200),
    (106, 200, 201, 300),
    (201, 400, 301, 500),
]
_NO2_BREAKPOINTS: list[tuple[float, float, int, int]] = [
    (0, 53, 0, 50),
    (54, 100, 51, 100),
    (101, 360, 101, 150),
    (361, 649, 151, 200),
    (650, 1249, 201, 300),
    (1250, 2049, 301, 500),
]

_BREAKPOINTS: dict[Pollutant, list[tuple[float, float, int, int]]] = {
    Pollutant.pm25: _PM25_BREAKPOINTS,
    Pollutant.o3: _O3_BREAKPOINTS,
    Pollutant.no2: _NO2_BREAKPOINTS,
}


def aqi_for(pollutant: Pollutant, concentration: float) -> int:
    """Convert a concentration to an AQI index via piecewise-linear interpolation."""
    bands = _BREAKPOINTS[pollutant]
    value = max(concentration, 0.0)
    for c_lo, c_hi, i_lo, i_hi in bands:
        if value <= c_hi:
            clamped = max(value, c_lo)
            return round((i_hi - i_lo) / (c_hi - c_lo) * (clamped - c_lo) + i_lo)
    return bands[-1][3]  # above the top band -> cap at max AQI


def category_from_aqi(aqi: int) -> AQICategory:
    if aqi <= 50:
        return AQICategory.good
    if aqi <= 100:
        return AQICategory.moderate
    if aqi <= 150:
        return AQICategory.unhealthy_sensitive
    if aqi <= 200:
        return AQICategory.unhealthy
    if aqi <= 300:
        return AQICategory.very_unhealthy
    return AQICategory.hazardous
