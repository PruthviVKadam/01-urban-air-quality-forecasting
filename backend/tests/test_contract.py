"""Contract tests — the hard limits are verified at the API boundary, not just in code.

If any of these fail, the contract is shipping a payload that violates rules.md.
"""

from fastapi.testclient import TestClient


def test_stations_carry_freshness(client: TestClient) -> None:
    resp = client.get("/stations")
    assert resp.status_code == 200
    stations = resp.json()
    assert stations, "expected at least one station"
    for s in stations:
        assert s.get("data_as_of")  # HL1
        assert isinstance(s["stale"], bool)  # HL1
        for reading in s["latest"]:
            assert "interpolated" in reading  # HL3
            assert reading["value"] >= 0


def test_forecast_encodes_hard_limits(client: TestClient) -> None:
    station_id = client.get("/stations").json()[0]["id"]
    resp = client.get("/forecast", params={"station_id": station_id, "pollutant": "pm25"})
    assert resp.status_code == 200
    body = resp.json()

    # HL1 — freshness.
    assert body["data_as_of"] and isinstance(body["stale"], bool)
    # HL2 — baseline shadow.
    assert body["baseline_label"]
    assert isinstance(body["beats_baseline"], bool)
    # HL4 — not medical guidance.
    assert "not medical guidance" in body["disclaimer"].lower()

    assert body["points"], "expected forecast points"
    for p in body["points"]:
        assert p["baseline"] >= 0  # HL2 per-point baseline present
        assert "interpolated" in p  # HL3
        assert p["value"] >= 0 and p["lower"] >= 0 and p["upper"] >= 0
        assert p["lower"] <= p["value"] <= p["upper"]


def test_forecast_rejects_horizon_over_max(client: TestClient) -> None:
    station_id = client.get("/stations").json()[0]["id"]
    resp = client.get("/forecast", params={"station_id": station_id, "horizon": 999})
    assert resp.status_code == 422
    assert resp.json()["code"]  # uniform error envelope


def test_unknown_station_returns_error_envelope(client: TestClient) -> None:
    resp = client.get("/forecast", params={"station_id": "does-not-exist"})
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"] and body["code"] == "not_found"
    assert "request_id" in body
