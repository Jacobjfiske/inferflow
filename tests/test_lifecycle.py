from fastapi.testclient import TestClient

from app.main import app
from app.model import Prediction


client = TestClient(app)


def test_inference_job_lifecycle_success() -> None:
    create_response = client.post(
        "/v1/inference",
        json={"text": "Limited time offer, click now to win", "model_version": "v-test"},
    )
    assert create_response.status_code == 200
    job_id = create_response.json()["job_id"]

    status_response = client.get(f"/v1/jobs/{job_id}")
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["status"] == "succeeded"
    assert body["result"]["label"] == "spam"
    assert body["result"]["model_version"] == "v-test"


def test_idempotency_key_returns_existing_job() -> None:
    headers = {"Idempotency-Key": "abc-123"}
    payload = {"text": "hello world"}

    first = client.post("/v1/inference", headers=headers, json=payload)
    second = client.post("/v1/inference", headers=headers, json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["job_id"] == second.json()["job_id"]


def test_failure_reason_is_stored() -> None:
    from app import tasks

    original_predict = tasks.predict_text

    def fail_predict(_: str) -> Prediction:
        raise ValueError("simulated fatal failure")

    tasks.predict_text = fail_predict
    try:
        response = client.post(
            "/v1/inference",
            json={"text": "this request should fail in test"},
        )
    finally:
        tasks.predict_text = original_predict
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    status_response = client.get(f"/v1/jobs/{job_id}")
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["status"] == "failed"
    assert "simulated fatal failure" in body["error"]
