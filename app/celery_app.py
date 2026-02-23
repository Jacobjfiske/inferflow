from celery import Celery

from app.config import settings


celery = Celery(
    "ml_inference",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks"],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=settings.celery_task_eager_propagates,
    task_store_eager_result=True,
    task_time_limit=settings.inference_timeout_seconds,
    task_soft_time_limit=settings.inference_timeout_seconds,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
