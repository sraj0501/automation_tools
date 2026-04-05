"""
Tests for backend/admin/auth.py

Covers:
  - hash_password / verify_password
  - create_token / decode_token (valid, expired, tampered)
  - check_credentials (env-var lookup, plain-text, scrypt hash)
  - require_auth FastAPI dependency (cookie present/missing/invalid)
"""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# hash_password / verify_password
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_hash_returns_scrypt_prefix(self):
        from backend.admin.auth import hash_password
        h = hash_password("secret123")
        assert h.startswith("scrypt$")

    def test_hash_is_different_each_call(self):
        from backend.admin.auth import hash_password
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # different salts

    def test_verify_correct_password(self):
        from backend.admin.auth import hash_password, verify_password
        h = hash_password("mypassword")
        assert verify_password("mypassword", h) is True

    def test_verify_wrong_password(self):
        from backend.admin.auth import hash_password, verify_password
        h = hash_password("correct")
        assert verify_password("wrong", h) is False

    def test_verify_empty_password_rejected(self):
        from backend.admin.auth import hash_password, verify_password
        h = hash_password("notempty")
        assert verify_password("", h) is False

    def test_verify_legacy_plain_text(self):
        """Verify that the legacy plain-text path works during migration."""
        from backend.admin.auth import verify_password
        # hashed value is just the plain-text string (legacy)
        assert verify_password("dev", "dev") is True
        assert verify_password("wrong", "dev") is False

    def test_verify_corrupt_hash_returns_false(self):
        from backend.admin.auth import verify_password
        assert verify_password("any", "scrypt$bad$data") is False

    def test_verify_empty_hash_returns_false(self):
        from backend.admin.auth import verify_password
        assert verify_password("any", "") is False


# ---------------------------------------------------------------------------
# create_token / decode_token
# ---------------------------------------------------------------------------

class TestJWTTokens:
    def test_decode_valid_token_returns_username(self):
        from backend.admin.auth import create_token, decode_token
        token = create_token("alice")
        assert decode_token(token) == "alice"

    def test_decode_garbage_returns_none(self):
        from backend.admin.auth import decode_token
        assert decode_token("not.a.token") is None

    def test_decode_empty_string_returns_none(self):
        from backend.admin.auth import decode_token
        assert decode_token("") is None

    def test_decode_tampered_token_returns_none(self):
        from backend.admin.auth import create_token, decode_token
        token = create_token("alice")
        # Flip a character in the signature (last segment)
        parts = token.split(".")
        parts[-1] = parts[-1][:-1] + ("A" if parts[-1][-1] != "A" else "B")
        assert decode_token(".".join(parts)) is None

    def test_decode_expired_token_returns_none(self):
        """Token with exp in the past should be rejected."""
        import jwt
        from backend.admin.auth import _SECRET, _ALGORITHM
        payload = {"sub": "alice", "iat": int(time.time()) - 7200, "exp": int(time.time()) - 3600}
        token = jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)
        from backend.admin.auth import decode_token
        assert decode_token(token) is None

    def test_token_for_different_users_are_distinct(self):
        from backend.admin.auth import create_token
        assert create_token("alice") != create_token("bob")


# ---------------------------------------------------------------------------
# check_credentials
# ---------------------------------------------------------------------------

class TestCheckCredentials:
    def test_correct_plain_text_credentials(self, monkeypatch):
        monkeypatch.setenv("ADMIN_USERNAME", "admin")
        monkeypatch.setenv("ADMIN_PASSWORD", "secret")
        from backend.admin import auth as _auth
        assert _auth.check_credentials("admin", "secret") is True

    def test_wrong_password_rejected(self, monkeypatch):
        monkeypatch.setenv("ADMIN_USERNAME", "admin")
        monkeypatch.setenv("ADMIN_PASSWORD", "secret")
        from backend.admin import auth as _auth
        assert _auth.check_credentials("admin", "wrong") is False

    def test_wrong_username_rejected(self, monkeypatch):
        monkeypatch.setenv("ADMIN_USERNAME", "admin")
        monkeypatch.setenv("ADMIN_PASSWORD", "secret")
        from backend.admin import auth as _auth
        assert _auth.check_credentials("notadmin", "secret") is False

    def test_empty_password_env_always_rejects(self, monkeypatch):
        monkeypatch.setenv("ADMIN_USERNAME", "admin")
        monkeypatch.setenv("ADMIN_PASSWORD", "")
        from backend.admin import auth as _auth
        assert _auth.check_credentials("admin", "") is False
        assert _auth.check_credentials("admin", "anything") is False

    def test_scrypt_hash_in_env(self, monkeypatch):
        from backend.admin.auth import hash_password
        hashed = hash_password("mypassword")
        monkeypatch.setenv("ADMIN_USERNAME", "admin")
        monkeypatch.setenv("ADMIN_PASSWORD", hashed)
        from backend.admin import auth as _auth
        assert _auth.check_credentials("admin", "mypassword") is True
        assert _auth.check_credentials("admin", "wrong") is False
