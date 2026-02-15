import pytest
from fastapi import HTTPException

from app.core import security


class DummyQuery:
    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return None


class DummySession:
    def query(self, *args, **kwargs):
        return DummyQuery()


def test_get_current_user_rejects_non_int_sub(monkeypatch):
    monkeypatch.setattr(security.jwt, "decode", lambda *args, **kwargs: {"sub": "abc"})
    with pytest.raises(HTTPException) as exc:
        security.get_current_user(token="token", db=DummySession())
    assert exc.value.status_code == 401


def test_get_current_user_optional_returns_none_on_bad_sub(monkeypatch):
    monkeypatch.setattr(security.jwt, "decode", lambda *args, **kwargs: {"sub": "abc"})
    assert security.get_current_user_optional(token="token", db=DummySession()) is None


def test_email_verification_token_roundtrip():
    token = security.create_email_verification_token(42, expires_hours=1)
    assert security.verify_email_verification_token(token) == 42


def test_email_verification_token_rejects_wrong_type():
    token = security.create_password_reset_token(42, expires_minutes=30)
    assert security.verify_email_verification_token(token) is None
