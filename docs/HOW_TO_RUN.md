# How to run KnowledgeOS

## What you need

- Docker Desktop (or another Docker Engine + Compose v2)
- Optional: Python 3.14 if you want to run tests on the host
- Optional: `OPENAI_API_KEY` for neural embeddings and generated answers

Without an API key the stack still runs. Embeddings are local hashing vectors and answers are extractive quotes from retrieved chunks. That is enough to show the pipeline. It is **not** production retrieval quality.

## 1. Start the stack

From the repository root:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Wait until `knowledgeos-backend` is healthy. Then:

| URL | Purpose |
|---|---|
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/api/v1/health | Liveness |
| http://localhost:8000/api/v1/ready | Postgres + Redis + MinIO |
| http://localhost:9001 | MinIO console (`minioadmin` / `minioadmin`) |

First boot runs Alembic migrations inside the API container.

## 2. Confirm readiness

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/health
Invoke-RestMethod http://localhost:8000/api/v1/ready
```

`ready` must look like:

```json
{
  "status": "ready",
  "checks": { "database": true, "redis": true, "storage": true }
}
```

If `ready` is `503`, the API is up but a dependency is not. Check `docker compose ps` and container logs.

## 3. Demo the product

Follow [DEMO.md](DEMO.md). Sample files are in [samples/](samples/).

## 4. Neural RAG (optional)

In the root `.env`:

```env
EMBEDDING_PROVIDER=openai
CHAT_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
```

`OPENAI_BASE_URL` can point at Groq or Ollama (`http://host.docker.internal:11434/v1`). Recreate:

```powershell
docker compose up -d --force-recreate backend worker
```

## 5. Tests on the host

```powershell
cd apps/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
pytest
```

- Unit + eval tests do **not** need Docker.
- Integration tests need Postgres at `DATABASE_URL`. If Postgres is down they **skip**, they do not fail the whole suite.
- Integration tests use in-memory storage and an inline ingestion queue so they do not need MinIO/Redis.

To test against Compose Postgres, keep `DATABASE_URL` pointed at `localhost:5432` with user/password `postgres` / `postgres` and database `knowledgeos`. If you already have another Postgres on 5432, change `POSTGRES_PORT` in `.env` (for example `5433`) and match `DATABASE_URL`.

## 6. Run API + worker on the host

```powershell
docker compose up postgres redis minio minio-init -d
cd apps/backend
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```powershell
cd apps/backend
.\.venv\Scripts\Activate.ps1
arq app.workers.ingestion.WorkerSettings
```

## Troubleshooting

| Symptom | What to do |
|---|---|
| Docker daemon errors | Start Docker Desktop, wait until it is running, retry `docker compose up` |
| Port 5432 already in use | Set `POSTGRES_PORT=5433` in `.env` and update host `DATABASE_URL` |
| Upload stays `pending` | Worker is down. `docker compose logs worker` |
| Upload is `failed` | Read `error_message` on the document. Encrypted PDFs and empty files fail on purpose |
| `ready.storage` is false | MinIO bucket init did not finish. Re-run `docker compose up minio-init` |
| Production JWT error | Set a real `JWT_SECRET_KEY`. The default `dev-only-change-me` is rejected when `ENVIRONMENT=production` |
| Python 3.14 missing | Use the Docker API container; host tests need 3.14 because `requires-python = ">=3.14"` |
