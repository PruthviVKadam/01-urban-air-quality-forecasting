"""Timestamp helpers — everything internal is tz-aware UTC, hour-aligned."""

from datetime import UTC, datetime


def parse_iso_utc(value: str) -> datetime:
    """Parse an ISO-8601 string to a tz-aware UTC datetime (handles trailing 'Z')."""
    text = value.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def floor_to_hour(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
