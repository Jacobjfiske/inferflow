from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_inference_rejects_empty_text() -> None:
    response = client.post("/v1/inference", json={"text": ""})
    assert response.status_code == 422


def test_inference_rejects_too_long_text() -> None:
    response = client.post("/v1/inference", json={"text": "a" * 5001})
    assert response.status_code == 422
