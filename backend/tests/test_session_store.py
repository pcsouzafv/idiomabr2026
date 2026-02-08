from app.services.session_store import InMemorySessionStore


def test_inmemory_store_expires_immediately():
    store = InMemorySessionStore()
    store.set("k", {"value": 1}, ttl_seconds=0)
    assert store.get("k") is None
