from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.model import Prediction


client = TestClient(app)


def test_transient_error_retries_and_succeeds() -> None:
    from app import tasks

    original_predict = tasks.predict_text
    attempts = {"count": 0}

    def flaky_predict(_: str) -> Prediction:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("simulated transient failure")
        return Prediction(label="ham", score=0.9)

    tasks.predict_text = flaky_predict
    try:
        response = client.post(
            "/v1/inference",
            json={"text": "retry scenario"},
        )
    finally:
        tasks.predict_text = original_predict
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    body = None
    for _ in range(30):
        status = client.get(f"/v1/jobs/{job_id}")
        assert status.status_code == 200
        body = status.json()
        if body["status"] in {"succeeded", "failed"}:
            break

    assert body is not None
    assert body["status"] == "succeeded"
    assert body["retry_count"] is not None
    assert body["retry_count"] >= 1
    assert body["result"]["label"] == "ham"


def test_transient_error_retry_exhaustion_fails() -> None:
    from app import tasks

    original_predict = tasks.predict_text

    def always_fail_predict(_: str) -> Prediction:
        raise RuntimeError("persistent transient failure")

    tasks.predict_text = always_fail_predict
    try:
        response = client.post(
            "/v1/inference",
            json={"text": "retry exhaustion scenario"},
        )
    finally:
        tasks.predict_text = original_predict
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    body = None
    for _ in range(40):
        status = client.get(f"/v1/jobs/{job_id}")
        assert status.status_code == 200
        body = status.json()
        if body["status"] in {"succeeded", "failed"}:
            break

    assert body is not None
    assert body["status"] == "failed"
    assert body["retry_count"] is not None
    assert body["retry_count"] >= settings.max_retries
    assert "persistent transient failure" in (body["error"] or "")
