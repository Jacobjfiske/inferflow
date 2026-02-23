from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "inferflow")
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    model_version: str = os.getenv("MODEL_VERSION", "v1")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    inference_timeout_seconds: int = int(os.getenv("INFERENCE_TIMEOUT_SECONDS", "15"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    retry_backoff_seconds: int = int(os.getenv("RETRY_BACKOFF_SECONDS", "2"))
    celery_task_always_eager: bool = os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"
    celery_task_eager_propagates: bool = os.getenv("CELERY_TASK_EAGER_PROPAGATES", "false").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
