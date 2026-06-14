import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_signup_creates_user_returns_token_no_password_hash(http_client: AsyncClient):
    resp = await http_client.post(
        "/api/v1/auth/signup",
        json={"email": "alice@integration.com", "password": "supersecret1"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["token"]
    assert data["user"]["email"] == "alice@integration.com"
    assert "password_hash" not in data["user"]
    assert "password" not in data["user"]


@pytest.mark.asyncio
async def test_signup_duplicate_email_returns_400(http_client: AsyncClient):
    payload = {"email": "bob@integration.com", "password": "supersecret1"}
    await http_client.post("/api/v1/auth/signup", json=payload)
    resp = await http_client.post("/api/v1/auth/signup", json=payload)
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "email_taken"


@pytest.mark.asyncio
async def test_login_correct_credentials_returns_200(http_client: AsyncClient):
    await http_client.post(
        "/api/v1/auth/signup",
        json={"email": "charlie@integration.com", "password": "supersecret1"},
    )
    resp = await http_client.post(
        "/api/v1/auth/login",
        json={"email": "charlie@integration.com", "password": "supersecret1"},
    )
    assert resp.status_code == 200
    assert resp.json()["token"]


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(http_client: AsyncClient):
    await http_client.post(
        "/api/v1/auth/signup",
        json={"email": "diana@integration.com", "password": "supersecret1"},
    )
    resp = await http_client.post(
        "/api/v1/auth/login",
        json={"email": "diana@integration.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["message"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_nonexistent_email_returns_401_same_message(http_client: AsyncClient):
    resp = await http_client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@integration.com", "password": "anypassword"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["message"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_me_returns_current_user(http_client: AsyncClient):
    signup_resp = await http_client.post(
        "/api/v1/auth/signup",
        json={"email": "eve@integration.com", "password": "supersecret1"},
    )
    token = signup_resp.json()["token"]

    resp = await http_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "eve@integration.com"


@pytest.mark.asyncio
async def test_me_no_token_returns_401(http_client: AsyncClient):
    resp = await http_client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_invalid_token_returns_401(http_client: AsyncClient):
    resp = await http_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer garbage.token.here"},
    )
    assert resp.status_code == 401
