# Interview talking points

Open with the demo, then the design. Do not claim this is a production SaaS.

## One-sentence pitch

“I built a workspace-scoped RAG backend: JWT auth, object storage, an ingestion worker, pgvector search, and answers that cite sources or refuse.”

## What is real engineering (say this)

- Auth is not a fake middleware: hashed passwords, short-lived JWT, rotated refresh cookies
- Ingestion is asynchronous; the API does not parse PDFs on the request thread
- Files are in MinIO; vectors are in Postgres; the app talks to both through adapters
- Providers are swappable (`local` / OpenAI-compatible) without rewriting retrieval
- Weak retrieval returns `grounded: false` instead of a confident lie

## What is a tradeoff (say this too)

- Default embeddings are hashing vectors so `docker compose up` works without a key. Neural embeddings need `EMBEDDING_PROVIDER=openai`
- Default answers are extractive quotes unless a chat provider is configured
- This is a modular monolith, not microservices
- Retrieval eval is a tiny recall@1 check, not BEIR/MTEB

## Questions you should be able to answer

- Why 800/150 chunking?
- Why HNSW cosine and a fixed 1536-d column?
- What happens if MinIO is down during ingest? (transient retry via ARQ)
- What happens if the file is an encrypted PDF? (permanent `failed`)
- How do you stop user B from reading user A’s workspace? (owner check, 404)
- How would you swap Ollama for OpenAI? (`OPENAI_BASE_URL`)

## Code to keep open

1. `app/modules/knowledge/application/services/ingestion_service.py`
2. `app/modules/knowledge/application/services/qa_service.py`
3. `app/infrastructure/ai/factory.py`
4. `app/workers/ingestion.py`
