# InferFlow

Asynchronous ML inference service for text classification workloads.

## Stack
- FastAPI
- Celery
- Redis
- PostgreSQL
- SQLAlchemy
- Docker Compose

## What it does
- Accepts inference requests through an API.
- Queues work for background execution.
- Tracks lifecycle state for each job (`queued`, `started`, `succeeded`, `failed`).
- Supports idempotent request submission via `Idempotency-Key`.
- Persists job state, retry count, and failure reason in PostgreSQL.

## API
- `GET /health`
- `GET /ready`
- `GET /metrics`
- `POST /v1/inference`
- `GET /v1/jobs/{job_id}`

## Request flow
1. Client sends `POST /v1/inference` with text payload.
2. API validates request and checks optional `Idempotency-Key`.
3. API creates a job record and enqueues Celery task.
4. Worker executes inference and updates job state.
5. Client polls `GET /v1/jobs/{job_id}` for terminal result.

## Run locally (Docker)
```bash
# from this project directory
cp .env.example .env
docker compose up --build
```

## Demo requests
Submit job:
```bash
curl -X POST http://localhost:8000/v1/inference \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: demo-001' \
  -d '{"text":"limited time offer, click now"}'
```

Check job:
```bash
curl http://localhost:8000/v1/jobs/<job_id>
```

## Run without Docker
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Start worker in another terminal:
```bash
celery -A app.celery_app.celery worker --loglevel=info
```

## Test
```bash
pytest -q
```

## Reliability behavior implemented
- Automatic retries for transient task failures with backoff.
- Timeout controls via Celery task limits.
- Idempotency key handling to avoid duplicate jobs.
- Persistent failure reasons and retry counters.

## Benchmark
Run quick local benchmark:
```bash
bash ./bench.sh 20
```

Reported metrics include:
- success rate
- p50 latency
- p95 latency
- retry rate

Recent local sample run:
- success rate: 100%
- p50 latency: 12ms
- p95 latency: 14ms
- retry rate: 0%

## Files
- Architecture notes: `docs/architecture.md`
- Benchmark script: `bench.sh`
- Main API: `app/main.py`
- Worker task: `app/tasks.py`

## Current limits
- DB schema setup uses `create_all()` at startup, not migrations.
- `/metrics` uses in-process counters.
- No auth or rate limiting in this scope.
