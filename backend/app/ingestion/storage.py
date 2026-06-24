"""Persistence: immutable raw snapshots + a columnar processed store (Parquet via DuckDB).

* Raw pulls are written once and never overwritten (immutable, replayable).
* The processed store is an idempotent upsert keyed by (station_id, pollutant, ts), so
  re-running ingestion for a window produces the same output (determinism mandate).
* Quarantined rows are appended to their own store for audit (never dropped).
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from app.ingestion.models import Measurement, QuarantinedRow
from app.schemas import Pollutant

_MEASUREMENT_DDL = """
CREATE TABLE m (
    station_id VARCHAR, pollutant VARCHAR, ts TIMESTAMP,
    value DOUBLE, unit VARCHAR, source VARCHAR, interpolated BOOLEAN
)
"""

_QUARANTINE_DDL = """
CREATE TABLE q (
    station_id VARCHAR, pollutant VARCHAR, ts TIMESTAMP,
    value DOUBLE, source VARCHAR, reason VARCHAR, quarantined_at TIMESTAMP
)
"""


def default_data_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data"


def _naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC)
    return dt.replace(tzinfo=None)


def _as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC)


class RawStore:
    """Immutable raw response snapshots under data/raw/{provider}/{station}/."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def write_raw(
        self,
        provider: str,
        station_id: str,
        label: str,
        payload: Any,
        fetched_at: datetime | None = None,
    ) -> Path:
        fetched_at = fetched_at or datetime.now(UTC)
        directory = self._root / provider / station_id
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{label}__{fetched_at.strftime('%Y%m%dT%H%M%SZ')}.json"
        if path.exists():
            return path  # immutable — keep the original snapshot
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path


class ProcessedStore:
    """Idempotent, columnar store of cleaned measurements (single Parquet file)."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute(_MEASUREMENT_DDL)
        if self._path.exists():
            con.execute(f"INSERT INTO m SELECT * FROM read_parquet('{self._path.as_posix()}')")

    def upsert(self, measurements: list[Measurement]) -> int:
        if not measurements:
            return self.count()
        con = duckdb.connect()
        try:
            self._load(con)
            keys = sorted(
                {(m.station_id, str(m.pollutant), _naive_utc(m.ts)) for m in measurements}
            )
            con.executemany(
                "DELETE FROM m WHERE station_id = ? AND pollutant = ? AND ts = ?", keys
            )
            con.executemany(
                "INSERT INTO m VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        m.station_id,
                        str(m.pollutant),
                        _naive_utc(m.ts),
                        m.value,
                        m.unit,
                        m.source,
                        m.interpolated,
                    )
                    for m in measurements
                ],
            )
            con.execute(f"COPY m TO '{self._path.as_posix()}' (FORMAT PARQUET)")
            return int(con.execute("SELECT count(*) FROM m").fetchone()[0])
        finally:
            con.close()

    def read(
        self, station_id: str | None = None, pollutant: Pollutant | None = None
    ) -> list[Measurement]:
        if not self._path.exists():
            return []
        con = duckdb.connect()
        try:
            query = (
                "SELECT station_id, pollutant, ts, value, unit, source, interpolated "
                f"FROM read_parquet('{self._path.as_posix()}')"
            )
            clauses: list[str] = []
            params: list[Any] = []
            if station_id is not None:
                clauses.append("station_id = ?")
                params.append(station_id)
            if pollutant is not None:
                clauses.append("pollutant = ?")
                params.append(str(pollutant))
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            query += " ORDER BY station_id, pollutant, ts"
            rows = con.execute(query, params).fetchall()
        finally:
            con.close()
        return [
            Measurement(
                station_id=r[0],
                pollutant=Pollutant(r[1]),
                ts=_as_utc(r[2]),
                value=r[3],
                unit=r[4],
                source=r[5],
                interpolated=bool(r[6]),
            )
            for r in rows
        ]

    def get_latest_ts(self, station_id: str | None = None) -> datetime | None:
        if not self._path.exists():
            return None
        con = duckdb.connect()
        try:
            query = f"SELECT max(ts) FROM read_parquet('{self._path.as_posix()}')"
            params: list[Any] = []
            if station_id is not None:
                query += " WHERE station_id = ?"
                params.append(station_id)
            res = con.execute(query, params).fetchone()
            if res and res[0]:
                return _as_utc(res[0])
            return None
        finally:
            con.close()

    def count(self) -> int:
        if not self._path.exists():
            return 0
        con = duckdb.connect()
        try:
            return int(
                con.execute(
                    f"SELECT count(*) FROM read_parquet('{self._path.as_posix()}')"
                ).fetchone()[0]
            )
        finally:
            con.close()


class QuarantineStore:
    """Append-only audit store for rejected rows (data/processed/quarantine.parquet)."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, rows: list[QuarantinedRow], quarantined_at: datetime | None = None) -> int:
        if not rows:
            return self.count()
        quarantined_at = _naive_utc(quarantined_at or datetime.now(UTC))
        con = duckdb.connect()
        try:
            con.execute(_QUARANTINE_DDL)
            if self._path.exists():
                con.execute(
                    f"INSERT INTO q SELECT * FROM read_parquet('{self._path.as_posix()}')"
                )
            con.executemany(
                "INSERT INTO q VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        r.station_id,
                        r.pollutant,
                        _naive_utc(r.ts) if r.ts else None,
                        r.value,
                        r.source,
                        r.reason,
                        quarantined_at,
                    )
                    for r in rows
                ],
            )
            con.execute(f"COPY q TO '{self._path.as_posix()}' (FORMAT PARQUET)")
            return int(con.execute("SELECT count(*) FROM q").fetchone()[0])
        finally:
            con.close()

    def count(self) -> int:
        if not self._path.exists():
            return 0
        con = duckdb.connect()
        try:
            return int(
                con.execute(
                    f"SELECT count(*) FROM read_parquet('{self._path.as_posix()}')"
                ).fetchone()[0]
            )
        finally:
            con.close()
