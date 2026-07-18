import pytest


@pytest.mark.integration
def test_register_login_and_me(client, unique_email: str) -> None:
    password = "Password1"

    register = client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": password},
    )
    assert register.status_code == 201
    register_body = register.json()
    assert register_body["access_token"]
    assert register_body["user"]["email"] == unique_email

    login = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login.status_code == 200
    access_token = login.json()["access_token"]

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == unique_email
