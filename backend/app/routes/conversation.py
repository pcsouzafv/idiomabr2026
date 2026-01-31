"""
Rotas para o módulo de conversação com ElevenLabs
Permite conversas full-time com IA usando text-to-speech
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import io
import uuid
from datetime import datetime, timedelta
from difflib import SequenceMatcher
import hashlib
import re

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.openai_tts_service import openai_tts_service
from app.services.conversation_ai_service import conversation_ai_service
from app.services.ai_teacher import ai_teacher_service
from app.models.conversation_lesson import ConversationLessonAttempt
from app.models.audio_attempt import AudioAttempt
from app.schemas.conversation import (
    TextToSpeechRequest,
    VoiceListResponse,
    VoiceInfo,
    ConversationCreateRequest,
    ConversationResponse,
    MessageRequest,
    MessageResponse,
    ConversationHistoryResponse,
    ConversationEndRequest,
    ConversationEndResponse,
    LessonStartRequest,
    LessonStartResponse,
    LessonMessageRequest,
    LessonMessageResponse,
    PronunciationResponse,
    LessonAttemptResponse,
    LessonAttemptDetailResponse,
    PronunciationAttemptResponse,
    LessonGenerateRequest,
    LessonGenerateResponse,
)

router = APIRouter(prefix="/api/conversation", tags=["Conversation"])

logger = logging.getLogger(__name__)

def _ensure_conversation_owner(conversation_id: str, current_user: User) -> None:
    conversation = conversation_ai_service.get_conversation(conversation_id)
    if not conversation or conversation.get("user_id") != current_user.id:
        # Avoid leaking whether the conversation exists for another user.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa\u00e7\u00e3o n\u00e3o encontrada",
        )


# ==================== TEXT-TO-SPEECH ====================

@router.post("/tts")
async def text_to_speech(
    request: TextToSpeechRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Converte texto em áudio usando OpenAI TTS
    Retorna o áudio em formato MP3
    """
    try:
        audio_data = openai_tts_service.text_to_speech(
            text=request.text,
            voice_id=request.voice_id,
            model_id=request.model_id,
            voice_settings=request.voice_settings
        )
        
        # Retorna o áudio como stream
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=speech.mp3"
            }
        )
    except ValueError as e:
        # Treat missing configuration/dependencies as a temporary unavailability (not a user input error).
        msg = str(e)
        lowered = msg.lower()
        if (
            "openai_api_key" in msg
            or "lemonfox_api_key" in msg
            or "tts requer" in lowered
            or "api key" in lowered
            or "biblioteca openai" in lowered
            or "openai" in lowered and "instalada" in lowered
        ):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=msg,
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )
    except Exception as e:
        # OpenAI SDK raises its own exceptions; we keep mapping simple and user-friendly.
        msg = str(e)
        status_code = getattr(e, "status_code", None)
        logger.warning("[TTS] OpenAI TTS error (%s): %s", type(e).__name__, msg)

        # Prefer structured status code when available (OpenAI APIStatusError etc.).
        if status_code in (401, 403) or "OPENAI_API_KEY" in msg or "LEMONFOX_API_KEY" in msg or "API key" in msg or "authentication" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="TTS requer LEMONFOX_API_KEY ou OPENAI_API_KEY válida/configurada.",
            )

        if status_code == 429 or "rate limit" in msg.lower() or "429" in msg:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="TTS (OpenAI) atingiu limite. Tente novamente em instantes.",
            )

        # Model not available in the account/environment.
        if status_code == 404 and ("model" in msg.lower() or "not found" in msg.lower()):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Modelo de TTS indisponível para esta conta. Ajuste OPENAI_TTS_MODEL ou verifique sua assinatura.",
            )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao gerar áudio via TTS (OpenAI).",
        )


@router.get("/voices", response_model=VoiceListResponse)
async def list_voices(
    current_user: User = Depends(get_current_user)
):
    """
    Lista todas as vozes disponíveis no OpenAI TTS
    """
    try:
        voices_data = openai_tts_service.list_voices()
        
        voices = [
            VoiceInfo(
                voice_id=v.get("voice_id", ""),
                name=v.get("name", ""),
                category=v.get("category"),
                description=v.get("description"),
                preview_url=v.get("preview_url"),
                labels=v.get("labels")
            )
            for v in voices_data
        ]
        
        return VoiceListResponse(voices=voices)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar vozes: {str(e)}"
        )


# ==================== CONVERSATIONAL AI ====================

@router.post("/start", response_model=ConversationResponse)
async def start_conversation(
    request: ConversationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Inicia uma nova conversação com IA
    """
    try:
        # Cria conversação usando o serviço híbrido (LLM + ElevenLabs TTS)
        result = conversation_ai_service.create_conversation(
            user_id=current_user.id,
            system_prompt=request.system_prompt,
        )

        conversation_id = result["conversation_id"]

        # Se houver mensagem inicial, adiciona ao histórico e gera resposta (sem áudio)
        if request.initial_message:
            conversation_ai_service.send_message(
                conversation_id=conversation_id,
                user_message=request.initial_message,
                generate_audio=False,
            )

        return ConversationResponse(
            conversation_id=conversation_id,
            status="active",
            created_at=datetime.utcnow(),
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao iniciar conversação: {str(e)}"
        )


@router.post("/lesson/start", response_model=LessonStartResponse)
async def start_lesson(
    request: LessonStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Inicia uma lição baseada em perguntas fixas"""
    try:
        questions = request.questions
        if request.num_questions:
            questions = questions[: max(1, int(request.num_questions))]
        result = conversation_ai_service.create_lesson(
            user_id=current_user.id,
            questions=questions,
            native_language=request.native_language,
            target_language=request.target_language,
            topic=request.topic,
        )

        return LessonStartResponse(
            conversation_id=result["conversation_id"],
            status="active",
            first_question=result["first_question"],
            total_questions=result["total_questions"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao iniciar lição: {str(e)}",
        )


@router.post("/lesson/generate", response_model=LessonGenerateResponse)
async def generate_lesson_questions(
    request: LessonGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Gera perguntas para uma lição baseada em um tema"""
    try:
        questions = conversation_ai_service.generate_lesson_questions(
            topic=request.topic,
            num_questions=request.num_questions,
        )
        return LessonGenerateResponse(questions=questions)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gerar perguntas: {str(e)}",
        )


@router.post("/{conversation_id}/message", response_model=MessageResponse)
async def send_message(
    conversation_id: str,
    request: MessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Envia uma mensagem na conversação e recebe resposta da IA com áudio
    """
    try:
        _ensure_conversation_owner(conversation_id, current_user)
        # Envia mensagem e recebe resposta (texto) e opcionalmente áudio (bytes)
        result = conversation_ai_service.send_message(
            conversation_id=conversation_id,
            user_message=request.message,
            generate_audio=False
        )
        
        message_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()

        # Se tem áudio, por enquanto não expomos URL (frontend usa /tts)
        audio_url = None
        
        return MessageResponse(
            message_id=message_id,
            conversation_id=conversation_id,
            user_message=request.message,
            ai_response=result["ai_response"],
            audio_url=audio_url,
            timestamp=timestamp
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao enviar mensagem: {str(e)}"
        )


@router.post("/lesson/{conversation_id}/message", response_model=LessonMessageResponse)
async def send_lesson_message(
    conversation_id: str,
    request: LessonMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Envia resposta do aluno na lição e recebe resposta da IA"""
    try:
        _ensure_conversation_owner(conversation_id, current_user)
        result = conversation_ai_service.send_lesson_message(
            conversation_id=conversation_id,
            user_message=request.message,
        )

        if result.get("is_final"):
            score = None
            match = re.search(r"Score\s*:\s*(\d{1,3})", result.get("ai_response") or "")
            if match:
                try:
                    score_val = int(match.group(1))
                    if 0 <= score_val <= 100:
                        score = score_val
                except Exception:
                    score = None

            conversation = conversation_ai_service.get_conversation(conversation_id) or {}
            lesson = conversation.get("lesson") or {}
            attempt = ConversationLessonAttempt(
                user_id=current_user.id,
                native_language=lesson.get("native_language") or "pt-BR",
                target_language=lesson.get("target_language") or "en",
                questions=lesson.get("questions") or [],
                answers=lesson.get("answers") or [],
                ai_feedback=result.get("ai_response") or "",
                ai_json={
                    "conversation_id": conversation_id,
                    "topic": lesson.get("topic"),
                    "num_questions": len(lesson.get("questions") or []),
                    "total_questions": result.get("total_questions"),
                    "score": score,
                },
            )
            db.add(attempt)
            db.commit()

        return LessonMessageResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao enviar mensagem da lição: {str(e)}",
        )


@router.post("/pronunciation", response_model=PronunciationResponse)
async def analyze_pronunciation(
    audio: UploadFile = File(...),
    expected_text: Optional[str] = Form(None),
    native_language: str = Form("pt-BR"),
    conversation_id: Optional[str] = Form(None),
    question_index: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Analisa pronúncia a partir de áudio do aluno (STT + feedback)."""
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Arquivo de áudio vazio")

    transcript = ""
    feedback = ""
    similarity = None
    model_used = None

    sha = hashlib.sha256(audio_bytes).hexdigest()

    try:
        transcript = await ai_teacher_service.transcribe_audio(
            audio_bytes=audio_bytes,
            filename=audio.filename or "audio.webm",
            content_type=audio.content_type or "audio/webm",
        )

        def _norm(s: str) -> str:
            return " ".join((s or "").lower().strip().split())

        if expected_text:
            similarity = int(round(SequenceMatcher(None, _norm(expected_text), _norm(transcript)).ratio() * 100))

        prompt = f"""Você é um professor de inglês. O aluno gravou um áudio para praticar pronúncia.

TEXTO-ALVO (o que o aluno queria dizer):
{expected_text or "(não informado)"}

TRANSCRIÇÃO DO ÁUDIO (STT):
{transcript}

Responda em {native_language} com:
1) Se parece correto ou não
2) Onde melhorar a pronúncia
3) Dicas práticas
4) Uma versão 'bem falada' para repetir
"""

        ai = await ai_teacher_service.get_ai_response(
            user_message=prompt,
            context=None,
            conversation_history=None,
            db=db,
            cache_operation="conversation.ai.pronunciation",
            cache_scope=f"user:{current_user.id}",
        )
        feedback = ai.get("response") or ""
        model_used = ai.get("model_used")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao analisar áudio: {str(e)}")

    attempt = AudioAttempt(
        user_id=current_user.id,
        sentence_id=None,
        filename=audio.filename,
        content_type=audio.content_type,
        audio_sha256=sha,
        audio_bytes=audio_bytes,
        expected_text=expected_text,
        transcript=transcript,
        similarity=similarity,
        ai_feedback=feedback,
        ai_json={
            "conversation_id": conversation_id,
            "question_index": question_index,
        },
        model_used=model_used,
    )
    db.add(attempt)
    db.commit()

    return PronunciationResponse(
        transcript=transcript,
        similarity=similarity,
        feedback=feedback,
    )


@router.post("/stt")
async def transcribe_conversation_audio(
    audio: UploadFile = File(...),
    language: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Transcreve áudio do usuário para texto (STT) usando OpenAI Whisper."""
    try:
        audio_bytes = await audio.read()
        logger.info(
            "[STT] file=%s content_type=%s bytes=%s",
            audio.filename,
            audio.content_type,
            len(audio_bytes) if audio_bytes else 0,
        )
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Arquivo de áudio vazio")

        transcript = await ai_teacher_service.transcribe_audio(
            audio_bytes,
            filename=audio.filename or "audio.webm",
            content_type=audio.content_type or "audio/webm",
            language=language,
            prompt=prompt,
        )

        return {"transcript": transcript}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao transcrever áudio: {str(e)}",
        )


@router.get("/{conversation_id}/history", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtém o histórico completo de uma conversação
    """
    try:
        _ensure_conversation_owner(conversation_id, current_user)
        messages = conversation_ai_service.get_conversation_history(conversation_id)
        
        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            messages=messages,
            total_messages=len(messages)
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter histórico: {str(e)}"
        )


@router.post("/{conversation_id}/end", response_model=ConversationEndResponse)
async def end_conversation(
    conversation_id: str,
    request: Optional[ConversationEndRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Encerra uma conversação
    """
    try:
        _ensure_conversation_owner(conversation_id, current_user)
        summary = conversation_ai_service.end_conversation(conversation_id)
        
        return ConversationEndResponse(
            conversation_id=conversation_id,
            status="ended",
            total_messages=summary["message_count"],
            duration_seconds=int(summary["duration_seconds"])
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao encerrar conversação: {str(e)}"
        )


@router.get("/active/list")
async def list_active_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lista todas as conversações ativas do usuário atual
    """
    try:
        user_conversations = conversation_ai_service.list_active_conversations(
            user_id=current_user.id
        )
        
        return {
            "active_conversations": user_conversations,
            "total": len(user_conversations)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar conversações: {str(e)}"
        )


@router.get("/lesson/attempts", response_model=list[LessonAttemptResponse])
async def list_lesson_attempts(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista lições concluídas do usuário"""
    try:
        limit = max(1, min(limit, 50))
        cutoff = datetime.utcnow() - timedelta(days=15)
        (
            db.query(ConversationLessonAttempt)
            .filter(
                ConversationLessonAttempt.user_id == current_user.id,
                ConversationLessonAttempt.created_at < cutoff,
            )
            .delete(synchronize_session=False)
        )
        (
            db.query(AudioAttempt)
            .filter(
                AudioAttempt.user_id == current_user.id,
                AudioAttempt.created_at < cutoff,
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        attempts = (
            db.query(ConversationLessonAttempt)
            .filter(ConversationLessonAttempt.user_id == current_user.id)
            .order_by(ConversationLessonAttempt.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            LessonAttemptResponse(
                id=a.id,
                created_at=a.created_at,
                questions=a.questions or [],
                answers=a.answers or [],
                ai_feedback=a.ai_feedback,
                topic=a.ai_json.get("topic") if isinstance(a.ai_json, dict) else None,
                num_questions=a.ai_json.get("num_questions") if isinstance(a.ai_json, dict) else None,
                score=a.ai_json.get("score") if isinstance(a.ai_json, dict) else None,
            )
            for a in attempts
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar lições: {str(e)}",
        )


@router.get("/lesson/attempts/{attempt_id}", response_model=LessonAttemptDetailResponse)
async def get_lesson_attempt_details(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detalhes de uma lição com tentativas de pronúncia"""
    try:
        attempt = (
            db.query(ConversationLessonAttempt)
            .filter(
                ConversationLessonAttempt.id == attempt_id,
                ConversationLessonAttempt.user_id == current_user.id,
            )
            .first()
        )
        if not attempt:
            raise HTTPException(status_code=404, detail="Lição não encontrada")

        conversation_id = None
        if isinstance(attempt.ai_json, dict):
            conversation_id = attempt.ai_json.get("conversation_id")

        pronunciations = []
        if conversation_id:
            items = (
                db.query(AudioAttempt)
                .filter(
                    AudioAttempt.user_id == current_user.id,
                    AudioAttempt.ai_json["conversation_id"].astext == str(conversation_id),
                )
                .order_by(AudioAttempt.created_at.desc())
                .all()
            )

            for item in items:
                q_index = None
                if isinstance(item.ai_json, dict):
                    q_index = item.ai_json.get("question_index")
                pronunciations.append(
                    PronunciationAttemptResponse(
                        question_index=q_index,
                        transcript=item.transcript or "",
                        similarity=item.similarity,
                        feedback=item.ai_feedback or "",
                        created_at=item.created_at,
                    )
                )

        attempt_response = LessonAttemptResponse(
            id=attempt.id,
            created_at=attempt.created_at,
            questions=attempt.questions or [],
            answers=attempt.answers or [],
            ai_feedback=attempt.ai_feedback,
            topic=attempt.ai_json.get("topic") if isinstance(attempt.ai_json, dict) else None,
            num_questions=attempt.ai_json.get("num_questions") if isinstance(attempt.ai_json, dict) else None,
            score=attempt.ai_json.get("score") if isinstance(attempt.ai_json, dict) else None,
        )

        return LessonAttemptDetailResponse(
            attempt=attempt_response,
            pronunciations=pronunciations,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar detalhes da lição: {str(e)}",
        )
