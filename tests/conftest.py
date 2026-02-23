import os
from pathlib import Path

import pytest

# Ensure tests do not require Redis/Postgres services.
os.environ["DATABASE_URL"] = f"sqlite:///{Path('test_app.db').absolute()}"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["CELERY_TASK_EAGER_PROPAGATES"] = "false"
os.environ["CELERY_BROKER_URL"] = "memory://"
os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"


@pytest.fixture(scope="session", autouse=True)
def setup_test_db() -> None:
    from app.database import Base, engine, init_db

    Base.metadata.drop_all(bind=engine)
    init_db()
