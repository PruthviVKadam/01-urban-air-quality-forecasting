from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"]
    assert "time" in body
    assert isinstance(body["upstreams"], list) and body["upstreams"]


def test_request_id_is_echoed(client: TestClient) -> None:
    resp = client.get("/health", headers={"X-Request-ID": "test-123"})
    assert resp.headers.get("X-Request-ID") == "test-123"


def test_request_id_is_minted_when_absent(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.headers.get("X-Request-ID")
