import json
import re
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models.word import Word
from app.services.ai_teacher import ai_teacher_service
from app.utils.example_generator import generate_example as legacy_generate_example


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _contains_word_or_phrase(example_en: str, english: str) -> bool:
    ex = _normalize(example_en)
    term = _normalize(english)
    if not ex or not term:
        return False

    # If it's a phrase, require each token to appear.
    tokens = [t for t in re.split(r"\s+", term) if t]
    if len(tokens) <= 1:
        return term in ex

    return all(t in ex for t in tokens)


def needs_example_regeneration(word: Word) -> bool:
    """Heurística simples: exemplos vazios/curtos ou que não usam a palavra-alvo."""
    example_en = (word.example_en or "").strip()  # type: ignore[attr-defined]
    example_pt = (word.example_pt or "").strip()  # type: ignore[attr-defined]

    if len(example_en) < 8 or len(example_pt) < 8:
        return True

    # Precisa ser um exemplo em inglês que realmente usa a palavra.
    english = (word.english or "").strip()  # type: ignore[attr-defined]
    if english and not _contains_word_or_phrase(example_en, english):
        return True

    # Evitar lixo óbvio (tokens estranhos)
    if re.search(r"\bui:d\b", example_en, re.IGNORECASE) or re.search(r"\bui:d\b", example_pt, re.IGNORECASE):
        return True

    return False


def _extract_json_object(text: str) -> Optional[dict]:
    if not text:
        return None

    # 1) Try direct JSON
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass

    # 2) Try to extract a single {...} block
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None

    try:
        obj = json.loads(match.group(0))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


async def generate_word_example_ai(word: Word, db: Session) -> Tuple[Optional[str], Optional[str]]:
    """Gera exemplo via IA (com cache), retornando (example_en, example_pt)."""
    english = (word.english or "").strip()  # type: ignore[attr-defined]
    portuguese = (word.portuguese or "").strip()  # type: ignore[attr-defined]
    level = (word.level or "").strip()  # type: ignore[attr-defined]
    word_type = (getattr(word, "word_type", None) or "").strip()

    if not english:
        return (None, None)

    system_prompt = (
        "You generate bilingual example sentences for language learning. "
        "Return ONLY valid JSON (no markdown, no commentary). "
        "Schema: {\"example_en\": string, \"example_pt\": string}. "
        "Rules: example_en must be natural English and MUST include the target term exactly (case-insensitive). "
        "example_pt must be a Brazilian Portuguese translation of example_en. "
        "Keep both short (<= 14 words), no proper nouns, no slang, no quotes."
    )

    user_prompt = (
        f"Target term (English): {english}\n"
        f"Meaning (pt-BR): {portuguese}\n"
        f"CEFR level: {level or 'unknown'}\n"
        f"Word type: {word_type or 'unknown'}\n\n"
        "Return JSON only."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    ai = await ai_teacher_service.get_ai_response_messages(
        messages,
        db=db,
        cache_operation="words.example.v1",
        cache_scope=f"word:{getattr(word, 'id', 'unknown')}",
    )

    obj = _extract_json_object((ai.get("response") or "").strip())
    if not obj:
        return (None, None)

    example_en = (obj.get("example_en") or "").strip()
    example_pt = (obj.get("example_pt") or "").strip()

    if len(example_en) < 8 or len(example_pt) < 8:
        return (None, None)

    if not _contains_word_or_phrase(example_en, english):
        return (None, None)

    return (example_en, example_pt)


async def get_best_word_example(word: Word, db: Session) -> Tuple[Optional[str], Optional[str]]:
    """Tenta IA primeiro; se falhar, cai no gerador legado."""
    try:
        example_en, example_pt = await generate_word_example_ai(word, db)
        if example_en and example_pt:
            return (example_en, example_pt)
    except Exception:
        pass

    # Legacy fallback
    try:
        return legacy_generate_example((word.english or "").strip())  # type: ignore[arg-type]
    except Exception:
        return (None, None)
