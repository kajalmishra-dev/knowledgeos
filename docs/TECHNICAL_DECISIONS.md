# Technical decisions

## Chunking: 800 characters, 150 overlap

Short factual notes fit in one window. Overlap keeps a sentence that would otherwise be split at a boundary. Separators prefer paragraphs, then sentences, then spaces (`chunking.py`). Changing size/overlap is env-only (`INGESTION_CHUNK_SIZE`, `INGESTION_CHUNK_OVERLAP`).

## pgvector in Postgres

One database for users, workspaces, documents, and vectors. HNSW cosine index on `document_chunks.embedding`. Dimension is **1536** (migration + `EMBEDDING_DIMENSIONS`). Changing dimension requires a new migration.

## ARQ on Redis, not Celery

The API is async. ARQ is Redis-native and small. The worker shares application code. Tests use an inline queue so pytest does not need Redis.

## Local hashing embeddings as the default

`LocalEmbeddingProvider` hashes tokens and character trigrams into a unit vector. Compose works without a paid API key. Overlapping terms rank closer; this is **not** neural semantic search. Set `EMBEDDING_PROVIDER=openai` for `text-embedding-3-small`.

Eval: `tests/eval/test_retrieval_quality.py` checks recall@1 on a four-document toy corpus for the local embedder (threshold 0.75).

## Extractive answers without a chat key

Default `CHAT_PROVIDER=extractive` quotes retrieved chunks and still returns citations. That is honest. It is not an LLM wrapper and not a chatbot. Same `QAService` path switches to OpenAI-compatible chat when configured.

## Refusal instead of guessing

`RETRIEVAL_MIN_SCORE` (default 0.18 for local embeddings). Empty or weak hits → `grounded: false`. Raise the threshold when you switch to neural embeddings.

## Object storage

Originals live in MinIO so the database does not hold blobs. Keys are `{workspace_id}/{document_id}/{safe_filename}`.

## JWT

Access token in the JSON body (~15 minutes). Refresh token in an httpOnly cookie, rotated on use. Production (`ENVIRONMENT=production`) refuses to boot with `JWT_SECRET_KEY=dev-only-change-me`.
