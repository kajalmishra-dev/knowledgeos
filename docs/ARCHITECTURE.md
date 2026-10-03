# Architecture

KnowledgeOS is a **modular monolith**: one FastAPI process, one ARQ worker, Postgres, Redis, MinIO.

```
                    ┌─────────────┐
   Browser/Swagger  │  FastAPI    │
                    │  /api/v1    │
                    └──────┬──────┘
           ┌───────────────┼────────────────┐
           ▼               ▼                ▼
     PostgreSQL          Redis            MinIO
     + pgvector        (ARQ jobs)      (original files)
                           │
                           ▼
                     ingestion worker
                     parse → chunk → embed → index
```

## Layers

| Layer | Location | Owns |
|---|---|---|
| API | `app/modules/*/api`, `app/api/v1` | HTTP, auth dependencies, response models |
| Application | `app/modules/*/application` | Upload, ingestion, retrieval, QA, workspace rules |
| Infrastructure | `app/infrastructure` | SQLAlchemy, MinIO, ARQ, OpenAI HTTP, local embeddings |
| Worker | `app/workers/ingestion.py` | Background ingest jobs |

External systems are behind protocols: `ObjectStorage`, `JobQueue`, `EmbeddingProvider`, `ChatProvider`.

## Request paths

**Upload**  
Validate type/size → put object in MinIO → insert `documents` row (`pending`) → enqueue `ingest_document`.

**Ingest**  
Load bytes → parse PDF/DOCX/Markdown/TXT → chunk (800/150) → embed → insert `document_chunks` with `vector(1536)` → `completed` or `failed`. Parse errors are permanent. Storage/embedding outages are retried by ARQ.

**Search**  
Embed query → cosine kNN over chunks in that workspace.

**Ask**  
Search → if best score `< RETRIEVAL_MIN_SCORE`, refuse → else generate (OpenAI-compatible) or extract quotes (default).

## AuthZ

Workspaces and documents are owner-scoped. Another user gets `404`, not a leak that the row exists.
