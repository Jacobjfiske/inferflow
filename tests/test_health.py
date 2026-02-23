from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "service" in body


def test_ready_checks_dependencies(monkeypatch) -> None:
    class FakeRedisClient:
        def ping(self) -> bool:
            return True

    class FakeRedis:
        @staticmethod
        def from_url(_: str) -> FakeRedisClient:
            return FakeRedisClient()

    monkeypatch.setattr(main_module, "Redis", FakeRedis)

    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
