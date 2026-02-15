from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models.ai_usage import AIUsageLog

_AI_USAGE_TABLE_EXISTS: Optional[bool] = None


def _to_int(value: Any, default: int = 0) -> int:
    try:
        parsed = int(value)
        return parsed if parsed >= 0 else default
    except (TypeError, ValueError):
        return default


def parse_usage_tokens(usage: Any) -> Dict[str, int]:
    if usage is None:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    # SDK v1 objects usually expose attributes; some providers return dict-like payloads.
    prompt_tokens = _to_int(getattr(usage, "prompt_tokens", None))
    completion_tokens = _to_int(getattr(usage, "completion_tokens", None))
    total_tokens = _to_int(getattr(usage, "total_tokens", None))

    if isinstance(usage, dict):
        prompt_tokens = _to_int(usage.get("prompt_tokens"), prompt_tokens)
        completion_tokens = _to_int(usage.get("completion_tokens"), completion_tokens)
        total_tokens = _to_int(usage.get("total_tokens"), total_tokens)

    # Some providers use input/output naming.
    if prompt_tokens == 0:
        prompt_tokens = _to_int(getattr(usage, "input_tokens", None), prompt_tokens)
    if completion_tokens == 0:
        completion_tokens = _to_int(getattr(usage, "output_tokens", None), completion_tokens)
    if isinstance(usage, dict):
        if prompt_tokens == 0:
            prompt_tokens = _to_int(usage.get("input_tokens"), prompt_tokens)
        if completion_tokens == 0:
            completion_tokens = _to_int(usage.get("output_tokens"), completion_tokens)

    if total_tokens == 0:
        total_tokens = prompt_tokens + completion_tokens

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def parse_model_name(response: Any, fallback_model: Optional[str] = None) -> Optional[str]:
    model = getattr(response, "model", None)
    if isinstance(model, str) and model.strip():
        return model.strip()

    if isinstance(response, dict):
        raw = response.get("model")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()

    if fallback_model and fallback_model.strip():
        return fallback_model.strip()

    return None


def track_ai_usage(
    db: Optional[Session],
    *,
    user_id: Optional[int],
    provider: str,
    operation: str,
    model: Optional[str],
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    cached: bool = False,
    meta_json: Optional[Dict[str, Any]] = None,
) -> None:
    if db is None:
        return

    global _AI_USAGE_TABLE_EXISTS
    if _AI_USAGE_TABLE_EXISTS is not True:
        try:
            table_exists = bool(inspect(db.get_bind()).has_table(AIUsageLog.__tablename__))
        except Exception:
            table_exists = False
        if not table_exists:
            return
        _AI_USAGE_TABLE_EXISTS = True

    entry = AIUsageLog(
        user_id=user_id,
        provider=(provider or "unknown").strip().lower(),
        model=(model or None),
        operation=(operation or "unknown").strip(),
        prompt_tokens=max(0, int(prompt_tokens)),
        completion_tokens=max(0, int(completion_tokens)),
        total_tokens=max(0, int(total_tokens)),
        cached=bool(cached),
        meta_json=meta_json,
    )
    db.add(entry)
