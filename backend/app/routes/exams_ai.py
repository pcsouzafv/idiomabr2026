import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.exam_ai import (
    ExamAIGenerateRequest,
    ExamAIGenerateResponse,
    ExamAIAnalyzeRequest,
    ExamAIAnalyzeResponse,
    ExamAIQuestionFeedback,
)
from app.services.ai_teacher import ai_teacher_service
from app.services.rag_service import rag_service


router = APIRouter(prefix="/api/exams", tags=["exams"])


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None

    # Common case: ```json ... ```
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            chunk = part.strip()
            if chunk.startswith("json"):
                chunk = chunk[4:].strip()
            if chunk.startswith("{") and chunk.endswith("}"):
                try:
                    return json.loads(chunk)
                except Exception:
                    pass

    # Fallback: first { ... last }
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            return None

    return None


def _as_list_of_str(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(v) for v in value if v is not None]


def _exam_score_hint(exam: str) -> str:
    e = (exam or "").lower().strip()
    if e == "ielts":
        return "IELTS band score (1-9)"
    if e == "toefl":
        return "TOEFL iBT score (0-120)"
    if e == "toeic":
        return "TOEIC score (10-990)"
    if e == "cambridge":
        return "Cambridge (B2 First / C1 Advanced / C2 Proficiency) style feedback"
    return "estimated score"


@router.post("/ai/generate", response_model=ExamAIGenerateResponse)
async def generate_mini_mock(
    request: ExamAIGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Gera um mini-simulado (sem persistência no banco; apenas cache de IA)."""

    user_stats = await rag_service._get_user_stats(db, current_user.id)
    level = request.level or user_stats.get("estimated_level") or "A1"

    system = (
        "You are an exam preparation coach for Brazilian Portuguese speakers learning English. "
        "You must output ONLY valid JSON (no markdown, no explanations)."
    )

    user = {
        "task": "generate_mini_mock",
        "exam": request.exam,
        "skill": request.skill,
        "level": level,
        "num_questions": request.num_questions,
        "requirements": {
            "language": "prompts in English",
            "answers": "do NOT include answer keys",
            "ids": "each question must have a stable id string",
            "types": ["multiple_choice", "short_answer", "essay", "speaking"],
        },
        "output_schema": {
            "instructions": "string",
            "questions": [
                {
                    "id": "string",
                    "type": "string",
                    "prompt": "string",
                    "options": "optional array of strings (only for multiple_choice)",
                }
            ],
        },
    }

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]

    try:
        ai = await ai_teacher_service.get_ai_response_messages(
            messages,
            db=db,
            cache_operation="exams.ai.generate",
            cache_scope=f"user:{current_user.id}",
        )
        raw = (ai.get("response") or "").strip()
        parsed = _extract_json_object(raw)

        questions_raw: Any = None
        if isinstance(parsed, dict):
            questions_raw = parsed.get("questions")
        questions = questions_raw if isinstance(questions_raw, list) else []

        if not isinstance(parsed, dict) or not questions:
            # Fallback: return raw as instructions so UI can show something.
            return ExamAIGenerateResponse(
                exam=request.exam,
                skill=request.skill,
                level=level,
                instructions=raw or "Não foi possível gerar o mini-simulado no momento.",
                questions=[],
                model_used=ai.get("model_used"),
                cached=ai.get("cached"),
            )

        return ExamAIGenerateResponse(
            exam=request.exam,
            skill=request.skill,
            level=level,
            instructions=(parsed.get("instructions") if isinstance(parsed.get("instructions"), str) else None),
            questions=questions,
            model_used=ai.get("model_used"),
            cached=ai.get("cached"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar simulado: {str(e)}")


@router.post("/ai/analyze", response_model=ExamAIAnalyzeResponse)
async def analyze_mini_mock(
    request: ExamAIAnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Analisa respostas do mini-simulado (sem persistência; apenas cache de IA)."""

    user_stats = await rag_service._get_user_stats(db, current_user.id)
    level = request.level or user_stats.get("estimated_level") or "A1"

    system = (
        "You are an exam preparation coach. Output ONLY valid JSON (no markdown). "
        "Be constructive, actionable, and motivational."
    )

    score_hint = _exam_score_hint(request.exam)

    user_payload = {
        "task": "analyze_mini_mock",
        "exam": request.exam,
        "skill": request.skill,
        "level": level,
        "score_hint": score_hint,
        "questions": [q.model_dump() for q in request.questions],
        "answers": [a.model_dump() for a in request.answers],
        "output_schema": {
            "estimated_score": "string (optional)",
            "overall_feedback": "string",
            "strengths": "array of strings",
            "weaknesses": "array of strings",
            "study_plan": "array of strings (5-8 bullets)",
            "motivation": "string (short)",
            "per_question": [
                {"id": "string", "feedback": "string", "improved_answer": "optional string"}
            ],
        },
    }

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]

    try:
        ai = await ai_teacher_service.get_ai_response_messages(
            messages,
            db=db,
            cache_operation="exams.ai.analyze",
            cache_scope=f"user:{current_user.id}",
        )

        raw = (ai.get("response") or "").strip()
        parsed = _extract_json_object(raw) or {}

        # If parsing fails, still return something useful to the UI.
        overall = parsed.get("overall_feedback") if isinstance(parsed, dict) else None
        if not overall:
            overall = raw or "Não foi possível analisar no momento."

        per_q: List[ExamAIQuestionFeedback] = []
        per_question_raw: Any = parsed.get("per_question") if isinstance(parsed, dict) else None
        if isinstance(per_question_raw, list):
            for item in per_question_raw:
                if not isinstance(item, dict) or "id" not in item or "feedback" not in item:
                    continue
                per_q.append(
                    ExamAIQuestionFeedback(
                        id=str(item.get("id")),
                        feedback=str(item.get("feedback")),
                        improved_answer=(item.get("improved_answer") if item.get("improved_answer") is None else str(item.get("improved_answer"))),
                    )
                )

        strengths = _as_list_of_str(parsed.get("strengths") if isinstance(parsed, dict) else None)
        weaknesses = _as_list_of_str(parsed.get("weaknesses") if isinstance(parsed, dict) else None)
        study_plan = _as_list_of_str(parsed.get("study_plan") if isinstance(parsed, dict) else None)

        return ExamAIAnalyzeResponse(
            exam=request.exam,
            skill=request.skill,
            estimated_score=(parsed.get("estimated_score") if isinstance(parsed, dict) else None),
            overall_feedback=overall,
            strengths=strengths,
            weaknesses=weaknesses,
            study_plan=study_plan,
            motivation=(parsed.get("motivation") if isinstance(parsed, dict) else None),
            per_question=per_q,
            model_used=ai.get("model_used"),
            cached=ai.get("cached"),
            raw_response=(None if isinstance(parsed, dict) and parsed else raw),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao analisar simulado: {str(e)}")
