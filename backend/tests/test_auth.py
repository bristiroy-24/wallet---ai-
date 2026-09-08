"""
tests/test_auth.py
───────────────────
Integration tests for POST /api/v1/auth/register and /auth/login.

Uses httpx.AsyncClient with ASGI transport — no real server.
Each test runs against a rolled-back in-memory SQLite DB.

Covers:
  - Successful registration returns 201 + user fields
  - Duplicate email returns 409
  - Successful login returns 200 + access_token
  - Wrong password returns 401
  - Unknown email returns 401
  - Token from login is a valid JWT
  - Password is never returned in any response
"""

import pytest
from httpx import AsyncClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL    = "/api/v1/auth/login"

VALID_USER = {
    "email":     "testuser@walletai.com",
    "password":  "strongpassword123",
    "full_name": "Test User",
}


# ── Registration ──────────────────────────────────────────────────────────────

class TestRegister:

    async def test_register_success_returns_201(self, client: AsyncClient):
        resp = await client.post(REGISTER_URL, json=VALID_USER)
        assert resp.status_code == 201

    async def test_register_returns_user_fields(self, client: AsyncClient):
        resp = await client.post(REGISTER_URL, json=VALID_USER)
        body = resp.json()
        assert body["email"] == VALID_USER["email"]
        assert body["full_name"] == VALID_USER["full_name"]
        assert "id" in body
        assert "created_at" in body

    async def test_register_does_not_return_password(self, client: AsyncClient):
        resp = await client.post(REGISTER_URL, json=VALID_USER)
        body = resp.json()
        assert "password" not in body
        assert "hashed_password" not in body

    async def test_register_duplicate_email_returns_409(self, client: AsyncClient):
        await client.post(REGISTER_URL, json=VALID_USER)
        resp2 = await client.post(REGISTER_URL, json=VALID_USER)
        assert resp2.status_code == 409
        assert "already exists" in resp2.json()["detail"]

    async def test_register_missing_email_returns_422(self, client: AsyncClient):
        resp = await client.post(REGISTER_URL, json={"password": "pass123"})
        assert resp.status_code == 422

    async def test_register_short_password_returns_422(self, client: AsyncClient):
        resp = await client.post(REGISTER_URL, json={
            "email": "short@test.com",
            "password": "abc",          # min_length=8
        })
        assert resp.status_code == 422

    async def test_register_invalid_email_returns_422(self, client: AsyncClient):
        resp = await client.post(REGISTER_URL, json={
            "email": "not-an-email",
            "password": "validpass123",
        })
        assert resp.status_code == 422

    async def test_register_without_full_name_succeeds(self, client: AsyncClient):
        resp = await client.post(REGISTER_URL, json={
            "email": "nofullname@test.com",
            "password": "validpass123",
        })
        assert resp.status_code == 201


# ── Login ─────────────────────────────────────────────────────────────────────

class TestLogin:

    @pytest.fixture(autouse=True)
    async def registered_user(self, client: AsyncClient):
        """Register the test user before every login test."""
        await client.post(REGISTER_URL, json=VALID_USER)

    async def test_login_success_returns_200(self, client: AsyncClient):
        resp = await client.post(LOGIN_URL, json={
            "email":    VALID_USER["email"],
            "password": VALID_USER["password"],
        })
        assert resp.status_code == 200

    async def test_login_returns_access_token(self, client: AsyncClient):
        resp = await client.post(LOGIN_URL, json={
            "email":    VALID_USER["email"],
            "password": VALID_USER["password"],
        })
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    async def test_login_token_is_valid_jwt(self, client: AsyncClient):
        resp = await client.post(LOGIN_URL, json={
            "email":    VALID_USER["email"],
            "password": VALID_USER["password"],
        })
        token = resp.json()["access_token"]
        from app.core.security import decode_access_token
        subject = decode_access_token(token)
        assert subject is not None  # valid JWT with a subject

    async def test_login_response_includes_user(self, client: AsyncClient):
        resp = await client.post(LOGIN_URL, json={
            "email":    VALID_USER["email"],
            "password": VALID_USER["password"],
        })
        user = resp.json().get("user", {})
        assert user.get("email") == VALID_USER["email"]

    async def test_login_wrong_password_returns_401(self, client: AsyncClient):
        resp = await client.post(LOGIN_URL, json={
            "email":    VALID_USER["email"],
            "password": "wrongpassword",
        })
        assert resp.status_code == 401
        assert "Incorrect" in resp.json()["detail"]

    async def test_login_unknown_email_returns_401(self, client: AsyncClient):
        resp = await client.post(LOGIN_URL, json={
            "email":    "ghost@nobody.com",
            "password": "doesnotmatter",
        })
        assert resp.status_code == 401

    async def test_login_missing_password_returns_422(self, client: AsyncClient):
        resp = await client.post(LOGIN_URL, json={"email": VALID_USER["email"]})
        assert resp.status_code == 422

    async def test_login_response_never_contains_hashed_password(self, client: AsyncClient):
        resp = await client.post(LOGIN_URL, json={
            "email":    VALID_USER["email"],
            "password": VALID_USER["password"],
        })
        body_str = resp.text
        assert "hashed_password" not in body_str
        assert VALID_USER["password"] not in body_str


# ── Protected endpoint reachability ──────────────────────────────────────────

class TestProtectedEndpoints:

    async def test_no_token_returns_401(self, client: AsyncClient):
        """Accessing a protected endpoint without a token should return 401."""
        resp = await client.get("/api/v1/accounts/")
        assert resp.status_code == 401

    async def test_invalid_token_returns_401(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/accounts/",
            headers={"Authorization": "Bearer thisisnotavalidtoken"},
        )
        assert resp.status_code == 401

    async def test_valid_token_reaches_endpoint(self, client: AsyncClient):
        """A valid JWT from login should allow access to protected endpoints."""
        # Register + login to get a token
        await client.post(REGISTER_URL, json=VALID_USER)
        login_resp = await client.post(LOGIN_URL, json={
            "email":    VALID_USER["email"],
            "password": VALID_USER["password"],
        })
        token = login_resp.json()["access_token"]

        # Access a protected endpoint
        resp = await client.get(
            "/api/v1/accounts/",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should be 200 (empty list is fine) — NOT 401
        assert resp.status_code == 200
