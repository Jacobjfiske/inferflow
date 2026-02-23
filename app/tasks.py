import logging

from celery.exceptions import SoftTimeLimitExceeded

from app.celery_app import celery
from app.config import settings
from app.database import SessionLocal
from app.job_store import update_job_failed, update_job_started, update_job_succeeded
from app.metrics import metrics
from app.model import predict_text

logger = logging.getLogger(__name__)


@celery.task(
    bind=True,
    name="app.tasks.run_inference",
    autoretry_for=(RuntimeError,),
    retry_backoff=settings.retry_backoff_seconds,
    retry_jitter=True,
    retry_kwargs={"max_retries": settings.max_retries},
)
def run_inference(self, text: str, model_version: str) -> dict:
    db = SessionLocal()
    retry_count = int(self.request.retries or 0)
    # Persist start state before model work begins.
    update_job_started(db, self.request.id, retry_count)
    logger.info("inference_started", extra={"job_id": self.request.id, "status": "started"})

    try:
        prediction = predict_text(text)
        score = round(prediction.score, 4)
        update_job_succeeded(db, self.request.id, prediction.label, score)
        metrics.inc_succeeded()
        logger.info("inference_succeeded", extra={"job_id": self.request.id, "status": "succeeded"})

        return {
            "label": prediction.label,
            "score": score,
            "model_version": model_version,
        }
    except SoftTimeLimitExceeded as exc:
        error = f"inference timeout after {settings.inference_timeout_seconds}s"
        update_job_failed(db, self.request.id, error, retry_count)
        metrics.inc_failed()
        logger.exception("inference_timeout", extra={"job_id": self.request.id, "status": "failed"})
        raise exc
    except RuntimeError as exc:
        # Let Celery retry transient runtime failures.
        if retry_count >= settings.max_retries:
            update_job_failed(db, self.request.id, str(exc), retry_count)
            metrics.inc_failed()
            logger.exception("inference_failed", extra={"job_id": self.request.id, "status": "failed"})
        raise
    except Exception as exc:
        update_job_failed(db, self.request.id, str(exc), retry_count)
        metrics.inc_failed()
        logger.exception("inference_failed", extra={"job_id": self.request.id, "status": "failed"})
        raise
    finally:
        db.close()
