from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db_models import JobRecord


def get_job(db: Session, job_id: str) -> JobRecord | None:
    return db.get(JobRecord, job_id)


def get_job_by_idempotency_key(db: Session, idempotency_key: str) -> JobRecord | None:
    stmt = select(JobRecord).where(JobRecord.idempotency_key == idempotency_key)
    return db.execute(stmt).scalar_one_or_none()


def create_job(
    db: Session,
    *,
    job_id: str,
    input_text: str,
    model_version: str,
    idempotency_key: str | None,
) -> JobRecord:
    record = JobRecord(
        job_id=job_id,
        input_text=input_text,
        model_version=model_version,
        idempotency_key=idempotency_key,
        status="queued",
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if idempotency_key:
            existing = get_job_by_idempotency_key(db, idempotency_key)
            if existing:
                return existing
        raise
    db.refresh(record)
    return record


def update_job_started(db: Session, job_id: str, retry_count: int) -> None:
    record = get_job(db, job_id)
    if not record:
        return

    record.status = "started"
    record.retry_count = retry_count
    db.commit()


def update_job_succeeded(db: Session, job_id: str, label: str, score: float) -> None:
    record = get_job(db, job_id)
    if not record:
        return

    record.status = "succeeded"
    record.result_label = label
    record.result_score = score
    record.error = None
    db.commit()


def update_job_failed(db: Session, job_id: str, error: str, retry_count: int) -> None:
    record = get_job(db, job_id)
    if not record:
        return

    record.status = "failed"
    record.error = error
    record.retry_count = retry_count
    db.commit()
