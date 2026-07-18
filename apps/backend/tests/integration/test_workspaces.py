import pytest


@pytest.mark.integration
def test_workspace_crud(client, unique_email: str) -> None:
    password = "Password1"

    register = client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": password},
    )
    assert register.status_code == 201
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={"name": "Research", "description": "My notes"},
    )
    assert create.status_code == 201
    workspace = create.json()
    workspace_id = workspace["id"]
    assert workspace["name"] == "Research"
    assert workspace["description"] == "My notes"

    listing = client.get("/api/v1/workspaces", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    fetched = client.get(f"/api/v1/workspaces/{workspace_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Research"

    updated = client.patch(
        f"/api/v1/workspaces/{workspace_id}",
        headers=headers,
        json={"name": "Research Hub"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Research Hub"

    deleted = client.delete(f"/api/v1/workspaces/{workspace_id}", headers=headers)
    assert deleted.status_code == 204

    missing = client.get(f"/api/v1/workspaces/{workspace_id}", headers=headers)
    assert missing.status_code == 404
