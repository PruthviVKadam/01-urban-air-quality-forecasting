from collections.abc import Iterator

import pytest
from app.main import app
from fastapi.testclient import TestClient
from app.cache import _cache, _rate_limits


@pytest.fixture
def client() -> Iterator[TestClient]:
    # Clear caches and rate limits before each test
    _cache.clear()
    _rate_limits.clear()
    
    # Context manager runs the lifespan so app.state.start_time is set.
    with TestClient(app) as c:
        yield c
