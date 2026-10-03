# Demo video (record this yourself)

This repo does not ship a rendered `.mp4`. Record a 3–4 minute walkthrough with OBS, ShareX, or Clipchamp using the shots below. Save the file as `docs/demo/knowledgeos-demo.mp4` if you want it next to these notes (the `docs/demo/` folder is gitignored if the video is large — or commit a short clip under 20 MB).

## Setup before you hit record

1. Docker Desktop running
2. `docker compose up --build` until `/api/v1/ready` is ready
3. Browser on http://localhost:8000/docs
4. VS Code showing `apps/backend/app/modules/knowledge` on the second screen (optional)

## Shot list

| Time | Picture | What you say |
|---|---|---|
| 0:00–0:20 | Repo root + `docker compose ps` | “KnowledgeOS is a FastAPI knowledge workspace: auth, workspaces, ingestion, pgvector search, grounded Q&A.” |
| 0:20–0:40 | `/ready` JSON | “Postgres, Redis, and MinIO are up. Migrations already ran.” |
| 0:40–1:10 | Swagger register + authorize | “JWT access token, httpOnly refresh cookie.” |
| 1:10–1:30 | Create workspace | “Data is scoped to the owner.” |
| 1:30–2:10 | Upload `france.md`, poll until `completed` | “File goes to MinIO. The ARQ worker parses, chunks, embeds, writes pgvector.” |
| 2:10–2:40 | Search `capital of France` | “Cosine search over chunk embeddings, not keyword-only SQL.” |
| 2:40–3:20 | Ask the same question | “Answer uses retrieved context and returns citations. No key → extractive quotes. With OpenAI, same pipeline, generated answer.” |
| 3:20–3:40 | Ask an unrelated question | “Weak retrieval → grounded false. We refuse instead of hallucinating.” |
| 3:40–4:00 | Code: `ingestion_service.py` + `qa_service.py` | “Business logic is in services. OpenAI/local providers sit behind protocols.” |

## On-screen text (optional captions)

- Upload → MinIO → Worker → pgvector
- Search = cosine kNN
- Ask = retrieve then generate or extract
- Refuse when score < threshold

## Do not do on camera

- Do not open `.env` with real keys
- Do not claim local hashing embeddings are production-quality
- Do not skip the refusal example — that is the anti-wrapper point
