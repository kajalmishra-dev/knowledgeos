import asyncio
import sys
import uuid
from time import monotonic

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine.url import make_url

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.core.config import get_settings
from app.dependencies.knowledge import (
    get_chat_provider,
    get_embedding_provider,
    get_job_queue,
    get_storage,
)
from app.infrastructure.ai.chat.extractive import ExtractiveChatProvider
from app.infrastructure.ai.embeddings.local import LocalEmbeddingProvider
from app.infrastructure.queue.inline import InlineJobQueue
from app.infrastructure.storage.memory import InMemoryStorage
from app.main import app


def postgres_reachable() -> bool:
    settings = get_settings()
    url = make_url(settings.database_url)
    try:
        import psycopg

        with psycopg.connect(
            host=url.host,
            port=url.port or 5432,
            dbname=url.database,
            user=url.username,
            password=url.password,
            connect_timeout=2,
        ) as connection:
            connection.execute("SELECT 1")
        return True
    except Exception:
        return False


@pytest.fixture
def client() -> TestClient:
    settings = get_settings()
    storage = InMemoryStorage()
    embeddings = LocalEmbeddingProvider(settings.embedding_dimensions)
    chat = ExtractiveChatProvider()
    queue = InlineJobQueue(settings, storage, embeddings)

    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_embedding_provider] = lambda: embeddings
    app.dependency_overrides[get_chat_provider] = lambda: chat
    app.dependency_overrides[get_job_queue] = lambda: queue

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def db_client(client: TestClient) -> TestClient:
    if not postgres_reachable():
        pytest.skip("PostgreSQL is not available at DATABASE_URL")
    return client


@pytest.fixture
def unique_email() -> str:
    return f"user-{uuid.uuid4()}@example.com"


@pytest.fixture
def auth_headers(db_client: TestClient, unique_email: str) -> dict[str, str]:
    register = db_client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": "Password1"},
    )
    assert register.status_code == 201
    token = register.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def wait_for_document(
    client: TestClient,
    headers: dict[str, str],
    workspace_id: str,
    document_id: str,
    *,
    timeout: float = 20.0,
) -> dict:
    deadline = monotonic() + timeout
    body: dict = {}
    while monotonic() < deadline:
        response = client.get(
            f"/api/v1/workspaces/{workspace_id}/documents/{document_id}",
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        if body["status"] in {"completed", "failed"}:
            return body
    raise AssertionError(f"Document {document_id} did not finish ingestion: {body}")
