# KnowledgeOS Backend

FastAPI application scaffold for the KnowledgeOS modular monolith.

## Requirements

- Python 3.14 (local installation)
- pip

## Setup

```powershell
cd apps/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
```

## Run

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: `GET http://localhost:8000/api/v1/health`

## Migrations

```powershell
alembic revision --autogenerate -m "description"
alembic upgrade head
```
