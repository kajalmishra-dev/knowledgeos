# Live demo (about 5 minutes)

Use this after `docker compose up --build` and `GET /api/v1/ready` returns `ready`.

Swagger: http://localhost:8000/docs

Sample files: `docs/samples/france.md` and `docs/samples/pipeline.md`.

## Script

### 1. Register

`POST /api/v1/auth/register`

```json
{ "email": "demo@example.com", "password": "Password1" }
```

Copy `access_token`. In Swagger click **Authorize** and paste `Bearer <token>`.

### 2. Create a workspace

`POST /api/v1/workspaces`

```json
{ "name": "Research", "description": "Demo workspace" }
```

Copy `id`.

### 3. Upload knowledge

`POST /api/v1/workspaces/{id}/documents`  
Form field name: `file`  
Upload `docs/samples/france.md`.

If status is `pending`, poll `GET /api/v1/workspaces/{id}/documents/{document_id}` until `completed` or `failed`. With Docker Compose, the ARQ worker does ingestion asynchronously.

Repeat with `docs/samples/pipeline.md` if you want two sources.

### 4. Search

`POST /api/v1/workspaces/{id}/search`

```json
{ "query": "capital of France" }
```

You should see a hit containing **Paris** and a cosine score.

### 5. Ask (grounded)

`POST /api/v1/workspaces/{id}/ask`

```json
{ "question": "What is the capital of France?" }
```

Expect:

- `grounded: true`
- answer mentions Paris
- `citations` with filename + chunk index

Without `OPENAI_API_KEY` the answer is extractive (quoted chunks). Say that out loud: retrieval and citations are real; generation needs a chat provider.

### 6. Ask (refusal)

```json
{ "question": "What is the gluon plasma temperature in lattice QCD?" }
```

Expect `grounded: false` and a refusal. This is how the system avoids hallucinating when retrieval is weak.

### 7. Show architecture (30 seconds)

In the repo:

- `apps/backend/app/modules/` — auth, workspace, knowledge
- `apps/backend/app/infrastructure/` — Postgres, MinIO, ARQ, AI providers
- `apps/backend/app/workers/ingestion.py` — parse → chunk → embed → pgvector

Talking points: [INTERVIEW.md](INTERVIEW.md)

## PowerShell (no Swagger)

```powershell
$base = "http://localhost:8000/api/v1"
$register = Invoke-RestMethod -Method POST "$base/auth/register" -ContentType application/json `
  -Body '{"email":"demo@example.com","password":"Password1"}'
$auth = @{ Authorization = "Bearer $($register.access_token)" }

$ws = Invoke-RestMethod -Method POST "$base/workspaces" -Headers $auth -ContentType application/json `
  -Body '{"name":"Research","description":"Demo"}'

Invoke-RestMethod -Method POST "$base/workspaces/$($ws.id)/documents" -Headers $auth `
  -Form @{ file = Get-Item docs/samples/france.md }

Invoke-RestMethod -Method POST "$base/workspaces/$($ws.id)/search" -Headers $auth -ContentType application/json `
  -Body '{"query":"capital of France"}'

Invoke-RestMethod -Method POST "$base/workspaces/$($ws.id)/ask" -Headers $auth -ContentType application/json `
  -Body '{"question":"What is the capital of France?"}'
```
