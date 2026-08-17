# KnowledgeOS

Production-minded knowledge workspace: upload documents, index them with a RAG pipeline, search semantically, and ask grounded questions with citations.

A recruiter can run Docker Compose, upload a Markdown/PDF/DOCX file, search it, ask a question, and inspect a real backend/AI architecture rather than an LLM wrapper.

**Docs:** [docs/README.md](docs/README.md) · [How to run](docs/HOW_TO_RUN.md) · [Demo](docs/DEMO.md) · [Demo video script](docs/DEMO_VIDEO.md) · [Architecture](docs/ARCHITECTURE.md)

---

## What it does

- Register/login with JWT access tokens and httpOnly refresh cookies
- Create and manage workspaces
- Upload PDF, Markdown, TXT, and DOCX files (10 MB default limit)
- Store originals in MinIO
- Ingest in the background: parse → chunk → embed → index in PostgreSQL/pgvector
- Semantic search over a workspace
- Ask questions with retrieved context and source citations
- Refuse to answer when retrieval is empty or too weak
- Survive invalid, empty, encrypted, and oversized files without crashing

---

## Fresh setup

### Prerequisites

- Docker and Docker Compose
- Optional: an OpenAI-compatible API key for neural embeddings and generated answers

### Start everything

```powershell
Copy-Item .env.example .env
docker compose up --build
```

This starts PostgreSQL 17 + pgvector, Redis, MinIO, the FastAPI API, and the ARQ ingestion worker. The API runs migrations on startup.

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health
- Ready: http://localhost:8000/api/v1/ready
- MinIO console: http://localhost:9001 (`minioadmin` / `minioadmin`)

Without `OPENAI_API_KEY`, the app uses local hashing embeddings and extractive answers so the demo still works. For generated answers:

```env
EMBEDDING_PROVIDER=openai
CHAT_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
```

`OPENAI_BASE_URL` can point at OpenAI, Groq, or Ollama. Embedding and chat providers are swappable without rewriting the pipeline.

---

## End-to-end demo

```powershell
# 1. Register
$register = Invoke-RestMethod -Method POST http://localhost:8000/api/v1/auth/register `
  -ContentType application/json `
  -Body '{"email":"demo@example.com","password":"Password1"}'
$token = $register.access_token
$auth = @{ Authorization = "Bearer $token" }

# 2. Create a workspace
$workspace = Invoke-RestMethod -Method POST http://localhost:8000/api/v1/workspaces `
  -Headers $auth -ContentType application/json `
  -Body '{"name":"Research","description":"Demo workspace"}'
$workspaceId = $workspace.id

# 3. Upload a knowledge source
@"
# France
Paris is the capital of France.
KnowledgeOS answers questions using retrieved document chunks.
"@ | Set-Content -Encoding utf8 notes.md

Invoke-RestMethod -Method POST "http://localhost:8000/api/v1/workspaces/$workspaceId/documents" `
  -Headers $auth -Form @{ file = Get-Item notes.md }

# 4. Search
Invoke-RestMethod -Method POST "http://localhost:8000/api/v1/workspaces/$workspaceId/search" `
  -Headers $auth -ContentType application/json `
  -Body '{"query":"capital of France"}'

# 5. Ask (answers include citations when grounded)
Invoke-RestMethod -Method POST "http://localhost:8000/api/v1/workspaces/$workspaceId/ask" `
  -Headers $auth -ContentType application/json `
  -Body '{"question":"What is the capital of France?"}'
```

Poll `GET /api/v1/workspaces/{id}/documents/{document_id}` until `status` is `completed` or `failed`. With Docker Compose, ingestion is asynchronous via Redis/ARQ. Failed jobs can be retried with `POST .../documents/{id}/reprocess`.

---

## Architecture

```
API (FastAPI)
  auth / workspaces / documents / search / ask
        │
        ├─ application services (use cases)
        │     document upload, ingestion, retrieval, QA
        ├─ infrastructure adapters
        │     PostgreSQL, MinIO, Redis/ARQ, embedding+chat providers
        └─ worker
              parse → chunk → embed → pgvector
```

Boundaries:

- **API** — HTTP, auth dependencies, Pydantic request/response models
- **Application** — workspace ownership, ingestion, retrieval, prompt construction
- **Infrastructure** — SQLAlchemy models, MinIO, ARQ, OpenAI-compatible HTTP, local embedding fallback
- **Domain errors** — `AppError` mapped to consistent `{"detail": "..."}` responses

Business logic is not in route handlers. External services sit behind protocols (`ObjectStorage`, `JobQueue`, `EmbeddingProvider`, `ChatProvider`).

### RAG pipeline

1. Validate type/size, store the original in MinIO, insert a `pending` document row
2. Enqueue `ingest_document` on Redis (ARQ)
3. Worker parses PDF/DOCX/Markdown/TXT
4. Recursive chunking: **800 characters, 150 overlap**, preferring paragraph then sentence breaks
5. Embeddings stored as `vector(1536)` with an HNSW cosine index
6. Search embeds the query and ranks by cosine similarity
7. Ask retrieves top-k chunks, refuses if the best score is below `RETRIEVAL_MIN_SCORE` (default `0.18`), otherwise generates an answer with `[n]` citations

### Chunking and embeddings

| Setting | Default | Why |
|---|---|---|
| Chunk size | 800 chars | Fits short factual passages without blowing the prompt |
| Overlap | 150 chars | Keeps sentences split at a window boundary |
| Dimensions | 1536 | Matches `text-embedding-3-small`; changing this needs a new migration |
| Local embeddings | token + trigram hashing | Lets Compose demo without an API key; not production retrieval quality |
| OpenAI embeddings | `text-embedding-3-small` | Replaceable via `OPENAI_BASE_URL` |

If the chat provider is unset or fails, KnowledgeOS falls back to an extractive answer that quotes retrieved chunks instead of hallucinating.

### Retrieval failure

Ask returns `grounded: false` and a refusal message when:

- the workspace has no completed documents
- retrieval returns no chunks
- the best cosine score is below `RETRIEVAL_MIN_SCORE`

---

## API surface

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Login |
| GET | `/api/v1/auth/me` | Current user |
| CRUD | `/api/v1/workspaces` | Workspaces |
| POST | `/api/v1/workspaces/{id}/documents` | Upload (`multipart/form-data` field `file`) |
| GET | `/api/v1/workspaces/{id}/documents` | List |
| POST | `/api/v1/workspaces/{id}/search` | Semantic search |
| POST | `/api/v1/workspaces/{id}/ask` | Grounded Q&A |
| GET | `/api/v1/health` | Liveness |
| GET | `/api/v1/ready` | Postgres + Redis + MinIO |

---

## Tests

Integration tests need PostgreSQL with pgvector (the Compose `postgres` service).

```powershell
cd apps/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
pytest
```

Unit tests cover chunking, parsers, local embeddings, and refusal/citation helpers. Integration tests cover auth, workspaces, upload → ingest → search → ask, and invalid uploads.

---

## Project layout

```
apps/backend/app/
  api/v1/                 HTTP routers
  core/                   settings, logging, errors
  dependencies/           FastAPI DI
  infrastructure/         DB, MinIO, Redis/ARQ, AI providers
  modules/auth|workspace|knowledge
  workers/ingestion.py    ARQ worker
infrastructure/docker/    backend image + entrypoint (runs Alembic)
infrastructure/postgres/  pgvector extension
infrastructure/minio/     bucket bootstrap
```

---

## Technical decisions

- **Modular monolith** — one deployable FastAPI app, module boundaries instead of microservices
- **ARQ over Celery** — async, Redis-native, small operational footprint
- **pgvector in Postgres** — no separate vector database for this scale
- **Provider protocols** — swap OpenAI/Ollama/local without touching retrieval or HTTP
- **Inline ingestion queue** — used by tests so pytest does not need Redis/MinIO
- Secrets come from environment variables; `.env` is gitignored
