import pytest
from types import SimpleNamespace
from fastapi import HTTPException

from app.routes.conversation import _ensure_conversation_owner
from app.services.conversation_ai_service import conversation_ai_service


def _seed_conversation(conversation_id: str, user_id: int) -> None:
    conversation_ai_service._save_conversation(
        conversation_id,
        {
            "id": conversation_id,
            "user_id": user_id,
            "created_at": "2026-01-31T00:00:00Z",
            "system_prompt": "test",
            "voice_id": None,
            "messages": [],
            "status": "active",
            "lesson": None,
        },
    )


def _clear_conversation(conversation_id: str) -> None:
    conversation_ai_service._delete_conversation(conversation_id)


def test_ensure_conversation_owner_allows_owner():
    conversation_id = "conv-owner"
    _seed_conversation(conversation_id, user_id=1)
    try:
        _ensure_conversation_owner(conversation_id, SimpleNamespace(id=1))
    finally:
        _clear_conversation(conversation_id)


def test_ensure_conversation_owner_blocks_other_user():
    conversation_id = "conv-other"
    _seed_conversation(conversation_id, user_id=1)
    try:
        with pytest.raises(HTTPException) as exc:
            _ensure_conversation_owner(conversation_id, SimpleNamespace(id=2))
        assert exc.value.status_code == 404
    finally:
        _clear_conversation(conversation_id)


def test_ensure_conversation_owner_missing_conversation():
    with pytest.raises(HTTPException) as exc:
        _ensure_conversation_owner("missing", SimpleNamespace(id=1))
    assert exc.value.status_code == 404
