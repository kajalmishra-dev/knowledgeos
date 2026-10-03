from io import BytesIO

import pytest

from tests.conftest import wait_for_document

SAMPLE = """# KnowledgeOS notes

KnowledgeOS stores notes in workspaces and answers questions from uploaded sources.

Paris is the capital of France.

The ingestion pipeline parses documents, chunks them, and stores embeddings in pgvector.
"""


@pytest.mark.integration
def test_upload_search_and_ask(db_client, auth_headers) -> None:
    workspace = db_client.post(
        "/api/v1/workspaces",
        headers=auth_headers,
        json={"name": "Research", "description": "Demo"},
    )
    assert workspace.status_code == 201
    workspace_id = workspace.json()["id"]

    upload = db_client.post(
        f"/api/v1/workspaces/{workspace_id}/documents",
        headers=auth_headers,
        files={"file": ("notes.md", SAMPLE.encode("utf-8"), "text/markdown")},
    )
    assert upload.status_code == 201
    document_id = upload.json()["id"]
    body = wait_for_document(db_client, auth_headers, workspace_id, document_id)
    assert body["status"] == "completed"
    assert body["chunk_count"] >= 1

    listing = db_client.get(
        f"/api/v1/workspaces/{workspace_id}/documents",
        headers=auth_headers,
    )
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    search = db_client.post(
        f"/api/v1/workspaces/{workspace_id}/search",
        headers=auth_headers,
        json={"query": "capital of France"},
    )
    assert search.status_code == 200
    hits = search.json()["hits"]
    assert hits
    assert "Paris" in hits[0]["content"]

    ask = db_client.post(
        f"/api/v1/workspaces/{workspace_id}/ask",
        headers=auth_headers,
        json={"question": "What is the capital of France?"},
    )
    assert ask.status_code == 200
    answer = ask.json()
    assert answer["grounded"] is True
    assert answer["citations"]
    assert "Paris" in answer["answer"]

    refuse = db_client.post(
        f"/api/v1/workspaces/{workspace_id}/ask",
        headers=auth_headers,
        json={"question": "What is the gluon plasma temperature in lattice QCD?"},
    )
    assert refuse.status_code == 200
    assert refuse.json()["grounded"] is False
    assert "don't have enough information" in refuse.json()["answer"]

    deleted = db_client.delete(
        f"/api/v1/workspaces/{workspace_id}/documents/{document_id}",
        headers=auth_headers,
    )
    assert deleted.status_code == 204


@pytest.mark.integration
def test_invalid_and_empty_files_are_rejected(db_client, auth_headers) -> None:
    workspace = db_client.post(
        "/api/v1/workspaces",
        headers=auth_headers,
        json={"name": "Uploads"},
    )
    workspace_id = workspace.json()["id"]

    empty = db_client.post(
        f"/api/v1/workspaces/{workspace_id}/documents",
        headers=auth_headers,
        files={"file": ("empty.md", b"", "text/markdown")},
    )
    assert empty.status_code == 400

    unsupported = db_client.post(
        f"/api/v1/workspaces/{workspace_id}/documents",
        headers=auth_headers,
        files={"file": ("malware.exe", b"MZ", "application/octet-stream")},
    )
    assert unsupported.status_code == 415

    unreadable = db_client.post(
        f"/api/v1/workspaces/{workspace_id}/documents",
        headers=auth_headers,
        files={"file": ("notes.md", b"\xff\xfe\x00\x00", "text/markdown")},
    )
    assert unreadable.status_code == 201
    body = wait_for_document(db_client, auth_headers, workspace_id, unreadable.json()["id"])
    assert body["status"] == "failed"
    assert body["error_message"]


@pytest.mark.integration
def test_oversized_file_is_rejected(db_client, auth_headers, monkeypatch) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "max_upload_bytes", 64)

    workspace = db_client.post(
        "/api/v1/workspaces",
        headers=auth_headers,
        json={"name": "Limits"},
    )
    workspace_id = workspace.json()["id"]
    oversized = db_client.post(
        f"/api/v1/workspaces/{workspace_id}/documents",
        headers=auth_headers,
        files={"file": ("big.md", b"x" * 128, "text/markdown")},
    )
    assert oversized.status_code == 413


@pytest.mark.integration
def test_workspace_isolation(db_client, unique_email) -> None:
    first = db_client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": "Password1"},
    )
    second = db_client.post(
        "/api/v1/auth/register",
        json={"email": f"other-{unique_email}", "password": "Password1"},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    owner = {"Authorization": f"Bearer {first.json()['access_token']}"}
    other = {"Authorization": f"Bearer {second.json()['access_token']}"}

    workspace = db_client.post(
        "/api/v1/workspaces",
        headers=owner,
        json={"name": "Private"},
    )
    workspace_id = workspace.json()["id"]
    stolen = db_client.get(f"/api/v1/workspaces/{workspace_id}", headers=other)
    assert stolen.status_code == 404


@pytest.mark.integration
def test_docx_ingest_and_search(db_client, auth_headers) -> None:
    from docx import Document as DocxDocument

    document = DocxDocument()
    document.add_paragraph("Berlin is the capital of Germany.")
    buffer = BytesIO()
    document.save(buffer)

    workspace = db_client.post(
        "/api/v1/workspaces",
        headers=auth_headers,
        json={"name": "Office"},
    )
    workspace_id = workspace.json()["id"]
    upload = db_client.post(
        f"/api/v1/workspaces/{workspace_id}/documents",
        headers=auth_headers,
        files={
            "file": (
                "notes.docx",
                buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert upload.status_code == 201
    body = wait_for_document(db_client, auth_headers, workspace_id, upload.json()["id"])
    assert body["status"] == "completed"

    search = db_client.post(
        f"/api/v1/workspaces/{workspace_id}/search",
        headers=auth_headers,
        json={"query": "capital of Germany"},
    )
    assert search.status_code == 200
    assert any("Berlin" in hit["content"] for hit in search.json()["hits"])
