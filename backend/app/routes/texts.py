import mimetypes
import os
import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import httpx

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.text_study import StudyText, StudyTextAttempt
from app.schemas.text_study import (
    StudyTextListItem,
    StudyTextDetail,
    StudyTextAttemptCreate,
    StudyTextAttemptResponse,
    StudyTextAudioAlignmentResponse,
    StudyTextWordTiming,
)
from app.services.ai_teacher import ai_teacher_service

router = APIRouter(prefix="/api/texts", tags=["texts"])

STATIC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "static"))


async def _read_audio_bytes_from_url(audio_url: str) -> tuple[bytes, str, str]:
    if not audio_url:
        raise HTTPException(status_code=400, detail="Texto sem áudio configurado")

    cleaned = audio_url.strip()

    if cleaned.startswith("/static/"):
        relative_path = cleaned.removeprefix("/static/")
        full_path = os.path.abspath(os.path.join(STATIC_ROOT, relative_path))

        if not (full_path == STATIC_ROOT or full_path.startswith(f"{STATIC_ROOT}{os.sep}")):
            raise HTTPException(status_code=400, detail="Caminho de áudio inválido")

        if not os.path.isfile(full_path):
            raise HTTPException(status_code=404, detail="Arquivo de áudio não encontrado")

        try:
            with open(full_path, "rb") as file:
                data = file.read()
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"Falha ao ler áudio: {str(e)}")

        filename = os.path.basename(full_path) or "audio.mp3"
        content_type = mimetypes.guess_type(filename)[0] or "audio/mpeg"
        return data, filename, content_type

    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(cleaned)
                response.raise_for_status()
        except Exception:
            raise HTTPException(status_code=502, detail="Falha ao baixar áudio remoto")

        filename = cleaned.rstrip("/").split("/")[-1] or "audio.mp3"
        content_type = response.headers.get("content-type") or mimetypes.guess_type(filename)[0] or "audio/mpeg"
        return response.content, filename, content_type

    raise HTTPException(status_code=400, detail="Formato de URL de áudio não suportado")


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


@router.get("/{text_id}/audio")
async def stream_text_audio(
    text_id: int,
    db: Session = Depends(get_db),
):
    """Retorna o áudio cadastrado para um texto, sem depender do mount /static no proxy."""

    text = db.query(StudyText).filter(StudyText.id == text_id).first()
    if not text:
        raise HTTPException(status_code=404, detail="Texto não encontrado")

    audio_url = (text.audio_url or "").strip()
    if not audio_url:
        raise HTTPException(status_code=404, detail="Texto sem áudio")

    audio_bytes, filename, content_type = await _read_audio_bytes_from_url(audio_url)

    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type=content_type or "audio/mpeg",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "public, max-age=86400",
        },
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


@router.get("/{text_id}/audio-alignment", response_model=StudyTextAudioAlignmentResponse)
async def get_text_audio_alignment(
    text_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    text = db.query(StudyText).filter(StudyText.id == text_id).first()
    if not text:
        raise HTTPException(status_code=404, detail="Texto não encontrado")

    content = (text.content_en or "").strip()
    audio_url = (text.audio_url or "").strip()
    if not content:
        return StudyTextAudioAlignmentResponse(source="none", word_timings=[])
    if not audio_url:
        return StudyTextAudioAlignmentResponse(source="none", word_timings=[])

    audio_bytes, filename, content_type = await _read_audio_bytes_from_url(audio_url)

    alignment = await ai_teacher_service.get_text_audio_word_alignment(
        text=content,
        audio_bytes=audio_bytes,
        filename=filename,
        content_type=content_type,
        db=db,
        cache_operation="texts.audio.alignment",
        cache_scope="global",
    )

    source = alignment.get("source") or "none"
    raw_timings = alignment.get("word_timings") or []
    timings: List[StudyTextWordTiming] = []

    for raw in raw_timings:
        try:
            timings.append(
                StudyTextWordTiming(
                    index=int(raw.get("index", 0)),
                    word=str(raw.get("word", "")),
                    start=float(raw.get("start", 0.0)),
                    end=float(raw.get("end", 0.0)),
                )
            )
        except (TypeError, ValueError):
            continue

    if source not in {"transcription_words", "transcription_segments"}:
        source = "none"

    return StudyTextAudioAlignmentResponse(source=source, word_timings=timings)
