from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routes import auth


class DummyQuery:
    def __init__(self, user):
        self._user = user

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._user


class DummySession:
    def __init__(self, user):
        self._user = user

    def query(self, *args, **kwargs):
        return DummyQuery(self._user)


def _settings(*, auth_require_email_verification: bool) -> SimpleNamespace:
    return SimpleNamespace(
        environment="production",
        access_token_expire_minutes=60,
        auth_require_email_verification=auth_require_email_verification,
    )


def test_login_blocks_unverified_user_when_verification_is_required(monkeypatch):
    user = SimpleNamespace(id=1, email="student@example.com", hashed_password="hash", email_verified=False)
    monkeypatch.setattr(auth, "verify_password", lambda plain, hashed: True)
    monkeypatch.setattr(auth, "enforce_rate_limit", lambda **kwargs: None)
    monkeypatch.setattr(
        auth,
        "get_settings",
        lambda: _settings(auth_require_email_verification=True),
    )
    request = SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1"))

    with pytest.raises(HTTPException) as exc:
        auth.login(
            request=request,
            form_data=SimpleNamespace(username="student@example.com", password="secret"),
            db=DummySession(user),
        )

    assert exc.value.status_code == 403
    assert "Email nao verificado" in str(exc.value.detail)


def test_login_allows_verified_user_when_verification_is_required(monkeypatch):
    user = SimpleNamespace(id=1, email="student@example.com", hashed_password="hash", email_verified=True)
    monkeypatch.setattr(auth, "verify_password", lambda plain, hashed: True)
    monkeypatch.setattr(auth, "enforce_rate_limit", lambda **kwargs: None)
    monkeypatch.setattr(
        auth,
        "get_settings",
        lambda: _settings(auth_require_email_verification=True),
    )
    monkeypatch.setattr(auth, "create_access_token", lambda data, expires_delta: "token-abc")
    request = SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1"))

    result = auth.login(
        request=request,
        form_data=SimpleNamespace(username="student@example.com", password="secret"),
        db=DummySession(user),
    )

    assert result["access_token"] == "token-abc"
    assert result["token_type"] == "bearer"


def test_login_allows_unverified_user_when_verification_is_disabled(monkeypatch):
    user = SimpleNamespace(id=1, email="student@example.com", hashed_password="hash", email_verified=False)
    monkeypatch.setattr(auth, "verify_password", lambda plain, hashed: True)
    monkeypatch.setattr(auth, "enforce_rate_limit", lambda **kwargs: None)
    monkeypatch.setattr(
        auth,
        "get_settings",
        lambda: _settings(auth_require_email_verification=False),
    )
    monkeypatch.setattr(auth, "create_access_token", lambda data, expires_delta: "token-xyz")
    request = SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1"))

    result = auth.login(
        request=request,
        form_data=SimpleNamespace(username="student@example.com", password="secret"),
        db=DummySession(user),
    )

    assert result["access_token"] == "token-xyz"
    assert result["token_type"] == "bearer"
