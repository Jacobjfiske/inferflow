# Architecture

## System Diagram

```mermaid
flowchart LR
    C[Client]
    API[FastAPI API Service]
    R[(Redis\nBroker + Result Backend)]
    W[Celery Worker]
    DB[(PostgreSQL\nJobs Table)]

    C -->|POST /v1/inference| API
    API -->|enqueue task| R
    API -->|insert queued job| DB
    W -->|consume task| R
    W -->|update started/succeeded/failed| DB
    C -->|GET /v1/jobs/{job_id}| API
    API -->|read durable status/result| DB
```

## Request Flow

1. Client submits text to `POST /v1/inference`.
2. API validates payload, applies idempotency check, enqueues Celery task.
3. API creates durable job record in PostgreSQL with `queued` state.
4. Worker reads the task from Redis and marks job `started`.
5. Worker runs inference and writes terminal state:
   - `succeeded` with `label` and `score`
   - `failed` with terminal error reason
6. Client polls `GET /v1/jobs/{job_id}` to retrieve durable job state.

## Reliability Notes

- Retries/backoff are applied for transient worker failures.
- Timeout guards prevent stuck tasks from running indefinitely.
- Idempotency keys prevent accidental duplicate job creation.
- Durable state in PostgreSQL makes status API robust across process restarts.
