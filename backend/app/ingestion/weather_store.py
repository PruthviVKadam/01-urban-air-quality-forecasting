"""Weather observation store — DuckDB/Parquet persistence for exogenous features.

Same idempotent-upsert pattern as ProcessedStore: keyed by (station_id, ts), so
re-running ingestion for a time window produces the same result (determinism mandate).
Used by Phase 2 feature engineering for temperature, humidity, wind, and pressure.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from app.ingestion.providers.base import WeatherObservation

_WEATHER_DDL = """
CREATE TABLE w (
    station_id VARCHAR, ts TIMESTAMP,
    temperature_c DOUBLE, humidity_pct DOUBLE,
    wind_speed_ms DOUBLE, pressure_hpa DOUBLE
)
"""


def _naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC)
    return dt.replace(tzinfo=None)


def _as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC)


class WeatherStore:
    """Idempotent, columnar store of weather observations (single Parquet file)."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute(_WEATHER_DDL)
        if self._path.exists():
            con.execute(f"INSERT INTO w SELECT * FROM read_parquet('{self._path.as_posix()}')")

    def upsert(self, observations: list[WeatherObservation]) -> int:
        """Insert-or-replace weather observations. Returns final row count."""
        if not observations:
            return self.count()
        con = duckdb.connect()
        try:
            self._load(con)
            keys = sorted({(o.station_id, _naive_utc(o.ts)) for o in observations})
            con.executemany("DELETE FROM w WHERE station_id = ? AND ts = ?", keys)
            con.executemany(
                "INSERT INTO w VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        o.station_id,
                        _naive_utc(o.ts),
                        o.temperature_c,
                        o.humidity_pct,
                        o.wind_speed_ms,
                        o.pressure_hpa,
                    )
                    for o in observations
                ],
            )
            con.execute(f"COPY w TO '{self._path.as_posix()}' (FORMAT PARQUET)")
            return int(con.execute("SELECT count(*) FROM w").fetchone()[0])  # type: ignore[index]
        finally:
            con.close()

    def read(
        self,
        station_id: str | None = None,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[WeatherObservation]:
        if not self._path.exists():
            return []
        con = duckdb.connect()
        try:
            query = (
                "SELECT station_id, ts, temperature_c, humidity_pct, "
                f"wind_speed_ms, pressure_hpa FROM read_parquet('{self._path.as_posix()}')"
            )
            clauses: list[str] = []
            params: list[Any] = []
            if station_id is not None:
                clauses.append("station_id = ?")
                params.append(station_id)
            if since is not None:
                clauses.append("ts >= ?")
                params.append(_naive_utc(since))
            if until is not None:
                clauses.append("ts <= ?")
                params.append(_naive_utc(until))
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            query += " ORDER BY station_id, ts"
            rows = con.execute(query, params).fetchall()
        finally:
            con.close()
        return [
            WeatherObservation(
                station_id=r[0],
                ts=_as_utc(r[1]),
                temperature_c=r[2],
                humidity_pct=r[3],
                wind_speed_ms=r[4],
                pressure_hpa=r[5],
            )
            for r in rows
        ]

    def count(self) -> int:
        if not self._path.exists():
            return 0
        con = duckdb.connect()
        try:
            return int(
                con.execute(
                    f"SELECT count(*) FROM read_parquet('{self._path.as_posix()}')"
                ).fetchone()[0]  # type: ignore[index]
            )
        finally:
            con.close()
