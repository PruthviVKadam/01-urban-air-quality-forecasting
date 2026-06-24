"""Last-known-good cache on disk.

Stores the most recent successful payload per key so the resilient client can serve
stale-but-usable data when an upstream is down (HL5). Survives process restarts.
"""

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CacheEntry:
    stored_at: float
    value: Any


class LastKnownGoodCache:
    def __init__(self, directory: Path, clock: Callable[[], float] = time.time) -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._clock = clock

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
        return self._dir / f"{digest}.json"

    def get(self, key: str) -> CacheEntry | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return CacheEntry(stored_at=raw["stored_at"], value=raw["value"])
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    def set(self, key: str, value: Any) -> None:
        path = self._path(key)
        payload = json.dumps({"stored_at": self._clock(), "value": value})
        # Write-then-rename for atomicity (no half-written cache files).
        tmp = path.with_suffix(".tmp")
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(path)

    def is_fresh(self, key: str, ttl_s: float) -> bool:
        entry = self.get(key)
        return entry is not None and (self._clock() - entry.stored_at) <= ttl_s
