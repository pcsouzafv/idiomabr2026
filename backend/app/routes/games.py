"""
Rotas para jogos interativos: Quiz, Hangman, Matching, Dictation.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, Any
from collections import Counter
import random
import uuid
import math
import json
import re
from datetime import datetime, timezone, timedelta

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import get_settings
from app.models.user import User
from app.models.word import Word
from app.models.review import Review
from app.models.progress import UserProgress
from app.models.gamification import UserStats, GameSession
from app.models.sentence import Sentence
from app.services.spaced_repetition import calculate_next_review
from app.services.achievements import check_and_unlock_achievements
from app.services.ai_teacher import ai_teacher_service
from app.services.session_store import get_session_store
from app.schemas.games import (
    QuizSessionResponse, QuizQuestion,
    QuizResultRequest, QuizResultResponse,
    HangmanState, HangmanGuessRequest, HangmanGuessResponse,
    MatchingGameResponse, MatchingCard,
    MatchingResultRequest, MatchingResultResponse,
    DictationSessionResponse, DictationWord,
    DictationResultRequest, DictationResultResponse,
    SentenceBuilderItem, SentenceBuilderSessionResponse,
    SentenceBuilderSubmitRequest, SentenceBuilderSubmitResponse,
    GrammarBuilderItem, GrammarBuilderSessionResponse,
    GrammarBuilderSubmitRequest, GrammarBuilderSubmitResponse,
    GameSessionResponse
)

router = APIRouter(prefix="/api/games", tags=["games"])

# Armazenamento temporario de sessoes (em producao usar Redis)
session_store = get_session_store()
SESSION_PREFIX = "games:"
SESSION_TTL_SECONDS = int(get_settings().session_ttl_seconds or 0) or 6 * 60 * 60


def _session_key(session_id: str) -> str:
    return f"{SESSION_PREFIX}{session_id}"


def _get_session(session_id: str) -> Optional[dict]:
    return session_store.get(_session_key(session_id))


def _save_session(session_id: str, payload: dict) -> None:
    session_store.set(_session_key(session_id), payload, ttl_seconds=SESSION_TTL_SECONDS)


def _delete_session(session_id: str) -> None:
    session_store.delete(_session_key(session_id))


def _cleanup_sessions() -> None:
    session_store.cleanup()

XP_REWARDS = {
    "quiz": {"base": 5, "correct": 10, "perfect_bonus": 50},
    "hangman": {"win": 30, "letter": 2},
    "matching": {"base": 20, "time_bonus_per_second": 1, "max_time_bonus": 100},
    "dictation": {"base": 5, "correct": 15, "perfect_bonus": 75},
    "sentence_builder": {"base": 10, "correct": 15, "perfect_bonus": 50},
    "grammar_builder": {"base": 10, "correct": 15, "perfect_bonus": 50}
}


def _normalize_sentence(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _pick_sentence_from_word(word: Word) -> tuple[str, str]:
    """Returns (sentence_en, sentence_pt)."""

    sentence_en = (word.example_en or "").strip()
    sentence_pt = (word.example_pt or word.portuguese or "").strip()

    # Prefer example_sentences JSON if present
    raw = (word.example_sentences or "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list) and parsed:
                candidates = [x for x in parsed if isinstance(x, dict) and x.get("en")]
                if candidates:
                    chosen = random.choice(candidates)
                    sentence_en = str(chosen.get("en") or sentence_en).strip()
                    if chosen.get("pt"):
                        sentence_pt = str(chosen.get("pt") or sentence_pt).strip()
        except Exception:
            pass

    sentence_pt = _sanitize_sentence_pt(sentence_pt)
    if not sentence_pt:
        sentence_pt = (word.portuguese or "").strip()

    return sentence_en, sentence_pt


def _tokenize_sentence_builder(text: str) -> list[str]:
    return [t for t in (text or "").strip().split() if t.strip()]


def _max_tokens_for_level(level: Optional[str]) -> int:
    # Conservative limits to keep sentences proportional.
    # A1..C2: increasingly longer sentences.
    mapping = {
        "A1": 6,
        "A2": 10,
        "B1": 14,
        "B2": 18,
        "C1": 24,
        "C2": 30,
    }
    if not level:
        return mapping["A1"]
    return mapping.get(level.upper(), 12)


def _pick_focus_word(tokens: list[str]) -> str:
    # Prefer an alphabetic token to show as "palavra foco".
    stopwords = {
        "a", "an", "the", "to", "of", "and", "or", "but", "for", "with",
        "at", "in", "on", "from", "by", "is", "are", "was", "were", "be",
        "been", "being", "do", "does", "did", "have", "has", "had", "i",
        "you", "he", "she", "it", "we", "they", "me", "him", "her", "them",
        "my", "your", "his", "her", "its", "our", "their", "this", "that",
        "these", "those", "there", "here", "as", "so", "if", "then", "when",
    }
    for t in tokens:
        clean = "".join([c for c in t if c.isalpha()]).lower()
        if len(clean) >= 3 and clean not in stopwords:
            return clean
    # Fallback: use the longest alphabetic token
    longest = ""
    for t in tokens:
        clean = "".join([c for c in t if c.isalpha()]).lower()
        if len(clean) > len(longest):
            longest = clean
    return longest


def _sanitize_sentence_pt(text: str) -> str:
    if not text:
        return ""
    normalized = " ".join(text.strip().split())
    lowered = normalized.lower()

    if re.search(r"\b(ao|na|no|de)\s+(o|a|os|as)\b", lowered):
        return ""

    replacements = {
        "A mercado": "O mercado",
        "A posto": "O posto",
        "A posto de gasolina": "O posto de gasolina",
        "A shopping": "O shopping",
    }
    for src, dst in replacements.items():
        if normalized.startswith(src):
            normalized = normalized.replace(src, dst, 1)
            lowered = normalized.lower()
            break

    if normalized.startswith("A ") and "está" in lowered:
        fem_map = {
            "caro": "cara",
            "barato": "barata",
            "limpo": "limpa",
            "cheio": "cheia",
            "tranquilo": "tranquila",
            "movimentado": "movimentada",
        }
        for masc, fem in fem_map.items():
            normalized = re.sub(rf"\bestá\s+{masc}\b", f"está {fem}", normalized, flags=re.IGNORECASE)

    normalized = re.sub(
        r"\bEu\s+passar\s+pano\b",
        "Eu passo pano",
        normalized,
        flags=re.IGNORECASE,
    )

    normalized = re.sub(
        r"\bEu\s+lavar\b",
        "Eu lavo",
        normalized,
        flags=re.IGNORECASE,
    )

    normalized = normalized.replace("depois do um lanche tarde", "depois de um lanche da tarde")

    normalized = normalized.replace(" na domingo", " no domingo")
    normalized = normalized.replace(" na sábado", " no sábado")

    return normalized


def _normalize_grammar_token(token: str) -> str:
    return re.sub(r"[^a-zA-Z']", "", token).strip().lower()


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(value.strip())
    return result


def _format_token_list(values: list[str], max_items: int = 6) -> str:
    if not values:
        return "-"
    unique = _dedupe_keep_order(values)
    if not unique:
        return "-"
    if len(unique) <= max_items:
        return ", ".join(unique)
    return ", ".join(unique[:max_items]) + ", ..."


def _build_grammar_error_feedback(
    *,
    expected_sentence: str,
    user_sentence: str,
    expected_tokens: list[str],
    user_tokens: list[str],
    tip: str,
    base_explanation: str,
    tense: Optional[str],
    grammar_points: list[str],
) -> dict[str, Any]:
    expected_clean = [t.strip() for t in expected_tokens if str(t).strip()]
    user_clean = [t.strip() for t in user_tokens if str(t).strip()]

    expected_norm = [_normalize_grammar_token(t) for t in expected_clean if _normalize_grammar_token(t)]
    user_norm = [_normalize_grammar_token(t) for t in user_clean if _normalize_grammar_token(t)]

    expected_counter = Counter(expected_norm)
    user_counter = Counter(user_norm)

    missing_tokens: list[str] = []
    for token, count in expected_counter.items():
        diff = count - user_counter.get(token, 0)
        if diff > 0:
            missing_tokens.extend([token] * diff)

    extra_tokens: list[str] = []
    for token, count in user_counter.items():
        diff = count - expected_counter.get(token, 0)
        if diff > 0:
            extra_tokens.extend([token] * diff)

    first_diff_index: Optional[int] = None
    compared = min(len(expected_norm), len(user_norm))
    for idx in range(compared):
        if expected_norm[idx] != user_norm[idx]:
            first_diff_index = idx
            break
    if first_diff_index is None and len(expected_norm) != len(user_norm):
        first_diff_index = compared

    first_mismatch = ""
    if first_diff_index is not None:
        expected_at = expected_clean[first_diff_index] if first_diff_index < len(expected_clean) else "(fim da frase)"
        user_at = user_clean[first_diff_index] if first_diff_index < len(user_clean) else "(fim da frase)"
        first_mismatch = (
            f"Na posição {first_diff_index + 1}, o esperado era \"{expected_at}\", "
            f"mas apareceu \"{user_at}\"."
        )

    tense_hints = {
        "present": "No presente simples, mantenha o verbo principal na forma base (ou com -s na 3ª pessoa).",
        "past": "No passado, confirme se o verbo principal está no passado (ou se há auxiliar correto).",
        "future": "No futuro, use a estrutura com auxiliar (ex.: will + verbo base) sem alterar o verbo principal.",
    }

    details: list[str] = [
        f"Frase-alvo: \"{expected_sentence}\".",
        f"Sua versão: \"{user_sentence or '(vazio)'}\".",
    ]
    if missing_tokens:
        details.append(f"Faltaram estes elementos: {_format_token_list(missing_tokens)}.")
    if extra_tokens:
        details.append(f"Você adicionou elementos extras/fora de ordem: {_format_token_list(extra_tokens)}.")
    if first_mismatch:
        details.append(first_mismatch)
    if grammar_points:
        details.append(f"Ponto gramatical foco: {_format_token_list(grammar_points)}.")
        point_hints = _grammar_point_hints(grammar_points)
        if point_hints:
            details.append(f"Regra do foco: {point_hints[0]}")
    if tip:
        details.append(f"Dica prática: {tip}")
    if base_explanation:
        details.append(f"Regra: {base_explanation}")
    tense_hint = tense_hints.get((tense or "").strip().lower())
    if tense_hint:
        details.append(tense_hint)
    details.append("Para corrigir, comece pelo sujeito, depois verbo, e só então complete com objetos/adverbios.")

    return {
        "missing_tokens": _dedupe_keep_order(missing_tokens),
        "extra_tokens": _dedupe_keep_order(extra_tokens),
        "first_mismatch": first_mismatch,
        "detailed_explanation": " ".join(details).strip(),
    }


def _parse_grammar_points(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
        if isinstance(parsed, str):
            return [parsed.strip()] if parsed.strip() else []
    except Exception:
        pass
    fallback_chunks = re.split(r"[;,|]", str(raw))
    return [p.strip() for p in fallback_chunks if p.strip()]


def _grammar_point_hints(grammar_points: list[str]) -> list[str]:
    joined = " ".join(grammar_points).lower()
    hints: list[str] = []

    marker_map: list[tuple[list[str], str]] = [
        (["present simple", "simple present"], "Present Simple: use o verbo principal na forma base para hábitos e rotinas."),
        (["present continuous", "present progressive"], "Present Continuous: use am/is/are + verbo com -ing para ações em andamento."),
        (["present perfect"], "Present Perfect: use have/has + particípio para experiência ou ligação com o presente."),
        (["present perfect continuous"], "Present Perfect Continuous: use have/has been + verbo com -ing para duração até o presente."),
        (["past simple", "simple past"], "Past Simple: use verbo no passado para ação concluída em momento específico."),
        (["past continuous"], "Past Continuous: use was/were + verbo com -ing para ação em progresso no passado."),
        (["past perfect"], "Past Perfect: use had + particípio para algo que aconteceu antes de outro evento passado."),
        (["past perfect continuous"], "Past Perfect Continuous: use had been + verbo com -ing para duração antes de outro ponto no passado."),
        (["future simple", "simple future"], "Future Simple: use will + verbo base para decisão, previsão ou promessa."),
        (["going to"], "Be going to: use am/is/are going to + verbo base para planos e previsões com evidência."),
        (["future continuous"], "Future Continuous: use will be + verbo com -ing para ação em progresso no futuro."),
        (["future perfect"], "Future Perfect: use will have + particípio para algo concluído antes de um momento futuro."),
        (["future perfect continuous"], "Future Perfect Continuous: use will have been + verbo com -ing para duração até um ponto futuro."),
        (["modal"], "Modais (can, should, must etc.) vêm antes do verbo principal na forma base."),
        (["passive", "voz passiva"], "Voz passiva: mantenha be + particípio, com foco na ação e não no agente."),
        (["zero conditional"], "Zero Conditional: if + presente, presente para fatos gerais."),
        (["first conditional"], "First Conditional: if + presente, will + verbo para possibilidade futura."),
        (["second conditional"], "Second Conditional: if + passado, would + verbo para hipótese no presente."),
        (["third conditional"], "Third Conditional: if + past perfect, would have + particípio para hipótese no passado."),
    ]

    for markers, hint in marker_map:
        if any(marker in joined for marker in markers):
            hints.append(hint)

    return _dedupe_keep_order(hints)


def _extract_sentence_tense(
    grammar_points: list[str],
    sentence_en: Optional[str] = None,
) -> Optional[str]:
    joined = " ".join(grammar_points).lower()
    sentence = _normalize_sentence(sentence_en or "")
    combined = f"{joined} {sentence}".strip()

    if not combined:
        return None

    # Future tense / future-aspect structures
    if (
        "future" in combined
        or re.search(r"\b(will|shall|won't|gonna)\b", combined)
        or re.search(r"\b(am|is|are)\s+going\s+to\b", combined)
        or re.search(r"\bnext\s+\w+\b", combined)
        or re.search(r"\btomorrow\b", combined)
    ):
        return "future"

    # Present perfect / present continuous markers
    if (
        "present" in combined
        or re.search(r"\b(am|is|are)\s+\w+ing\b", sentence)
        or re.search(r"\b(has|have)\s+been\s+\w+ing\b", sentence)
        or re.search(r"\b(has|have)\s+\w+(ed|en|wn|ne|lt|t)\b", sentence)
        or re.search(r"\b(usually|always|often|every)\b", sentence)
    ):
        return "present"

    # Past forms and time markers
    if (
        "past" in combined
        or re.search(r"\b(was|were|had|did|didn't)\b", sentence)
        or re.search(r"\b(yesterday|ago|last\s+\w+)\b", sentence)
        or re.search(r"\bin\s+\d{4}\b", sentence)
        or re.search(r"\b\w+ed\b", sentence)
    ):
        return "past"

    # Plain affirmative sentences without clear markers are usually present simple.
    if sentence:
        return "present"

    return None


def _infer_grammar_points_from_sentence(
    sentence_en: str,
    tense_value: Optional[str],
) -> list[str]:
    sentence = _normalize_sentence(sentence_en or "")
    points: list[str] = []

    if re.search(r"\b(am|is|are)\s+\w+ing\b", sentence):
        points.append("present continuous")
    if re.search(r"\b(was|were)\s+\w+ing\b", sentence):
        points.append("past continuous")
    if re.search(r"\b(has|have)\s+been\s+\w+ing\b", sentence):
        points.append("present perfect continuous")
    if re.search(r"\bhad\s+been\s+\w+ing\b", sentence):
        points.append("past perfect continuous")
    if re.search(r"\b(has|have)\s+\w+(ed|en|wn|ne|lt|t)\b", sentence):
        points.append("present perfect")
    if re.search(r"\bhad\s+\w+(ed|en|wn|ne|lt|t)\b", sentence):
        points.append("past perfect")
    if re.search(r"\b(am|is|are)\s+going\s+to\b", sentence):
        points.append("be going to")
        points.append("future")
    if re.search(r"\bwill\s+be\s+\w+ing\b", sentence):
        points.append("future continuous")
    if re.search(r"\bwill\s+have\s+been\s+\w+ing\b", sentence):
        points.append("future perfect continuous")
    if re.search(r"\bwill\s+have\s+\w+(ed|en|wn|ne|lt|t)\b", sentence):
        points.append("future perfect")
    if re.search(r"\b(will|shall)\b", sentence):
        points.append("future simple")
    if re.search(r"\b(can|could|may|might|must|should|would|shall)\b", sentence):
        points.append("modal verbs")
    if re.search(r"\bif\b", sentence):
        if re.search(r"\bif\b.*\bwill\b|\bwill\b.*\bif\b", sentence):
            points.append("first conditional")
        elif re.search(r"\bif\b.*\bhad\b.*\bwould have\b", sentence):
            points.append("third conditional")
        elif re.search(r"\bif\b.*\bwould\b", sentence):
            points.append("second conditional")
        else:
            points.append("conditional sentence")
    if re.search(r"\b(be|am|is|are|was|were|been)\s+\w+(ed|en|wn|ne|lt|t)\b", sentence):
        points.append("passive voice")

    if not points and tense_value == "past":
        points.append("past simple")
    elif not points and tense_value == "future":
        points.append("future simple")
    elif not points:
        points.append("present simple")

    return _dedupe_keep_order(points)


def _cefr_levels_for_grammar_level(level: Optional[int]) -> list[str]:
    if level == 1:
        return ["A1"]
    if level == 2:
        return ["A2"]
    if level == 3:
        return ["B1", "B2", "C1", "C2"]
    return []


def _grammar_difficulty_for_level(level: Optional[str]) -> float:
    mapping = {
        "A1": 1.0,
        "A2": 2.0,
        "B1": 3.5,
        "B2": 5.0,
        "C1": 6.5,
        "C2": 8.0,
    }
    normalized = (level or "").strip().upper()
    return mapping.get(normalized, 2.0)


def _is_low_quality_grammar_sentence(sentence_en: str, sentence_pt: str) -> bool:
    normalized_en = f" {_normalize_sentence(sentence_en)} "
    normalized_pt = f" {_normalize_sentence(sentence_pt)} "

    if not normalized_en.strip() or not normalized_pt.strip():
        return True

    # Bloqueia pares semânticos incoerentes comuns em frases geradas/ruins.
    non_food_places = [
        " hardware store ",
        " bookstore ",
        " library ",
        " bank ",
        " office ",
    ]
    food_items = [
        " eggs ",
        " milk ",
        " bread ",
        " cheese ",
        " rice ",
        " beans ",
        " meat ",
        " apple ",
        " apples ",
        " banana ",
        " bananas ",
    ]
    if any(place in normalized_en for place in non_food_places) and any(item in normalized_en for item in food_items):
        return True

    food_places = [
        " supermarket ",
        " grocery store ",
        " market ",
        " bakery ",
        " butcher ",
    ]
    hardware_items = [
        " hammer ",
        " nails ",
        " screwdriver ",
        " wrench ",
        " drill ",
        " screws ",
    ]
    if any(place in normalized_en for place in food_places) and any(item in normalized_en for item in hardware_items):
        return True

    # Heurística para pt-BR também (quando o EN veio aceitável, mas PT ficou absurdo).
    pt_hardware_places = [" loja de ferragens ", " biblioteca ", " banco "]
    pt_food_items = [" ovos ", " leite ", " pao ", " carne ", " arroz ", " feijao "]
    if any(place in normalized_pt for place in pt_hardware_places) and any(item in normalized_pt for item in pt_food_items):
        return True

    return False


def _collect_grammar_candidates(
    rows: list[Sentence],
    chosen_tense: str,
) -> list[tuple[Sentence, str, list[str], Optional[str]]]:
    candidates_with_meta: list[tuple[Sentence, str, list[str], Optional[str]]] = []
    for sentence in rows:
        sentence_en = (sentence.english or "").strip()
        sentence_pt = _sanitize_sentence_pt(sentence.portuguese or "")
        if not sentence_en or not sentence_pt:
            continue
        if _is_low_quality_grammar_sentence(sentence_en, sentence_pt):
            continue

        grammar_points = _parse_grammar_points(sentence.grammar_points)
        tense_value = _extract_sentence_tense(grammar_points, sentence_en)
        if not grammar_points:
            grammar_points = _infer_grammar_points_from_sentence(sentence_en, tense_value)
        elif not _grammar_point_hints(grammar_points):
            grammar_points = _dedupe_keep_order(
                grammar_points + _infer_grammar_points_from_sentence(sentence_en, tense_value)
            )

        if chosen_tense and tense_value != chosen_tense:
            continue

        candidates_with_meta.append((sentence, sentence_pt, grammar_points, tense_value))
    return candidates_with_meta


def _map_sentence_level_to_numeric(level: Optional[str]) -> int:
    if not level:
        return 0
    normalized = level.strip().upper()
    if normalized == "A1":
        return 1
    if normalized == "A2":
        return 2
    if normalized in ("B1", "B2", "C1", "C2"):
        return 3
    return 0


def _extract_json_object(text: str) -> Optional[dict]:
    if not text:
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        return None
    return None


def _grammar_guidance_is_off_topic(text: str) -> bool:
    lowered = (text or "").lower()
    if not lowered:
        return True

    banned_markers = [
        "feminine places",
        "masculine places",
        "em português",
        "in portuguese",
        "portuguese grammar",
        "gramática do português",
        "vou ao",
        "vou à",
        "ao meio-dia",
        "masculino",
        "feminino",
        "contração ao",
        "contração à",
        "a + a",
        "a + as",
    ]
    return any(marker in lowered for marker in banned_markers)


def _build_default_grammar_tip_explanation(
    *,
    sentence_en: str,
    grammar_points: list[str],
    tense_value: Optional[str],
    fallback_tip: str,
    fallback_explanation: str,
) -> tuple[str, str]:
    normalized_sentence = " ".join((sentence_en or "").strip().split())
    lowered = f" {normalized_sentence.lower()} "
    attention_points: list[str] = []

    if " to the " in lowered:
        attention_points.append("Use `to the` antes do lugar (ex.: `to the bookstore`).")
    elif re.search(r"\bto\s+[a-z]", lowered):
        attention_points.append("Use `to` para indicar destino/movimento.")

    if re.search(r"\bon\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", lowered):
        attention_points.append("Use `on` antes de dia da semana (ex.: `on Monday`).")

    if re.search(r"\bat\s+(\d{1,2}(:\d{2})?\s*(a\.m\.|p\.m\.)|noon|midnight)\b", lowered):
        attention_points.append("Use `at` para horário específico (ex.: `at 7:00 a.m.` / `at noon`).")

    if re.search(r"\bthe\s+[a-z]", lowered):
        attention_points.append("Mantenha o artigo `the` imediatamente antes do substantivo.")

    tense_hints = {
        "present": "No presente simples em inglês, mantenha verbo principal e ordem fixa da frase.",
        "past": "No passado, confirme a forma verbal correta e mantenha os auxiliares na posição certa.",
        "future": "No futuro, use auxiliar + verbo base (ex.: `will` + verbo) sem inverter a ordem.",
    }
    grammar_hints = _grammar_point_hints(grammar_points)

    default_tip = "Em inglês, mantenha a ordem Subject + Verb + Complement."
    if attention_points:
        default_tip = attention_points[0]
    elif grammar_hints:
        default_tip = grammar_hints[0]
    if fallback_tip and not _grammar_guidance_is_off_topic(fallback_tip):
        default_tip = fallback_tip

    details: list[str] = [
        f"Frase correta em inglês: \"{normalized_sentence}\".",
        "Foque na ordem em inglês: sujeito + verbo + complementos.",
    ]
    tense_hint = tense_hints.get((tense_value or "").strip().lower())
    if tense_hint:
        details.append(tense_hint)
    if attention_points:
        details.append("Pontos de atenção: " + " ".join(attention_points[:3]))
    if grammar_points:
        details.append(f"Foco gramatical: {_format_token_list(grammar_points)}.")
    if grammar_hints:
        details.append("Guia do tempo/estrutura: " + " ".join(grammar_hints[:2]))
    if fallback_explanation and not _grammar_guidance_is_off_topic(fallback_explanation):
        details.append(f"Regra adicional: {fallback_explanation}")
    details.append("Exemplo semelhante: I go to the gym at 8:00 a.m. on Monday.")

    return default_tip, " ".join(details).strip()


async def _generate_grammar_tip_explanation(
    *,
    sentence_en: str,
    sentence_pt: str,
    grammar_points: list[str],
    level: Optional[str],
    tense_value: Optional[str],
    category: Optional[str],
    db: Session,
    sentence_id: int,
    fallback_tip: str,
    fallback_explanation: str,
) -> tuple[str, str]:
    default_tip, default_explanation = _build_default_grammar_tip_explanation(
        sentence_en=sentence_en,
        grammar_points=grammar_points,
        tense_value=tense_value,
        fallback_tip=fallback_tip,
        fallback_explanation=fallback_explanation,
    )

    system_prompt = (
        "Você é uma professora de gramática de inglês para brasileiros. "
        "O exercício é de montar frase em INGLÊS com tokens embaralhados. "
        "Explique SOMENTE gramática e ordem da frase em inglês. "
        "NÃO ensine gramática do português, gênero de substantivo, nem contrações como ao/à/às. "
        "Responda em pt-BR. "
        "Retorne JSON somente com as chaves: tip, explanation. "
        "tip: 1 frase curta (máximo 14 palavras). "
        "explanation: 3-6 frases curtas, práticas, citando onde ficam artigos/preposições/tempo."
    )

    user_prompt = (
        f"Sentence (EN): {sentence_en}\n"
        f"Sentence (PT - apenas contexto de significado): {sentence_pt}\n"
        f"CEFR level: {level or 'unknown'}\n"
        f"Tense: {tense_value or 'unknown'}\n"
        f"Grammar points: {', '.join(grammar_points) if grammar_points else 'none'}\n"
        f"Topic: {category or 'general'}\n\n"
        "Restrições:\n"
        "- Não mencionar regras de português.\n"
        "- Não falar de masculino/feminino em português.\n"
        "- Focar em ordem e conectores do inglês (ex.: to, the, on, at).\n"
        "Return JSON only."
    )

    try:
        ai = await ai_teacher_service.get_ai_response_messages_prefer_deepseek(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            db=db,
            cache_operation="grammar_builder.tip.v3",
            cache_scope=f"sentence:{sentence_id}",
        )
        data = _extract_json_object(ai.get("response", "")) or {}
        tip_value = str(data.get("tip") or "").strip()
        explanation_value = str(data.get("explanation") or "").strip()
        combined = f"{tip_value} {explanation_value}".strip()
        if tip_value and explanation_value and not _grammar_guidance_is_off_topic(combined):
            return tip_value, explanation_value
    except Exception as exc:
        print(f"[WARN] Grammar AI tip failed: {exc}")

    return default_tip, default_explanation


async def _generate_sentence_pt_ai(
    *,
    sentence_en: str,
    sentence_pt: str,
    level: Optional[str],
    category: Optional[str],
    db: Session,
    sentence_id: int,
) -> str:
    system_prompt = (
        "You are a Brazilian Portuguese teacher. Rewrite/translate the sentence "
        "into natural pt-BR for learners. Keep it short, simple, and faithful. "
        "Return JSON only with key: sentence_pt."
    )

    user_prompt = (
        f"Sentence (EN): {sentence_en}\n"
        f"Current PT (may be wrong): {sentence_pt}\n"
        f"CEFR level: {level or 'unknown'}\n"
        f"Topic: {category or 'general'}\n\n"
        "Return JSON only."
    )

    try:
        ai = await ai_teacher_service.get_ai_response_messages_prefer_deepseek(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            db=db,
            cache_operation="sentence_builder.pt.v1",
            cache_scope=f"sentence:{sentence_id}",
        )
        data = _extract_json_object(ai.get("response", "")) or {}
        candidate = str(data.get("sentence_pt") or "").strip()
        if candidate:
            return candidate
    except Exception as exc:
        print(f"[WARN] Sentence PT AI failed: {exc}")

    return sentence_pt


GRAMMAR_SEED_SENTENCES: list[dict[str, Any]] = [
    {
        "english": "I go to the bookstore on Monday",
        "portuguese": "Eu vou para a livraria na segunda-feira.",
        "level": "A1",
        "tense": "present",
        "category": "daily_life",
        "grammar_points": ["present simple", "prepositions of time", "word order"],
    },
    {
        "english": "She studies English every night",
        "portuguese": "Ela estuda ingles toda noite.",
        "level": "A1",
        "tense": "present",
        "category": "study",
        "grammar_points": ["present simple", "third person -s"],
    },
    {
        "english": "We are eating lunch now",
        "portuguese": "Nos estamos almocando agora.",
        "level": "A1",
        "tense": "present",
        "category": "daily_life",
        "grammar_points": ["present continuous"],
    },
    {
        "english": "They play soccer in the park",
        "portuguese": "Eles jogam futebol no parque.",
        "level": "A1",
        "tense": "present",
        "category": "leisure",
        "grammar_points": ["present simple", "prepositions of place"],
    },
    {
        "english": "He is watching TV at home",
        "portuguese": "Ele esta assistindo TV em casa.",
        "level": "A1",
        "tense": "present",
        "category": "daily_life",
        "grammar_points": ["present continuous"],
    },
    {
        "english": "Do you drink coffee in the morning",
        "portuguese": "Voce bebe cafe de manha?",
        "level": "A1",
        "tense": "present",
        "category": "daily_life",
        "grammar_points": ["present simple questions", "auxiliary do"],
    },
    {
        "english": "I went to the bookstore yesterday",
        "portuguese": "Eu fui para a livraria ontem.",
        "level": "A1",
        "tense": "past",
        "category": "daily_life",
        "grammar_points": ["past simple", "irregular verbs"],
    },
    {
        "english": "She studied English last night",
        "portuguese": "Ela estudou ingles ontem a noite.",
        "level": "A1",
        "tense": "past",
        "category": "study",
        "grammar_points": ["past simple"],
    },
    {
        "english": "We were eating lunch when he arrived",
        "portuguese": "Nos estavamos almocando quando ele chegou.",
        "level": "A1",
        "tense": "past",
        "category": "daily_life",
        "grammar_points": ["past continuous", "past simple"],
    },
    {
        "english": "They played soccer on Saturday",
        "portuguese": "Eles jogaram futebol no sabado.",
        "level": "A1",
        "tense": "past",
        "category": "leisure",
        "grammar_points": ["past simple", "prepositions of time"],
    },
    {
        "english": "He watched TV after dinner",
        "portuguese": "Ele assistiu TV depois do jantar.",
        "level": "A1",
        "tense": "past",
        "category": "daily_life",
        "grammar_points": ["past simple"],
    },
    {
        "english": "Did you drink coffee this morning",
        "portuguese": "Voce bebeu cafe esta manha?",
        "level": "A1",
        "tense": "past",
        "category": "daily_life",
        "grammar_points": ["past simple questions", "auxiliary did"],
    },
    {
        "english": "I will go to the bookstore tomorrow",
        "portuguese": "Eu irei para a livraria amanha.",
        "level": "A1",
        "tense": "future",
        "category": "daily_life",
        "grammar_points": ["future simple", "will"],
    },
    {
        "english": "She will study English tonight",
        "portuguese": "Ela vai estudar ingles hoje a noite.",
        "level": "A1",
        "tense": "future",
        "category": "study",
        "grammar_points": ["future simple", "will"],
    },
    {
        "english": "We are going to eat lunch at noon",
        "portuguese": "Nos vamos almocar ao meio-dia.",
        "level": "A1",
        "tense": "future",
        "category": "daily_life",
        "grammar_points": ["be going to", "future plans"],
    },
    {
        "english": "They will play soccer next Saturday",
        "portuguese": "Eles vao jogar futebol no proximo sabado.",
        "level": "A1",
        "tense": "future",
        "category": "leisure",
        "grammar_points": ["future simple", "time expressions"],
    },
    {
        "english": "He is going to watch TV later",
        "portuguese": "Ele vai assistir TV mais tarde.",
        "level": "A1",
        "tense": "future",
        "category": "daily_life",
        "grammar_points": ["be going to", "future intentions"],
    },
    {
        "english": "Will you drink coffee tomorrow morning",
        "portuguese": "Voce vai beber cafe amanha de manha?",
        "level": "A1",
        "tense": "future",
        "category": "daily_life",
        "grammar_points": ["future simple questions", "will"],
    },
    {
        "english": "I usually take the bus to work",
        "portuguese": "Eu geralmente pego o onibus para o trabalho.",
        "level": "A2",
        "tense": "present",
        "category": "work",
        "grammar_points": ["present simple", "frequency adverbs"],
    },
    {
        "english": "She is meeting her friend tomorrow",
        "portuguese": "Ela vai encontrar a amiga amanha.",
        "level": "A2",
        "tense": "present",
        "category": "conversation",
        "grammar_points": ["present continuous for future"],
    },
    {
        "english": "We have finished our homework",
        "portuguese": "Nos terminamos nossa tarefa.",
        "level": "A2",
        "tense": "present",
        "category": "study",
        "grammar_points": ["present perfect"],
    },
    {
        "english": "They have been waiting for thirty minutes",
        "portuguese": "Eles estao esperando ha trinta minutos.",
        "level": "A2",
        "tense": "present",
        "category": "daily_life",
        "grammar_points": ["present perfect continuous", "for + duration"],
    },
    {
        "english": "He does not eat meat on Fridays",
        "portuguese": "Ele nao come carne nas sextas-feiras.",
        "level": "A2",
        "tense": "present",
        "category": "daily_life",
        "grammar_points": ["present simple negative", "auxiliary does"],
    },
    {
        "english": "Have you ever visited London",
        "portuguese": "Voce ja visitou Londres alguma vez?",
        "level": "A2",
        "tense": "present",
        "category": "travel",
        "grammar_points": ["present perfect questions", "ever"],
    },
    {
        "english": "I worked at that company in 2019",
        "portuguese": "Eu trabalhei naquela empresa em 2019.",
        "level": "A2",
        "tense": "past",
        "category": "work",
        "grammar_points": ["past simple"],
    },
    {
        "english": "She was studying when I called",
        "portuguese": "Ela estava estudando quando eu liguei.",
        "level": "A2",
        "tense": "past",
        "category": "study",
        "grammar_points": ["past continuous", "past simple"],
    },
    {
        "english": "We had already left before the rain started",
        "portuguese": "Nos ja tinhamos saido antes da chuva comecar.",
        "level": "A2",
        "tense": "past",
        "category": "daily_life",
        "grammar_points": ["past perfect", "sequence of past events"],
    },
    {
        "english": "They had been traveling for hours before the flight landed",
        "portuguese": "Eles estavam viajando havia horas antes do voo pousar.",
        "level": "A2",
        "tense": "past",
        "category": "travel",
        "grammar_points": ["past perfect continuous"],
    },
    {
        "english": "He did not see the message yesterday",
        "portuguese": "Ele nao viu a mensagem ontem.",
        "level": "A2",
        "tense": "past",
        "category": "conversation",
        "grammar_points": ["past simple negative", "auxiliary did"],
    },
    {
        "english": "Had you ever tried sushi before that day",
        "portuguese": "Voce ja tinha provado sushi antes daquele dia?",
        "level": "A2",
        "tense": "past",
        "category": "daily_life",
        "grammar_points": ["past perfect questions", "ever"],
    },
    {
        "english": "I will answer your email tonight",
        "portuguese": "Eu vou responder seu email hoje a noite.",
        "level": "A2",
        "tense": "future",
        "category": "work",
        "grammar_points": ["future simple", "will"],
    },
    {
        "english": "She is going to start a new course next month",
        "portuguese": "Ela vai comecar um novo curso no proximo mes.",
        "level": "A2",
        "tense": "future",
        "category": "study",
        "grammar_points": ["be going to", "future plans"],
    },
    {
        "english": "We will be flying to Rome this time tomorrow",
        "portuguese": "Nos estaremos voando para Roma a esta hora amanha.",
        "level": "A2",
        "tense": "future",
        "category": "travel",
        "grammar_points": ["future continuous"],
    },
    {
        "english": "They will have finished the project by Friday",
        "portuguese": "Eles terao terminado o projeto ate sexta-feira.",
        "level": "A2",
        "tense": "future",
        "category": "work",
        "grammar_points": ["future perfect"],
    },
    {
        "english": "He will have been working here for five years in June",
        "portuguese": "Em junho ele tera estado trabalhando aqui por cinco anos.",
        "level": "A2",
        "tense": "future",
        "category": "work",
        "grammar_points": ["future perfect continuous"],
    },
    {
        "english": "Are you going to visit your parents this weekend",
        "portuguese": "Voce vai visitar seus pais neste fim de semana?",
        "level": "A2",
        "tense": "future",
        "category": "conversation",
        "grammar_points": ["be going to questions"],
    },
    {
        "english": "You should see a doctor soon",
        "portuguese": "Voce deveria consultar um medico em breve.",
        "level": "B1",
        "tense": "present",
        "category": "conversation",
        "grammar_points": ["modal verbs", "should"],
    },
    {
        "english": "The report is being reviewed by the manager",
        "portuguese": "O relatorio esta sendo revisado pelo gerente.",
        "level": "B1",
        "tense": "present",
        "category": "work",
        "grammar_points": ["passive voice", "present continuous passive"],
    },
    {
        "english": "If you heat ice it melts",
        "portuguese": "Se voce aquece gelo ele derrete.",
        "level": "B1",
        "tense": "present",
        "category": "study",
        "grammar_points": ["zero conditional"],
    },
    {
        "english": "I have been studying English since 2021",
        "portuguese": "Eu venho estudando ingles desde 2021.",
        "level": "B2",
        "tense": "present",
        "category": "study",
        "grammar_points": ["present perfect continuous", "since"],
    },
    {
        "english": "She has already completed the final draft",
        "portuguese": "Ela ja completou a versao final.",
        "level": "B2",
        "tense": "present",
        "category": "work",
        "grammar_points": ["present perfect", "already"],
    },
    {
        "english": "The data is updated every hour",
        "portuguese": "Os dados sao atualizados a cada hora.",
        "level": "B1",
        "tense": "present",
        "category": "work",
        "grammar_points": ["passive voice", "present simple passive"],
    },
    {
        "english": "The book was written by a famous author",
        "portuguese": "O livro foi escrito por um autor famoso.",
        "level": "B1",
        "tense": "past",
        "category": "study",
        "grammar_points": ["passive voice", "past simple passive"],
    },
    {
        "english": "If I had more time I would learn German",
        "portuguese": "Se eu tivesse mais tempo eu aprenderia alemao.",
        "level": "B1",
        "tense": "past",
        "category": "study",
        "grammar_points": ["second conditional"],
    },
    {
        "english": "If I had studied harder I would have passed the exam",
        "portuguese": "Se eu tivesse estudado mais eu teria passado na prova.",
        "level": "B2",
        "tense": "past",
        "category": "study",
        "grammar_points": ["third conditional"],
    },
    {
        "english": "He had been working there for ten years before the company closed",
        "portuguese": "Ele tinha trabalhado la por dez anos antes da empresa fechar.",
        "level": "B2",
        "tense": "past",
        "category": "work",
        "grammar_points": ["past perfect continuous"],
    },
    {
        "english": "She had left before we arrived",
        "portuguese": "Ela ja tinha saido antes de chegarmos.",
        "level": "B1",
        "tense": "past",
        "category": "daily_life",
        "grammar_points": ["past perfect"],
    },
    {
        "english": "They were discussing the contract at 8 PM",
        "portuguese": "Eles estavam discutindo o contrato as 8 da noite.",
        "level": "B1",
        "tense": "past",
        "category": "work",
        "grammar_points": ["past continuous"],
    },
    {
        "english": "I think it will rain tonight",
        "portuguese": "Eu acho que vai chover hoje a noite.",
        "level": "B1",
        "tense": "future",
        "category": "conversation",
        "grammar_points": ["future simple", "prediction"],
    },
    {
        "english": "Look at those clouds it is going to rain",
        "portuguese": "Olhe aquelas nuvens vai chover.",
        "level": "B1",
        "tense": "future",
        "category": "conversation",
        "grammar_points": ["be going to", "prediction with evidence"],
    },
    {
        "english": "This time next week I will be presenting at the conference",
        "portuguese": "Nesta hora na proxima semana eu estarei apresentando na conferencia.",
        "level": "B2",
        "tense": "future",
        "category": "work",
        "grammar_points": ["future continuous"],
    },
    {
        "english": "By next year I will have completed my degree",
        "portuguese": "Ate o proximo ano eu terei concluido meu curso.",
        "level": "B2",
        "tense": "future",
        "category": "study",
        "grammar_points": ["future perfect"],
    },
    {
        "english": "In June I will have been living here for five years",
        "portuguese": "Em junho eu terei morado aqui por cinco anos.",
        "level": "C1",
        "tense": "future",
        "category": "daily_life",
        "grammar_points": ["future perfect continuous"],
    },
    {
        "english": "If it rains tomorrow I will stay home",
        "portuguese": "Se chover amanha eu vou ficar em casa.",
        "level": "B1",
        "tense": "future",
        "category": "daily_life",
        "grammar_points": ["first conditional"],
    },
]


def _seed_grammar_sentences_if_missing(
    db: Session,
    *,
    chosen_tense: str,
    chosen_level: Optional[int],
) -> int:
    level_filter = set(_cefr_levels_for_grammar_level(chosen_level))
    relevant_seeds = [
        seed
        for seed in GRAMMAR_SEED_SENTENCES
        if (not chosen_tense or seed["tense"] == chosen_tense)
        and (not level_filter or seed["level"] in level_filter)
    ]
    if not relevant_seeds:
        return 0

    english_lowers = list({str(seed["english"]).strip().lower() for seed in relevant_seeds if str(seed["english"]).strip()})
    if not english_lowers:
        return 0

    existing_rows = (
        db.query(Sentence.english, Sentence.level)
        .filter(func.lower(Sentence.english).in_(english_lowers))
        .all()
    )
    existing_keys = {
        (
            _normalize_sentence(str(row[0])),
            str(row[1] or "").strip().upper(),
        )
        for row in existing_rows
        if row and str(row[0]).strip()
    }

    to_insert: list[Sentence] = []
    for seed in relevant_seeds:
        english = str(seed["english"]).strip()
        portuguese = str(seed["portuguese"]).strip()
        if not english or not portuguese:
            continue
        level_value = str(seed["level"]).strip().upper() or "A1"
        sentence_key = (_normalize_sentence(english), level_value)
        if sentence_key in existing_keys:
            continue
        to_insert.append(
            Sentence(
                english=english,
                portuguese=portuguese,
                level=level_value,
                category=str(seed.get("category") or "grammar").strip() or "grammar",
                grammar_points=json.dumps(seed.get("grammar_points") or [], ensure_ascii=False),
                difficulty_score=_grammar_difficulty_for_level(str(seed["level"])),
            )
        )
        existing_keys.add(sentence_key)

    if not to_insert:
        return 0

    try:
        db.add_all(to_insert)
        db.commit()
        return len(to_insert)
    except Exception as exc:
        db.rollback()
        print(f"[WARN] Failed to seed grammar sentences: {exc}")
        return 0


def calculate_level(xp: int) -> int:
    """Calcula o nível baseado no XP total."""
    # Fórmula: nível = 1 + floor(sqrt(xp / 100))
    import math
    return 1 + int(math.sqrt(xp / 100))


def xp_for_level(level: int) -> int:
    """Retorna o XP necessário para um nível."""
    return (level - 1) ** 2 * 100


def get_or_create_stats(db: Session, user_id: int) -> UserStats:
    """Obtém ou cria estatísticas do usuário."""
    stats = db.query(UserStats).filter(UserStats.user_id == user_id).first()
    if not stats:
        stats = UserStats(user_id=user_id)
        db.add(stats)
        db.commit()
        db.refresh(stats)
    return stats


def add_xp(db: Session, user_id: int, xp: int) -> UserStats:
    """Adiciona XP ao usuário e atualiza nível."""
    stats = get_or_create_stats(db, user_id)
    stats.total_xp += xp  # type: ignore[misc]
    stats.level = calculate_level(stats.total_xp)  # type: ignore[arg-type,misc]
    db.commit()
    return stats


def check_achievements(db: Session, user_id: int, _stats: UserStats) -> list:
    """Verifica e desbloqueia novas conquistas."""
    return check_and_unlock_achievements(db, user_id)


# ==================== QUIZ ====================

@router.post("/quiz/start", response_model=QuizSessionResponse)
def start_quiz(
    num_questions: int = 10,
    level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Inicia uma sessão de quiz de múltipla escolha."""
    _cleanup_sessions()
    query = db.query(Word)
    
    if level:
        query = query.filter(Word.level == level)
    
    # Pegar palavras aleatórias
    all_words = query.all()
    if len(all_words) < num_questions:
        raise HTTPException(status_code=400, detail="Não há palavras suficientes para o quiz")
    
    selected_words = random.sample(all_words, min(num_questions, len(all_words)))
    
    # Criar perguntas
    questions = []
    all_portuguese = [w.portuguese.strip() for w in all_words if w.portuguese]
    
    for word in selected_words:
        correct_pt = word.portuguese.strip()
        # Gerar opções incorretas
        wrong_options = [p for p in all_portuguese if p != correct_pt]
        # Deduplicar para evitar opções repetidas
        wrong_options = list(dict.fromkeys(wrong_options))
        wrong_options = random.sample(wrong_options, min(3, len(wrong_options)))
        
        options = wrong_options + [correct_pt]
        random.shuffle(options)
        
        questions.append(QuizQuestion(
            word_id=word.id,
            english=word.english,
            ipa=word.ipa or "",
            correct_answer=correct_pt,
            options=options
        ))
    
    questions_payload = [q.model_dump() for q in questions]
    session_id = str(uuid.uuid4())
    _save_session(
        session_id,
        {
            "type": "quiz",
            "user_id": current_user.id,
            "questions": questions_payload,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return QuizSessionResponse(
        session_id=session_id,
        questions=questions,
        total=len(questions)
    )


@router.post("/quiz/submit", response_model=QuizResultResponse)
def submit_quiz(
    request: QuizResultRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submete respostas do quiz e calcula pontuação."""
    _cleanup_sessions()
    session_id = request.session_id
    session = _get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Sessao nao pertence ao usuario")

    questions_raw = session["questions"]
    questions = [QuizQuestion(**q) if isinstance(q, dict) else q for q in questions_raw]
    
    correct = 0
    correct_words = []
    incorrect_words = []
    
    for i, answer_idx in enumerate(request.answers):
        if i < len(questions):
            question = questions[i]
            # answer_idx é o índice da opção escolhida, -1 significa timeout
            if answer_idx >= 0 and answer_idx < len(question.options):
                chosen = question.options[answer_idx]
                if chosen == question.correct_answer:
                    correct += 1
                    correct_words.append(question.english)
                else:
                    incorrect_words.append({
                        "word": question.english,
                        "your_answer": chosen,
                        "correct_answer": question.correct_answer
                    })
            else:
                # Timeout ou resposta inválida
                incorrect_words.append({
                    "word": question.english,
                    "your_answer": "(tempo esgotado)",
                    "correct_answer": question.correct_answer
                })
    
    total = len(questions)
    percentage = (correct / total) * 100 if total > 0 else 0
    
    # Calcular XP
    xp = XP_REWARDS["quiz"]["base"] + (correct * XP_REWARDS["quiz"]["correct"])
    if correct == total and total >= 5:
        xp += XP_REWARDS["quiz"]["perfect_bonus"]
    
    # Atualizar estatísticas
    stats = get_or_create_stats(db, current_user.id)
    stats.total_reviews += total  # type: ignore[misc]
    stats.correct_answers += correct  # type: ignore[misc]
    stats.games_played += 1  # type: ignore[misc]
    if correct == total:
        stats.games_won += 1  # type: ignore[misc]
    if correct > stats.best_quiz_score:
        stats.best_quiz_score = correct  # type: ignore[misc]
    
    add_xp(db, current_user.id, xp)
    
    # Salvar sessão de jogo
    game_session = GameSession(
        user_id=current_user.id,
        game_type="quiz",
        score=correct,
        max_score=total,
        time_spent=request.time_spent,
        xp_earned=xp
    )
    db.add(game_session)
    db.commit()
    
    # Verificar conquistas
    new_achievements = check_achievements(db, current_user.id, stats)
    
    # Limpar sessão
    _delete_session(session_id)
    
    return QuizResultResponse(
        score=correct,
        total=total,
        percentage=percentage,
        xp_earned=xp,
        correct_words=correct_words,
        incorrect_words=incorrect_words,
        new_achievements=new_achievements
    )


# ==================== MONTAR FRASES (Sentence Builder) ====================


@router.post("/sentence-builder/start", response_model=SentenceBuilderSessionResponse)
async def start_sentence_builder(
    num_sentences: int = 5,
    level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Inicia uma sessão de montar frases usando a tabela de sentenças do banco.

    Respeita o nível via `Sentence.level` e limita o tamanho da frase para ficar proporcional ao nível.
    """
    _cleanup_sessions()

    chosen_level = (level or "A1").upper()
    max_tokens = _max_tokens_for_level(chosen_level)

    query = db.query(Sentence).filter(
        Sentence.english.isnot(None),
        Sentence.english != "",
        Sentence.portuguese.isnot(None),
        Sentence.portuguese != "",
        Sentence.level == chosen_level,
    )

    # Priorizar sentenças com áudio quando disponível
    query = query.order_by(func.random())

    # Buscar um conjunto maior e filtrar em memória por tamanho.
    # (func.random funciona bem no Postgres; evita carregar a tabela inteira.)
    candidate_limit = max(20, num_sentences * 12)
    candidates = query.limit(candidate_limit).all()
    if len(candidates) < 1:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Não há sentenças cadastradas para o nível {chosen_level}. "
                "Cadastre mais sentenças e tente novamente."
            ),
        )

    items = []
    correct_map = {}
    for s in candidates:
        sentence_en = (s.english or "").strip()
        sentence_pt = _sanitize_sentence_pt(s.portuguese or "")
        if not sentence_pt:
            continue
        sentence_pt = await _generate_sentence_pt_ai(
            sentence_en=sentence_en,
            sentence_pt=sentence_pt,
            level=s.level,
            category=s.category,
            db=db,
            sentence_id=s.id,
        )
        tokens = _tokenize_sentence_builder(sentence_en)

        # Evitar frases muito curtas ou longas demais para o nível.
        if len(tokens) < 3 or len(tokens) > max_tokens:
            continue

        shuffled = tokens[:]
        random.shuffle(shuffled)

        item_id = str(uuid.uuid4())
        items.append(
            SentenceBuilderItem(
                item_id=item_id,
                # Reaproveita o campo existente sem quebrar o frontend
                word_id=s.id,
                focus_word=_pick_focus_word(tokens),
                sentence_en=sentence_en,
                sentence_pt=sentence_pt,
                tokens=shuffled,
                audio_url=s.audio_url,
            )
        )

        correct_map[item_id] = {
            "sentence_en": sentence_en,
            "tokens": tokens,
            "sentence_id": s.id,
            "level": chosen_level,
        }

        if len(items) >= num_sentences:
            break

    if not items:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Não foi possível gerar frases válidas para o nível {chosen_level}. "
                "Tente cadastrar frases mais curtas para este nível."
            ),
        )

    session_id = str(uuid.uuid4())
    _save_session(
        session_id,
        {
            "type": "sentence_builder",
            "user_id": current_user.id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "correct": correct_map,
        },
    )

    return SentenceBuilderSessionResponse(session_id=session_id, items=items, total=len(items))


@router.post("/sentence-builder/submit", response_model=SentenceBuilderSubmitResponse)
def submit_sentence_builder(
    request: SentenceBuilderSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submete uma sessão de montar frases e calcula pontuação."""
    _cleanup_sessions()

    session_id = request.session_id
    session = _get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    if session.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Sessao nao pertence ao usuario")
    if session.get("type") != "sentence_builder":
        raise HTTPException(status_code=400, detail="Tipo de sessao invalido")

    correct_map = session.get("correct") or {}

    total = len(correct_map)
    score = 0
    results = []

    for ans in request.answers:
        correct = correct_map.get(ans.item_id)
        if not correct:
            continue

        expected_tokens = correct.get("tokens") or []
        expected_sentence = correct.get("sentence_en") or ""

        user_sentence = " ".join([t for t in (ans.tokens or []) if str(t).strip()]).strip()
        expected_norm = _normalize_sentence(expected_sentence)
        user_norm = _normalize_sentence(user_sentence)

        is_correct = user_norm == expected_norm
        if is_correct:
            score += 1

        results.append({
            "item_id": ans.item_id,
            "correct": is_correct,
            "expected": expected_sentence,
            "your_answer": user_sentence,
            "expected_tokens": expected_tokens,
        })

    percentage = (score / total) * 100 if total > 0 else 0

    xp = XP_REWARDS["sentence_builder"]["base"] + (score * XP_REWARDS["sentence_builder"]["correct"])
    if score == total and total >= 3:
        xp += XP_REWARDS["sentence_builder"]["perfect_bonus"]

    stats = get_or_create_stats(db, current_user.id)
    stats.total_reviews += total  # type: ignore[misc]
    stats.correct_answers += score  # type: ignore[misc]
    stats.games_played += 1  # type: ignore[misc]
    if score == total:
        stats.games_won += 1  # type: ignore[misc]

    add_xp(db, current_user.id, xp)

    game_session = GameSession(
        user_id=current_user.id,
        game_type="sentence_builder",
        score=score,
        max_score=total,
        time_spent=request.time_spent,
        xp_earned=xp
    )
    db.add(game_session)
    db.commit()
    new_achievements = check_achievements(db, current_user.id, stats)

    _delete_session(session_id)

    return SentenceBuilderSubmitResponse(
        score=score,
        total=total,
        percentage=percentage,
        xp_earned=xp,
        results=results,
        new_achievements=new_achievements,
    )


# ==================== GRAMÁTICA (Grammar Builder) ====================


@router.post("/grammar-builder/start", response_model=GrammarBuilderSessionResponse)
async def start_grammar_builder(
    num_sentences: int = 8,
    tense: Optional[str] = None,
    level: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Inicia uma sessão de gramática focada em verbos e ordem da frase."""
    _cleanup_sessions()

    valid_tenses = {"present", "past", "future"}
    chosen_tense = (tense or "").strip().lower()
    if chosen_tense and chosen_tense not in valid_tenses:
        chosen_tense = ""
    chosen_level = level if level in (1, 2, 3) else None
    requested_count = max(1, min(num_sentences, 10))

    query = db.query(Sentence).filter(
        Sentence.english.isnot(None),
        Sentence.english != "",
        Sentence.portuguese.isnot(None),
        Sentence.portuguese != "",
    )

    cefr_levels = _cefr_levels_for_grammar_level(chosen_level)
    if cefr_levels:
        query = query.filter(Sentence.level.in_(cefr_levels))

    candidates = query.all()
    candidates_with_meta = _collect_grammar_candidates(candidates, chosen_tense)

    if len(candidates_with_meta) < requested_count:
        _seed_grammar_sentences_if_missing(
            db,
            chosen_tense=chosen_tense,
            chosen_level=chosen_level,
        )
        candidates = query.all()
        candidates_with_meta = _collect_grammar_candidates(candidates, chosen_tense)

    if not candidates_with_meta:
        filters_applied = []
        if chosen_tense:
            filters_applied.append(f"tempo verbal '{chosen_tense}'")
        if chosen_level:
            filters_applied.append(f"nivel '{chosen_level}'")
        detail = "Não há frases disponíveis para este filtro."
        if filters_applied:
            detail = f"Não há frases disponíveis para o filtro de {' e '.join(filters_applied)}."
        raise HTTPException(status_code=400, detail=detail)

    selected = random.sample(candidates_with_meta, min(requested_count, len(candidates_with_meta)))
    items = []
    correct_map = {}

    for s, sentence_pt, grammar_points, tense_value in selected:
        tense_value = tense_value or _extract_sentence_tense(grammar_points, s.english) or "present"
        if not grammar_points:
            grammar_points = _infer_grammar_points_from_sentence(s.english, tense_value)

        tokens = _tokenize_sentence_builder(s.english)
        shuffled = tokens[:]
        random.shuffle(shuffled)

        item_id = str(uuid.uuid4())
        tip_value = "Pontos gramaticais: " + ", ".join(grammar_points) if grammar_points else "Construa a frase com a ordem correta (SVO)."
        explanation_parts = []
        if grammar_points:
            explanation_parts.append(f"Foco: {', '.join(grammar_points)}.")
        if s.category:
            explanation_parts.append(f"Tema: {s.category}.")
        explanation_value = " ".join(explanation_parts).strip()

        tip_value, explanation_value = await _generate_grammar_tip_explanation(
            sentence_en=s.english,
            sentence_pt=sentence_pt,
            grammar_points=grammar_points,
            level=s.level,
            tense_value=tense_value,
            category=s.category,
            db=db,
            sentence_id=s.id,
            fallback_tip=tip_value,
            fallback_explanation=explanation_value,
        )
        mapped_level = _map_sentence_level_to_numeric(s.level)
        items.append(
            GrammarBuilderItem(
                item_id=item_id,
                sentence_pt=sentence_pt,
                tokens=shuffled,
                verb="",
                tip=tip_value,
                explanation=explanation_value,
                level=mapped_level,
                tense=tense_value or "",
                expected=s.english,
                audio_url=s.audio_url,
            )
        )

        correct_map[item_id] = {
            "sentence_en": s.english,
            "tokens": tokens,
            "verb": "",
            "tip": tip_value,
            "explanation": explanation_value,
            "grammar_points": grammar_points,
            "level": mapped_level,
            "tense": tense_value or "",
            "audio_url": s.audio_url,
        }

    session_id = str(uuid.uuid4())
    _save_session(
        session_id,
        {
            "type": "grammar_builder",
            "user_id": current_user.id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "correct": correct_map,
        },
    )

    return GrammarBuilderSessionResponse(session_id=session_id, items=items, total=len(items))


@router.post("/grammar-builder/submit", response_model=GrammarBuilderSubmitResponse)
def submit_grammar_builder(
    request: GrammarBuilderSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submete a sessão de gramática e registra desempenho."""
    _cleanup_sessions()

    session_id = request.session_id
    session = _get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    if session.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Sessao nao pertence ao usuario")
    if session.get("type") != "grammar_builder":
        raise HTTPException(status_code=400, detail="Tipo de sessao invalido")

    correct_map = session.get("correct") or {}

    total = len(correct_map)
    score = 0
    results = []

    for ans in request.answers:
        correct = correct_map.get(ans.item_id)
        if not correct:
            continue

        expected_tokens = correct.get("tokens") or []
        expected_sentence = correct.get("sentence_en") or ""

        user_sentence = " ".join([t for t in (ans.tokens or []) if str(t).strip()]).strip()
        expected_norm = _normalize_sentence(expected_sentence)
        user_norm = _normalize_sentence(user_sentence)

        is_correct = user_norm == expected_norm
        if is_correct:
            score += 1

        error_feedback = {}
        if not is_correct:
            error_feedback = _build_grammar_error_feedback(
                expected_sentence=expected_sentence,
                user_sentence=user_sentence,
                expected_tokens=[str(t) for t in expected_tokens if str(t).strip()],
                user_tokens=[str(t).strip() for t in (ans.tokens or []) if str(t).strip()],
                tip=str(correct.get("tip") or ""),
                base_explanation=str(correct.get("explanation") or ""),
                tense=str(correct.get("tense") or ""),
                grammar_points=[
                    str(point).strip()
                    for point in (correct.get("grammar_points") or [])
                    if str(point).strip()
                ],
            )

        results.append({
            "item_id": ans.item_id,
            "correct": is_correct,
            "expected": expected_sentence,
            "your_answer": user_sentence,
            "expected_tokens": expected_tokens,
            "tip": correct.get("tip") or "",
            "explanation": correct.get("explanation") or "",
            "verb": correct.get("verb") or "",
            "level": correct.get("level"),
            "tense": correct.get("tense"),
            "missing_tokens": error_feedback.get("missing_tokens", []),
            "extra_tokens": error_feedback.get("extra_tokens", []),
            "first_mismatch": error_feedback.get("first_mismatch", ""),
            "detailed_explanation": error_feedback.get("detailed_explanation", ""),
        })

    percentage = (score / total) * 100 if total > 0 else 0

    xp = XP_REWARDS["grammar_builder"]["base"] + (score * XP_REWARDS["grammar_builder"]["correct"])
    if score == total and total >= 3:
        xp += XP_REWARDS["grammar_builder"]["perfect_bonus"]

    stats = get_or_create_stats(db, current_user.id)
    stats.total_reviews += total  # type: ignore[misc]
    stats.correct_answers += score  # type: ignore[misc]
    stats.games_played += 1  # type: ignore[misc]
    if score == total:
        stats.games_won += 1  # type: ignore[misc]

    add_xp(db, current_user.id, xp)

    game_session = GameSession(
        user_id=current_user.id,
        game_type="grammar_builder",
        score=score,
        max_score=total,
        time_spent=request.time_spent,
        xp_earned=xp
    )
    db.add(game_session)
    db.commit()
    new_achievements = check_achievements(db, current_user.id, stats)

    _delete_session(session_id)

    return GrammarBuilderSubmitResponse(
        score=score,
        total=total,
        percentage=percentage,
        xp_earned=xp,
        results=results,
        new_achievements=new_achievements,
    )


# ==================== HANGMAN ====================

@router.post("/hangman/start", response_model=HangmanState)
def start_hangman(
    level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Inicia um novo jogo da forca."""
    _cleanup_sessions()
    import re

    query = db.query(Word)
    
    if level:
        query = query.filter(Word.level == level)
    
    # Filtrar palavras com tamanho adequado (3-12 letras)
    words = query.all()
    valid_words = []
    for w in words:
        english_clean = (w.english or "").strip()
        if 3 <= len(english_clean) <= 12 and english_clean.isalpha():
            valid_words.append(w)
    
    if not valid_words:
        raise HTTPException(status_code=400, detail="Não há palavras disponíveis")

    # Preferir palavras com mais contexto (para dicas melhores)
    def _has_context(w: Word) -> bool:
        return any([
            (w.word_type or "").strip(),
            (w.definition_pt or "").strip(),
            (w.definition_en or "").strip(),
            (w.example_en or "").strip(),
            (w.example_pt or "").strip(),
            (w.usage_notes or "").strip(),
            (w.tags or "").strip(),
            (w.ipa or "").strip(),
        ])

    enriched_words = [w for w in valid_words if _has_context(w)]
    word = random.choice(enriched_words) if enriched_words else random.choice(valid_words)
    english_clean = word.english.strip()
    session_id = str(uuid.uuid4())

    def _parse_tags(raw: Optional[str]) -> list[str]:
        if not raw:
            return []
        parts = [p.strip() for p in raw.split(",")]
        return [p for p in parts if p]

    def _mask_word_in_text(text: Optional[str], answer: str) -> Optional[str]:
        if not text:
            return None
        text_clean = " ".join(text.strip().split())
        if not text_clean:
            return None
        # Mascara a palavra exata no exemplo para não dar spoiler.
        # Ex.: "I like apples" -> "I like _____"
        pattern = re.compile(r"\\b" + re.escape(answer) + r"\\b", re.IGNORECASE)
        masked = pattern.sub("_" * len(answer), text_clean)
        return masked
    
    _save_session(
        session_id,
        {
            "type": "hangman",
            "user_id": current_user.id,
            "word": english_clean.lower(),
            "word_id": word.id,
            "guessed": [],
            "attempts_left": 6,
            "hint": word.portuguese.strip(),
            "ipa": word.ipa or "",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    display = " ".join(["_" for _ in english_clean])
    
    return HangmanState(
        session_id=session_id,
        word_id=word.id,
        display=display,
        guessed_letters=[],
        attempts_left=6,
        max_attempts=6,
        hint=word.portuguese.strip(),
        ipa=word.ipa or "",

        level=word.level,
        word_type=(word.word_type or None),
        tags=_parse_tags(word.tags),
        definition_pt=(word.definition_pt or None),
        definition_en=(word.definition_en or None),
        example_en=_mask_word_in_text(word.example_en, english_clean.lower()),
        example_pt=_mask_word_in_text(word.example_pt, english_clean.lower()),
        usage_notes=(word.usage_notes or None),
        length=len(english_clean)
    )


@router.post("/hangman/{session_id}/guess", response_model=HangmanGuessResponse)
def guess_hangman(
    session_id: str,
    request: HangmanGuessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Tenta adivinhar uma letra no jogo da forca."""
    _cleanup_sessions()
    session = _get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Sessao nao pertence ao usuario")

    letter = request.letter.lower()
    if len(letter) != 1 or not letter.isalpha():
        raise HTTPException(status_code=400, detail="Envie apenas uma letra")
    
    if letter in session["guessed"]:
        raise HTTPException(status_code=400, detail="Letra já foi tentada")
    
    session["guessed"].append(letter)
    word = session["word"]
    
    correct = letter in word
    if not correct:
        session["attempts_left"] -= 1
    
    # Construir display
    display = " ".join([c if c in session["guessed"] else "_" for c in word])
    
    # Verificar fim de jogo
    game_over = session["attempts_left"] == 0 or "_" not in display
    won = "_" not in display
    
    xp_earned = 0
    new_achievements = []
    if game_over:
        stats = get_or_create_stats(db, current_user.id)
        stats.games_played += 1  # type: ignore[misc]

        if won:
            xp_earned = XP_REWARDS["hangman"]["win"]
            stats.games_won += 1  # type: ignore[misc]
            streak = 6 - session["attempts_left"]  # Quanto menos erros, maior streak
            if streak > stats.best_hangman_streak:
                stats.best_hangman_streak = streak  # type: ignore[misc]
        
        add_xp(db, current_user.id, xp_earned)
        
        # Salvar sessão
        game_session = GameSession(
            user_id=current_user.id,
            game_type="hangman",
            score=1 if won else 0,
            max_score=1,
            xp_earned=xp_earned
        )
        db.add(game_session)
        db.commit()
        new_achievements = check_achievements(db, current_user.id, stats)
        
        _delete_session(session_id)
    
    if not game_over:
        _save_session(session_id, session)

    return HangmanGuessResponse(
        correct=correct,
        display=display,
        guessed_letters=session["guessed"] if not game_over else [],
        attempts_left=session["attempts_left"] if not game_over else 0,
        game_over=game_over,
        won=won,
        word=word if game_over else None,
        xp_earned=xp_earned,
        new_achievements=new_achievements,
    )


# ==================== MATCHING ====================

@router.post("/matching/start", response_model=MatchingGameResponse)
def start_matching(
    num_pairs: int = 6,
    level: Optional[str] = None,
    review_ratio: float = 0.8,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Inicia um jogo de combinar palavras."""
    _cleanup_sessions()
    def _norm(text: Optional[str]) -> str:
        if not text:
            return ""
        # NBSP -> espaço, trim e normaliza whitespace para evitar duplicatas "invisíveis"
        return " ".join(text.replace("\u00A0", " ").strip().split())

    def _simplify_pt(text: str) -> str:
        # Para o Matching (ensino), traduções curtas evitam ambiguidade.
        # Ex.: "implantação, deploy" -> "implantação"
        base = text
        for sep in [";", ",", "/"]:
            if sep in base:
                base = base.split(sep, 1)[0]
        if "(" in base:
            base = base.split("(", 1)[0]
        return _norm(base)

    base_query = db.query(Word).filter(Word.english.isnot(None), Word.portuguese.isnot(None))

    if level:
        base_query = base_query.filter(Word.level == level)

    # Foco no ensino:
    # 1) Prioriza palavras com revisão vencida (next_review <= agora)
    # 2) Completa com palavras novas (ainda sem UserProgress)
    # 3) Se ainda faltar, faz fallback para palavras aleatórias (mantendo regras de unicidade)
    #
    # A proporção é ajustável via query param `review_ratio`.
    # Padrão: 80% revisão / 20% novas.
    now = datetime.now(timezone.utc)

    # Sanitiza `review_ratio` para evitar erros e manter comportamento previsível.
    if review_ratio < 0:
        review_ratio = 0
    if review_ratio > 1:
        review_ratio = 1
    target_due = int(math.ceil(num_pairs * review_ratio))

    due_rows = db.query(UserProgress, Word).join(
        Word, UserProgress.word_id == Word.id
    ).filter(
        UserProgress.user_id == current_user.id,
        UserProgress.next_review <= now,
        Word.english.isnot(None),
        Word.portuguese.isnot(None),
    )
    if level:
        due_rows = due_rows.filter(Word.level == level)

    due = [
        w for _, w in due_rows.order_by(
            UserProgress.next_review,
            UserProgress.ease_factor,
            UserProgress.repetitions,
        ).limit(max(num_pairs * 30, 50)).all()
    ]

    studied_ids = db.query(UserProgress.word_id).filter(
        UserProgress.user_id == current_user.id
    ).subquery()

    # Para ensino, quando não há filtro de nível, introduz novas palavras mais fáceis primeiro.
    if level:
        new_words = base_query.filter(
            ~Word.id.in_(studied_ids)
        ).order_by(func.random()).limit(max(num_pairs * 60, 100)).all()
    else:
        new_easy = base_query.filter(
            ~Word.id.in_(studied_ids),
            Word.level.in_(["A1", "A2"])
        ).order_by(func.random()).limit(max(num_pairs * 60, 120)).all()
        new_rest = base_query.filter(
            ~Word.id.in_(studied_ids),
            ~Word.level.in_(["A1", "A2"])
        ).order_by(func.random()).limit(max(num_pairs * 60, 120)).all()
        new_words = [*new_easy, *new_rest]

    fallback = base_query.order_by(func.random()).limit(max(num_pairs * 120, 200)).all()

    picked: list[tuple[Word, str, str]] = []
    picked_due = 0
    seen_en: set[str] = set()
    seen_pt: set[str] = set()
    seen_ids: set[int] = set()

    def try_add_word(w: Word, is_due: bool) -> bool:
        nonlocal picked_due
        if w.id in seen_ids:
            return False

        en = _norm(w.english)
        pt = _simplify_pt(_norm(w.portuguese))
        if not en or not pt:
            return False
        if not en.isalpha():
            return False

        en_key = en.casefold()
        pt_key = pt.casefold()
        # Evita pares que viram “pegadinha” (ex.: cognatos iguais/mesmo texto)
        if en_key == pt_key:
            return False
        if en_key in seen_en or pt_key in seen_pt:
            return False

        seen_ids.add(w.id)
        seen_en.add(en_key)
        seen_pt.add(pt_key)
        picked.append((w, en, pt))
        if is_due:
            picked_due += 1
        return True

    # 1) Primeiro, tenta bater a meta de revisão.
    for w in due:
        if picked_due >= target_due:
            break
        try_add_word(w, is_due=True)
        if len(picked) >= num_pairs:
            break

    # 2) Completa com palavras novas.
    if len(picked) < num_pairs:
        for w in new_words:
            try_add_word(w, is_due=False)
            if len(picked) >= num_pairs:
                break

    # 3) Fallback aleatório.
    if len(picked) < num_pairs:
        for w in fallback:
            try_add_word(w, is_due=False)
            if len(picked) >= num_pairs:
                break

    if len(picked) < num_pairs:
        raise HTTPException(
            status_code=400,
            detail="Não há palavras suficientes (pares únicos) para iniciar o Matching"
        )

    cards: list[MatchingCard] = []
    for word, en, pt in picked:
        cards.append(
            MatchingCard(
                id=f"en_{word.id}",
                content=en,
                type="english",
                pair_id=word.id,
            )
        )
        cards.append(
            MatchingCard(
                id=f"pt_{word.id}",
                content=pt,
                type="portuguese",
                pair_id=word.id,
            )
        )

    random.shuffle(cards)
    
    session_id = str(uuid.uuid4())
    _save_session(
        session_id,
        {
            "type": "matching",
            "user_id": current_user.id,
            "pairs": num_pairs,
            "words": {str(w.id): {"en": en, "pt": pt} for (w, en, pt) in picked},
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return MatchingGameResponse(
        session_id=session_id,
        cards=cards,
        total_pairs=num_pairs,
        due_pairs=picked_due,
        new_pairs=(len(picked) - picked_due),
        review_ratio=review_ratio,
    )


@router.post("/matching/submit", response_model=MatchingResultResponse)
def submit_matching(
    request: MatchingResultRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submete resultado do jogo de matching."""
    _cleanup_sessions()
    session = _get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Sessao nao pertence ao usuario")

    pairs = session["pairs"]
    
    # Calcular XP (baseado em tempo e movimentos)
    xp = XP_REWARDS["matching"]["base"]
    
    # Bônus de tempo (máximo 60 segundos)
    if request.time_spent < 60:
        time_bonus = min(
            (60 - request.time_spent) * XP_REWARDS["matching"]["time_bonus_per_second"],
            XP_REWARDS["matching"]["max_time_bonus"]
        )
        xp += int(time_bonus)
    
    # Atualizar estatísticas
    stats = get_or_create_stats(db, current_user.id)
    stats.games_played += 1  # type: ignore[misc]
    if request.completed:
        stats.games_won += 1  # type: ignore[misc]

    # Integra o Matching ao aprendizado: ao completar, registra revisão e atualiza agenda (spaced repetition)
    if request.completed:
        word_ids = [int(w) for w in session.get("words", {}).keys()]

        # Heurística simples de dificuldade baseada em desempenho
        difficulty = "medium"
        if request.moves <= pairs and request.time_spent <= 60:
            difficulty = "easy"
        elif request.moves > max(pairs * 2, pairs + 6):
            difficulty = "hard"

        reviewed_at = datetime.now(timezone.utc)
        for word_id in word_ids:
            review = Review(
                user_id=current_user.id,
                word_id=word_id,
                difficulty=difficulty,
                direction="mixed",
                reviewed_at=reviewed_at,
            )
            db.add(review)

            progress = db.query(UserProgress).filter(
                UserProgress.user_id == current_user.id,
                UserProgress.word_id == word_id,
            ).first()

            if not progress:
                progress = UserProgress(
                    user_id=current_user.id,
                    word_id=word_id,
                )
                db.add(progress)
                db.flush()

            next_review, interval, ease, reps = calculate_next_review(difficulty, progress)
            progress.next_review = next_review  # type: ignore[misc]
            progress.interval = interval  # type: ignore[misc]
            progress.ease_factor = ease  # type: ignore[misc]
            progress.repetitions = reps  # type: ignore[misc]
            progress.last_review = reviewed_at  # type: ignore[misc]
            progress.total_reviews += 1  # type: ignore[misc]
            if difficulty in ["easy", "medium"]:
                progress.correct_count += 1  # type: ignore[misc]

        # Atualizar streak de estudo (mesma regra do /study/review)
        today = reviewed_at.date()
        if current_user.last_study_date:
            last_date = current_user.last_study_date.date()
            if last_date == today - timedelta(days=1):
                current_user.current_streak += 1  # type: ignore[misc]
            elif last_date != today:
                current_user.current_streak = 1  # type: ignore[misc]
        else:
            current_user.current_streak = 1  # type: ignore[misc]
        current_user.last_study_date = reviewed_at  # type: ignore[misc]

        learned_words_count = db.query(func.count(UserProgress.id)).filter(
            UserProgress.user_id == current_user.id,
            UserProgress.correct_count >= 3,
        ).scalar() or 0
        stats.words_learned = int(learned_words_count)  # type: ignore[misc]
        if current_user.current_streak > stats.longest_streak:
            stats.longest_streak = current_user.current_streak  # type: ignore[misc]

    is_best = False
    if stats.best_matching_time is None or request.time_spent < stats.best_matching_time:
        stats.best_matching_time = request.time_spent  # type: ignore[misc]
        is_best = True
    
    add_xp(db, current_user.id, xp)
    
    # Salvar sessão
    # Matching também é sessão de estudo: registra prática em stats.
    # moves = tentativas de pares; completed implica pares corretos == total_pairs.
    moves = max(0, int(request.moves or 0))
    if request.completed:
        stats.total_reviews += max(pairs, moves)
        stats.correct_answers += pairs
    else:
        stats.total_reviews += moves

    game_session = GameSession(
        user_id=current_user.id,
        game_type="matching",
        score=pairs if request.completed else 0,
        max_score=pairs,
        time_spent=request.time_spent,
        xp_earned=xp,
        completed=request.completed,
    )
    db.add(game_session)
    db.commit()
    new_achievements = check_achievements(db, current_user.id, stats)
    
    _delete_session(request.session_id)
    
    return MatchingResultResponse(
        score=pairs if request.completed else 0,
        time_spent=request.time_spent,
        moves=request.moves,
        xp_earned=xp,
        is_best_time=is_best,
        new_achievements=new_achievements,
    )


# ==================== DICTATION ====================

@router.post("/dictation/start", response_model=DictationSessionResponse)
def start_dictation(
    num_words: int = 10,
    level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Inicia uma sessão de ditado."""
    _cleanup_sessions()
    query = db.query(Word)
    
    if level:
        query = query.filter(Word.level == level)
    
    words = query.all()
    # Para o ditado, usar somente palavras que o usuário consiga digitar de forma previsível.
    # Isso evita frases (com espaço), hífens, apóstrofos etc.
    valid_words = [
        w for w in words
        if w.english and w.english.strip() and w.english.strip().isalpha()
    ]
    if len(valid_words) < num_words:
        raise HTTPException(status_code=400, detail="Não há palavras suficientes")
    
    selected = random.sample(valid_words, num_words)
    
    dictation_words = []
    word_map = {}
    
    for word in selected:
        english_clean = word.english.strip()
        dictation_words.append(DictationWord(
            word_id=word.id,
            word=english_clean,  # Palavra para text-to-speech
            ipa=word.ipa or "",
            hint=word.portuguese.strip()  # Tradução como dica
        ))
        word_map[str(word.id)] = english_clean.lower()
    
    session_id = str(uuid.uuid4())
    _save_session(
        session_id,
        {
            "type": "dictation",
            "user_id": current_user.id,
            "words": word_map,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return DictationSessionResponse(
        session_id=session_id,
        words=dictation_words,
        total=len(dictation_words)
    )


@router.post("/dictation/submit", response_model=DictationResultResponse)
def submit_dictation(
    request: DictationResultRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submete respostas do ditado."""
    _cleanup_sessions()
    session_id = request.session_id
    session = _get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Sessao nao pertence ao usuario")

    word_map = session["words"]
    
    correct = 0
    results = []
    
    for answer in request.answers:
        key = str(answer.word_id)
        if key in word_map:
            correct_word = word_map[key]
            is_correct = answer.answer.lower().strip() == correct_word
            
            if is_correct:
                correct += 1
            
            results.append({
                "word_id": answer.word_id,
                "your_answer": answer.answer,
                "correct_answer": correct_word,
                "is_correct": is_correct
            })
    
    total = len(word_map)
    percentage = (correct / total) * 100 if total > 0 else 0
    
    # Calcular XP
    xp = XP_REWARDS["dictation"]["base"] + (correct * XP_REWARDS["dictation"]["correct"])
    if correct == total and total >= 5:
        xp += XP_REWARDS["dictation"]["perfect_bonus"]
    
    # Atualizar estatísticas
    stats = get_or_create_stats(db, current_user.id)
    stats.total_reviews += total  # type: ignore[misc]
    stats.correct_answers += correct  # type: ignore[misc]
    stats.games_played += 1  # type: ignore[misc]
    if correct == total:
        stats.games_won += 1  # type: ignore[misc]
    
    add_xp(db, current_user.id, xp)
    
    # Salvar sessão
    game_session = GameSession(
        user_id=current_user.id,
        game_type="dictation",
        score=correct,
        max_score=total,
        time_spent=request.time_spent,
        xp_earned=xp
    )
    db.add(game_session)
    db.commit()
    new_achievements = check_achievements(db, current_user.id, stats)
    
    _delete_session(session_id)
    
    return DictationResultResponse(
        score=correct,
        total=total,
        percentage=percentage,
        xp_earned=xp,
        results=results,
        new_achievements=new_achievements,
    )


# ==================== HISTÓRICO ====================

@router.get("/history", response_model=list[GameSessionResponse])
def get_game_history(
    game_type: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna histórico de jogos do usuário."""
    query = db.query(GameSession).filter(GameSession.user_id == current_user.id)
    
    if game_type:
        query = query.filter(GameSession.game_type == game_type)
    
    sessions = query.order_by(GameSession.played_at.desc()).limit(limit).all()
    return sessions
