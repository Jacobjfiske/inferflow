import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from celery.result import AsyncResult
from fastapi import Depends, FastAPI, Header
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.celery_app import celery
from app.config import settings
from app.database import get_db, init_db
from app.job_store import (
    create_job,
    get_job,
    get_job_by_idempotency_key,
    update_job_failed,
)
from app.logging_config import configure_logging
from app.metrics import metrics
from app.schemas import InferenceAcceptedResponse, InferenceRequest, JobStatusResponse
from app.tasks import run_inference


configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name}


@app.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    redis_client = Redis.from_url(settings.redis_url)
    redis_client.ping()
    return {"status": "ready", "service": settings.app_name}


@app.get("/metrics")
def get_metrics() -> dict[str, int]:
    return metrics.snapshot()


@app.post("/v1/inference", response_model=InferenceAcceptedResponse)
def create_inference_job(
    payload: InferenceRequest,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> InferenceAcceptedResponse:
    model_version = payload.model_version or settings.model_version

    if idempotency_key:
        # Reuse prior job when client retries the same request.
        existing = get_job_by_idempotency_key(db, idempotency_key)
        if existing:
            return InferenceAcceptedResponse(
                job_id=existing.job_id, status=existing.status, idempotency_key=idempotency_key
            )

    job_id = str(uuid4())
    create_job(
        db,
        job_id=job_id,
        input_text=payload.text,
        model_version=model_version,
        idempotency_key=idempotency_key,
    )
    try:
        run_inference.apply_async(args=(payload.text, model_version), task_id=job_id)
    except Exception as exc:
        update_job_failed(db, job_id, f"enqueue failed: {exc}", 0)
        raise

    metrics.inc_submitted()
    logger.info("job_queued", extra={"job_id": job_id, "status": "queued"})

    return InferenceAcceptedResponse(job_id=job_id, status="queued", idempotency_key=idempotency_key)


@app.get("/v1/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)) -> JobStatusResponse:
    record = get_job(db, job_id)
    if record:
        result = None
        if record.result_label is not None and record.result_score is not None:
            result = {
                "label": record.result_label,
                "score": record.result_score,
                "model_version": record.model_version,
            }
        return JobStatusResponse(
            job_id=job_id,
            status=record.status,
            result=result,
            error=record.error,
            retry_count=record.retry_count,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    # Fallback to broker state while migration data is absent.
    task = AsyncResult(job_id, app=celery)

    if task.state == "PENDING":
        return JobStatusResponse(job_id=job_id, status="queued")

    if task.state == "STARTED":
        return JobStatusResponse(job_id=job_id, status="started")

    if task.state == "SUCCESS":
        return JobStatusResponse(job_id=job_id, status="succeeded", result=task.result)

    if task.state == "FAILURE":
        return JobStatusResponse(job_id=job_id, status="failed", error=str(task.result))

    # Surface broker states that are not final.
    return JobStatusResponse(job_id=job_id, status=task.state.lower())
