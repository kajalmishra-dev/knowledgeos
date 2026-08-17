# KnowledgeOS Backend

FastAPI modular monolith: auth, workspaces, document ingestion, semantic search, and grounded Q&A.

## Requirements

- Python 3.14
- Docker Compose services: Postgres (pgvector), Redis, MinIO — or the full stack via the repo-root compose file

## Setup

```powershell
cd apps/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Start infrastructure from the repo root:

```powershell
docker compose up postgres redis minio minio-init -d
```

## Run API

```powershell
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health: `GET http://localhost:8000/api/v1/health`  
Ready: `GET http://localhost:8000/api/v1/ready`  
Docs: `http://localhost:8000/docs`

## Run ingestion worker

```powershell
arq app.workers.ingestion.WorkerSettings
```

For a single-process demo without a worker, set `INGESTION_QUEUE=inline` in `.env`.

## Tests

```powershell
pytest
```

Integration tests skip automatically if Postgres is not reachable. Full walkthrough: [docs/HOW_TO_RUN.md](../docs/HOW_TO_RUN.md).

## Migrations

```powershell
alembic revision --autogenerate -m "description"
alembic upgrade head
```
