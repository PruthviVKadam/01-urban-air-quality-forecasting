from collections.abc import Iterator

import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> Iterator[TestClient]:
    # Context manager runs the lifespan so app.state.start_time is set.
    with TestClient(app) as c:
        yield c
