"""
tests/test_security.py
───────────────────────
Unit tests for app/core/security.py

Covers:
  - Password hashing and verification (bcrypt)
  - JWT token creation and decoding
  - Token expiry and invalid token handling
"""

from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


# ── Password hashing ──────────────────────────────────────────────────────────

class TestPasswordHashing:

    def test_hash_returns_string(self):
        result = hash_password("mysecretpassword")
        assert isinstance(result, str)

    def test_hash_is_not_plaintext(self):
        plain = "mysecretpassword"
        assert hash_password(plain) != plain

    def test_same_plain_produces_different_hashes(self):
        """bcrypt uses a random salt — two hashes of the same plaintext differ."""
        h1 = hash_password("samepassword")
        h2 = hash_password("samepassword")
        assert h1 != h2

    def test_verify_correct_password_returns_true(self):
        plain = "correctpassword123"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_wrong_password_returns_false(self):
        hashed = hash_password("correctpassword123")
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_empty_password_returns_false(self):
        hashed = hash_password("somepassword")
        assert verify_password("", hashed) is False

    def test_verify_garbage_hash_returns_false(self):
        """Should not raise — just return False."""
        assert verify_password("anypassword", "not-a-valid-bcrypt-hash") is False

    def test_hash_unicode_password(self):
        plain = "पासवर्ड123"  # Hindi characters
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True


# ── JWT tokens ────────────────────────────────────────────────────────────────

class TestJWTTokens:

    def test_create_token_returns_string(self):
        token = create_access_token(subject=uuid4())
        assert isinstance(token, str)
        assert len(token) > 20

    def test_decode_valid_token_returns_subject(self):
        user_id = uuid4()
        token = create_access_token(subject=user_id)
        decoded = decode_access_token(token)
        assert decoded == str(user_id)

    def test_decode_token_with_string_subject(self):
        token = create_access_token(subject="user-123")
        assert decode_access_token(token) == "user-123"

    def test_decode_expired_token_returns_none(self):
        token = create_access_token(
            subject=uuid4(),
            expires_delta=timedelta(seconds=-1),  # already expired
        )
        assert decode_access_token(token) is None

    def test_decode_tampered_token_returns_none(self):
        token = create_access_token(subject=uuid4())
        tampered = token[:-5] + "XXXXX"
        assert decode_access_token(tampered) is None

    def test_decode_garbage_string_returns_none(self):
        assert decode_access_token("not.a.jwt") is None

    def test_decode_empty_string_returns_none(self):
        assert decode_access_token("") is None

    def test_extra_claims_are_included(self):
        """Extra claims survive the encode/decode round-trip."""
        from jose import jwt
        from app.core.config import settings

        user_id = uuid4()
        token = create_access_token(
            subject=user_id,
            extra_claims={"role": "admin"},
        )
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload.get("role") == "admin"
        assert payload.get("sub") == str(user_id)
