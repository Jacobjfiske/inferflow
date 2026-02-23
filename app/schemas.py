from datetime import datetime

from pydantic import BaseModel, Field


class InferenceRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    model_version: str | None = None


class InferenceAcceptedResponse(BaseModel):
    job_id: str
    status: str
    idempotency_key: str | None = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: dict | None = None
    error: str | None = None
    retry_count: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
