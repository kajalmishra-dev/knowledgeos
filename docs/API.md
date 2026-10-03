# API

Base URL: `http://localhost:8000/api/v1`  
Auth: `Authorization: Bearer <access_token>` except register/login/refresh/logout/health/ready.

## Auth

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/register` | Password: 8+ chars, upper, lower, digit |
| POST | `/auth/login` | Sets refresh cookie |
| POST | `/auth/refresh` | Cookie in, new access token out |
| POST | `/auth/logout` | Revokes refresh cookie |
| GET | `/auth/me` | Current user |

## Workspaces

| Method | Path |
|---|---|
| POST | `/workspaces` |
| GET | `/workspaces` |
| GET | `/workspaces/{id}` |
| PATCH | `/workspaces/{id}` |
| DELETE | `/workspaces/{id}` |

## Documents

| Method | Path | Notes |
|---|---|---|
| POST | `/workspaces/{id}/documents` | multipart field `file` (PDF, MD, TXT, DOCX, 10 MB) |
| GET | `/workspaces/{id}/documents` | List |
| GET | `/workspaces/{id}/documents/{doc_id}` | Status: pending / processing / completed / failed |
| POST | `/workspaces/{id}/documents/{doc_id}/reprocess` | Retry failed jobs |
| DELETE | `/workspaces/{id}/documents/{doc_id}` | Drops object + chunks |

## RAG

`POST /workspaces/{id}/search`

```json
{ "query": "capital of France", "top_k": 5 }
```

`POST /workspaces/{id}/ask`

```json
{ "question": "What is the capital of France?", "top_k": 5 }
```

Response includes `answer`, `grounded`, `citations`, `retrieved`.

## Ops

| Method | Path |
|---|---|
| GET | `/health` |
| GET | `/ready` |
