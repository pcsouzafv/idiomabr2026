from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.text_study import StudyText, StudyTextAttempt
from app.schemas.text_study import (
    StudyTextListItem,
    StudyTextDetail,
    StudyTextAttemptCreate,
    StudyTextAttemptResponse,
)
from app.services.ai_teacher import ai_teacher_service

router = APIRouter(prefix="/api/texts", tags=["texts"])


@router.get("/", response_model=List[StudyTextListItem])
def list_texts(
    level: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(StudyText)
    if level:
        query = query.filter(StudyText.level == level)

    texts = query.order_by(StudyText.id.desc()).limit(limit).all()

    items: List[StudyTextListItem] = []
    for t in texts:
        word_count = len((t.content_en or "").split())
        items.append(
            StudyTextListItem(
                id=t.id,
                title=t.title,
                level=t.level,
                word_count=word_count,
            )
        )
    return items


@router.get("/{text_id}", response_model=StudyTextDetail)
def get_text(
    text_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    text = db.query(StudyText).filter(StudyText.id == text_id).first()
    if not text:
        raise HTTPException(status_code=404, detail="Texto não encontrado")

    return StudyTextDetail(
        id=text.id,
        title=text.title,
        level=text.level,
        content_en=text.content_en,
        content_pt=text.content_pt,
        audio_url=getattr(text, "audio_url", None),
        tags=text.tags,
    )


@router.post("/{text_id}/attempt", response_model=StudyTextAttemptResponse)
async def submit_attempt(
    text_id: int,
    payload: StudyTextAttemptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    text = db.query(StudyText).filter(StudyText.id == text_id).first()
    if not text:
        raise HTTPException(status_code=404, detail="Texto não encontrado")

    prompt = f"""Você é Sarah, professora de inglês. Vou te dar um texto para leitura (em inglês) e uma resposta do aluno.

Nível do aluno: {text.level}

TEXTO (inglês):
{text.content_en}

TAREFA: {payload.task}
RESPOSTA DO ALUNO:
{payload.user_text}

Avalie e responda em português:
1) Correções (se houver), com explicação breve
2) Sugestões para melhorar (vocabulário/gramática/clareza)
3) Nota de 0 a 10
4) Um exercício rápido de fixação (1 pergunta)
"""

    ai = await ai_teacher_service.get_ai_response(
        user_message=prompt,
        context=None,
        conversation_history=None,
        db=db,
        cache_operation=f"texts.attempt:{payload.task}",
        cache_scope=f"user:{current_user.id}",
    )

    attempt = StudyTextAttempt(
        user_id=current_user.id,
        text_id=text.id,
        task=payload.task,
        user_text=payload.user_text,
        ai_feedback=ai.get("response"),
        ai_json=None,
        model_used=ai.get("model_used"),
    )

    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return StudyTextAttemptResponse(
        id=attempt.id,
        text_id=attempt.text_id,
        task=attempt.task,
        user_text=attempt.user_text,
        ai_feedback=attempt.ai_feedback,
        model_used=attempt.model_used,
    )
