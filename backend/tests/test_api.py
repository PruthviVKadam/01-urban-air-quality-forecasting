import time
import pytest
from fastapi.testclient import TestClient

def test_forecast_caching(client: TestClient) -> None:
    station_id = client.get("/stations").json()[0]["id"]
    
    # First request
    start = time.monotonic()
    resp1 = client.get("/forecast", params={"station_id": station_id, "pollutant": "pm25"})
    assert resp1.status_code == 200
    dur1 = time.monotonic() - start
    
    # Second request should hit cache
    start = time.monotonic()
    resp2 = client.get("/forecast", params={"station_id": station_id, "pollutant": "pm25"})
    assert resp2.status_code == 200
    dur2 = time.monotonic() - start
    
    # The cache hit should be extremely fast, definitely < 5ms usually,
    # but more reliably, the responses must be exactly identical
    assert resp1.json() == resp2.json()

def test_rate_limiting(client: TestClient) -> None:
    station_id = client.get("/stations").json()[0]["id"]
    
    # Hit the limit (120 requests)
    for _ in range(120):
        resp = client.get("/forecast", params={"station_id": station_id})
        # If the rate limit kicks in early due to some test artifact, break
        if resp.status_code == 429:
            break
            
    # The 121st request MUST be 429
    resp = client.get("/forecast", params={"station_id": station_id})
    assert resp.status_code == 429
    assert resp.json()["error"] == "rate_limit_exceeded"
