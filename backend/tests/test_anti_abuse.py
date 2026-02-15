from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services import anti_abuse
from app.services.session_store import InMemorySessionStore


def _request(headers: dict[str, str] | None = None, host: str = "127.0.0.1"):
    return SimpleNamespace(headers=headers or {}, client=SimpleNamespace(host=host))


def test_get_client_ip_prefers_x_forwarded_for():
    req = _request(headers={"x-forwarded-for": "198.51.100.10, 203.0.113.7"}, host="10.0.0.1")
    assert anti_abuse.get_client_ip(req) == "198.51.100.10"


def test_get_client_ip_falls_back_to_client_host():
    req = _request(headers={}, host="10.0.0.2")
    assert anti_abuse.get_client_ip(req) == "10.0.0.2"


def test_enforce_rate_limit_blocks_after_limit(monkeypatch):
    store = InMemorySessionStore()
    monkeypatch.setattr(anti_abuse, "get_session_store", lambda: store)

    anti_abuse.enforce_rate_limit(scope="auth-register-ip", identifier="1.2.3.4", limit=2, window_seconds=60)
    anti_abuse.enforce_rate_limit(scope="auth-register-ip", identifier="1.2.3.4", limit=2, window_seconds=60)

    with pytest.raises(HTTPException) as exc:
        anti_abuse.enforce_rate_limit(scope="auth-register-ip", identifier="1.2.3.4", limit=2, window_seconds=60)

    assert exc.value.status_code == 429
