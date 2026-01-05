import pytest

pytestmark = pytest.mark.asyncio


async def register(client, email="user@example.com", timezone="UTC"):
    return await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "secure-pass",
            "timezone": timezone,
        },
    )


async def test_register_success(client):
    response = await register(client)

    assert response.status_code == 201
    assert response.json()["email"] == "user@example.com"
    assert response.json()["timezone"] == "UTC"


async def test_register_duplicate_email(client):
    first = await register(client)
    second = await register(client)

    assert first.status_code == 201
    assert second.status_code == 409


async def test_register_invalid_timezone(client):
    response = await register(client, timezone="Invalid/Timezone")

    assert response.status_code == 422


async def test_login_success(client):
    await register(client)
    response = await client.post(
        "/auth/login",
        data={"username": "  USER@EXAMPLE.COM  ", "password": "secure-pass"},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


async def test_login_wrong_password(client):
    await register(client)
    response = await client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


async def test_me_requires_valid_token(client):
    missing = await client.get("/users/me")
    invalid = await client.get(
        "/users/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert missing.status_code == 401
    assert invalid.status_code == 401


async def test_me_with_valid_token(client):
    await register(client)
    login = await client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "secure-pass"},
    )
    token = login.json()["access_token"]

    response = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"


async def test_update_timezone(client):
    await register(client)
    login = await client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "secure-pass"},
    )
    token = login.json()["access_token"]

    response = await client.patch(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"timezone": "Europe/Moscow"},
    )

    assert response.status_code == 200
    assert response.json()["timezone"] == "Europe/Moscow"
