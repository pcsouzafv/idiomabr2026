from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.core.config import get_settings

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # type: ignore


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


class SessionStore:
    def get(self, key: str) -> Optional[dict]:
        raise NotImplementedError

    def set(self, key: str, value: dict, ttl_seconds: Optional[float] = None) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def list_keys(self, prefix: str) -> list[str]:
        raise NotImplementedError

    def cleanup(self) -> None:
        return None


class InMemorySessionStore(SessionStore):
    def __init__(self) -> None:
        self._data: dict[str, dict] = {}
        self._expires_at: dict[str, Optional[datetime]] = {}

    def _is_expired(self, key: str, now: Optional[datetime] = None) -> bool:
        now = now or datetime.now(timezone.utc)
        expires_at = self._expires_at.get(key)
        if expires_at and expires_at <= now:
            self._data.pop(key, None)
            self._expires_at.pop(key, None)
            return True
        return False

    def get(self, key: str) -> Optional[dict]:
        if self._is_expired(key):
            return None
        return self._data.get(key)

    def set(self, key: str, value: dict, ttl_seconds: Optional[float] = None) -> None:
        self._data[key] = value
        if ttl_seconds is not None:
            ttl_seconds = float(ttl_seconds)
            if ttl_seconds <= 0:
                self._expires_at[key] = datetime.now(timezone.utc)
                return
            self._expires_at[key] = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        else:
            self._expires_at[key] = None

    def delete(self, key: str) -> None:
        self._data.pop(key, None)
        self._expires_at.pop(key, None)

    def list_keys(self, prefix: str) -> list[str]:
        now = datetime.now(timezone.utc)
        keys: list[str] = []
        for key in list(self._data.keys()):
            if self._is_expired(key, now):
                continue
            if key.startswith(prefix):
                keys.append(key)
        return keys

    def cleanup(self) -> None:
        self.list_keys("")


class RedisSessionStore(SessionStore):
    def __init__(self, url: str) -> None:
        if redis is None:  # pragma: no cover
            raise RuntimeError("redis library is not available")
        self.client = redis.Redis.from_url(url, decode_responses=True)

    def get(self, key: str) -> Optional[dict]:
        raw = self.client.get(key)
        if not raw:
            return None
        try:
            value = json.loads(raw)
        except Exception:
            return None
        return value if isinstance(value, dict) else None

    def set(self, key: str, value: dict, ttl_seconds: Optional[float] = None) -> None:
        payload = json.dumps(value, default=_json_default)
        if ttl_seconds is not None:
            ttl_seconds = int(float(ttl_seconds))
            if ttl_seconds <= 0:
                self.client.set(key, payload)
                self.client.expire(key, 1)
                return
            self.client.setex(key, ttl_seconds, payload)
            return
        self.client.set(key, payload)

    def delete(self, key: str) -> None:
        self.client.delete(key)

    def list_keys(self, prefix: str) -> list[str]:
        pattern = f"{prefix}*"
        keys: list[str] = []
        cursor = 0
        while True:
            cursor, batch = self.client.scan(cursor=cursor, match=pattern, count=200)
            keys.extend(batch)
            if cursor == 0:
                break
        return keys

    def cleanup(self) -> None:
        return None


_session_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    global _session_store
    if _session_store is not None:
        return _session_store

    settings = get_settings()
    if settings.redis_enabled and settings.redis_url:
        try:
            store = RedisSessionStore(settings.redis_url)
            store.client.ping()
            _session_store = store
            return _session_store
        except Exception:
            _session_store = InMemorySessionStore()
            return _session_store

    _session_store = InMemorySessionStore()
    return _session_store
