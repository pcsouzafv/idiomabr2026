from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
from typing import List, Optional
from datetime import datetime, timedelta
import random
import io
import hashlib
from difflib import SequenceMatcher

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.sentence import Sentence, SentenceReview, UserSentenceProgress, AIConversation
from app.models.audio_attempt import AudioAttempt
from app.schemas.sentence import (
    SentenceResponse,
    SentenceCreate,
    SentenceReviewCreate,
    SentenceReviewResponse,
    StudySession,
    StudyCard,
    AITeacherRequest,
    AITeacherResponse,
    AIConversationResponse
)
from app.services.ai_teacher import ai_teacher_service
from app.services.rag_service import rag_service
from app.services.spaced_repetition import calculate_next_review

router = APIRouter(prefix="/api/sentences", tags=["sentences"])


@router.get("/", response_model=List[SentenceResponse])
def list_sentences(
    skip: int = 0,
    limit: int = 20,
    level: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    mode: str = "smart",  # smart, new, review, all
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lista frases disponíveis com Sistema de Repetição Espaçada (SRS).

    Modos:
    - smart (padrão): Prioriza revisões + frases novas (igual ao sistema de palavras)
    - new: Apenas frases novas (nunca estudadas)
    - review: Apenas frases para revisar
    - all: Todas as frases (sem filtro de progresso)
    """

    now = datetime.utcnow()

    if mode == "smart":
        # PRIORIDADE 1: Frases para revisar (next_review <= agora)
        review_query = db.query(Sentence).join(
            UserSentenceProgress,
            and_(
                UserSentenceProgress.sentence_id == Sentence.id,
                UserSentenceProgress.user_id == current_user.id
            )
        ).filter(
            UserSentenceProgress.next_review <= now
        )

        if level:
            review_query = review_query.filter(Sentence.level == level)
        if category:
            review_query = review_query.filter(Sentence.category == category)
        if search:
            review_query = review_query.filter(
                or_(
                    Sentence.english.ilike(f"%{search}%"),
                    Sentence.portuguese.ilike(f"%{search}%")
                )
            )

        review_sentences = review_query.order_by(UserSentenceProgress.next_review).limit(limit // 2).all()

        # PRIORIDADE 2: Frases novas (nunca estudadas)
        studied_ids = db.query(UserSentenceProgress.sentence_id).filter(
            UserSentenceProgress.user_id == current_user.id
        ).all()
        studied_ids = [sid[0] for sid in studied_ids]

        new_query = db.query(Sentence).filter(
            ~Sentence.id.in_(studied_ids) if studied_ids else True
        )

        if level:
            new_query = new_query.filter(Sentence.level == level)
        if category:
            new_query = new_query.filter(Sentence.category == category)
        if search:
            new_query = new_query.filter(
                or_(
                    Sentence.english.ilike(f"%{search}%"),
                    Sentence.portuguese.ilike(f"%{search}%")
                )
            )

        new_sentences = new_query.order_by(
            Sentence.difficulty_score,
            func.random()
        ).limit(limit - len(review_sentences)).all()

        # Combinar revisões + novas (revisões primeiro)
        sentences = review_sentences + new_sentences

    elif mode == "new":
        # Apenas frases novas
        studied_ids = db.query(UserSentenceProgress.sentence_id).filter(
            UserSentenceProgress.user_id == current_user.id
        ).all()
        studied_ids = [sid[0] for sid in studied_ids]

        query = db.query(Sentence).filter(
            ~Sentence.id.in_(studied_ids) if studied_ids else True
        )

        if level:
            query = query.filter(Sentence.level == level)
        if category:
            query = query.filter(Sentence.category == category)
        if search:
            query = query.filter(
                or_(
                    Sentence.english.ilike(f"%{search}%"),
                    Sentence.portuguese.ilike(f"%{search}%")
                )
            )

        sentences = query.order_by(Sentence.difficulty_score).offset(skip).limit(limit).all()

    elif mode == "review":
        # Apenas frases para revisar
        query = db.query(Sentence).join(
            UserSentenceProgress,
            and_(
                UserSentenceProgress.sentence_id == Sentence.id,
                UserSentenceProgress.user_id == current_user.id
            )
        ).filter(
            UserSentenceProgress.next_review <= now
        )

        if level:
            query = query.filter(Sentence.level == level)
        if category:
            query = query.filter(Sentence.category == category)
        if search:
            query = query.filter(
                or_(
                    Sentence.english.ilike(f"%{search}%"),
                    Sentence.portuguese.ilike(f"%{search}%")
                )
            )

        sentences = query.order_by(UserSentenceProgress.next_review).offset(skip).limit(limit).all()

    else:  # mode == "all"
        # Todas as frases (comportamento antigo)
        query = db.query(Sentence)

        if level:
            query = query.filter(Sentence.level == level)
        if category:
            query = query.filter(Sentence.category == category)
        if search:
            query = query.filter(
                or_(
                    Sentence.english.ilike(f"%{search}%"),
                    Sentence.portuguese.ilike(f"%{search}%")
                )
            )

        sentences = query.offset(skip).limit(limit).all()

    return sentences


@router.get("/{sentence_id}", response_model=SentenceResponse)
def get_sentence(
    sentence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtém detalhes de uma frase específica"""
    sentence = db.query(Sentence).filter(Sentence.id == sentence_id).first()
    if not sentence:
        raise HTTPException(status_code=404, detail="Frase não encontrada")
    return sentence


@router.get("/study/session", response_model=StudySession)
def get_study_session(
    size: int = 10,
    direction: str = "mixed",
    level: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cria uma sessão de estudo de frases.
    direction: 'en_to_pt', 'pt_to_en', ou 'mixed'
    """

    now = datetime.utcnow()

    # Buscar frases para revisar (vencidas)
    review_query = db.query(Sentence).join(
        UserSentenceProgress,
        and_(
            UserSentenceProgress.sentence_id == Sentence.id,
            UserSentenceProgress.user_id == current_user.id
        )
    ).filter(
        or_(
            UserSentenceProgress.next_review <= now,
            UserSentenceProgress.next_review.is_(None)
        )
    )

    if level:
        review_query = review_query.filter(Sentence.level == level)
    if category:
        review_query = review_query.filter(Sentence.category == category)

    review_sentences = review_query.limit(size // 2).all()

    # Buscar frases novas (nunca estudadas)
    studied_ids = db.query(UserSentenceProgress.sentence_id).filter(
        UserSentenceProgress.user_id == current_user.id
    ).all()
    studied_ids = [sid[0] for sid in studied_ids]

    new_query = db.query(Sentence).filter(
        ~Sentence.id.in_(studied_ids) if studied_ids else True
    )

    if level:
        new_query = new_query.filter(Sentence.level == level)
    if category:
        new_query = new_query.filter(Sentence.category == category)

    new_sentences = new_query.order_by(Sentence.difficulty_score).limit(size - len(review_sentences)).all()

    # Combinar e embaralhar
    all_sentences = review_sentences + new_sentences
    random.shuffle(all_sentences)

    # Criar cards
    cards = []
    for sentence in all_sentences:
        # Determinar direção
        if direction == "mixed":
            card_direction = random.choice(["en_to_pt", "pt_to_en"])
        else:
            card_direction = direction

        is_new = sentence.id not in [s.id for s in review_sentences]

        cards.append(StudyCard(
            sentence=SentenceResponse.model_validate(sentence),
            direction=card_direction,
            is_new=is_new
        ))

    return StudySession(
        cards=cards,
        total_new=len(new_sentences),
        total_review=len(review_sentences),
        session_size=len(cards)
    )


@router.post("/study/review", response_model=SentenceReviewResponse)
def submit_sentence_review(
    review: SentenceReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registra uma revisão de frase e atualiza o progresso"""

    # Verificar se a frase existe
    sentence = db.query(Sentence).filter(Sentence.id == review.sentence_id).first()
    if not sentence:
        raise HTTPException(status_code=404, detail="Frase não encontrada")

    # Criar review
    db_review = SentenceReview(
        user_id=current_user.id,
        sentence_id=review.sentence_id,
        difficulty=review.difficulty,
        direction=review.direction,
        reviewed_at=datetime.utcnow()
    )
    db.add(db_review)

    # Atualizar ou criar progresso
    progress = db.query(UserSentenceProgress).filter(
        and_(
            UserSentenceProgress.user_id == current_user.id,
            UserSentenceProgress.sentence_id == review.sentence_id
        )
    ).first()

    if not progress:
        progress = UserSentenceProgress(
            user_id=current_user.id,
            sentence_id=review.sentence_id,
            easiness_factor=2.5,
            interval=0,
            repetitions=0
        )
        db.add(progress)

    # Calcular próxima revisão usando algoritmo SM-2
    next_review_data = calculate_next_review(
        quality={"easy": 5, "medium": 3, "hard": 1}[review.difficulty],
        easiness_factor=progress.easiness_factor,
        interval=progress.interval,
        repetitions=progress.repetitions
    )

    progress.easiness_factor = next_review_data["easiness_factor"]
    progress.interval = next_review_data["interval"]
    progress.repetitions = next_review_data["repetitions"]
    progress.last_reviewed = datetime.utcnow()
    progress.next_review = datetime.utcnow() + timedelta(days=next_review_data["interval"])

    db.commit()
    db.refresh(db_review)

    return db_review


@router.post("/ai/ask", response_model=AITeacherResponse)
async def ask_ai_teacher(
    request: AITeacherRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Faz uma pergunta ao professor de IA.
    Pode incluir contexto de uma frase específica.
    """

    context = None

    # Se uma frase específica foi mencionada, buscar contexto
    if request.sentence_id and request.include_context:
        context = await rag_service.get_sentence_context(
            db=db,
            sentence_id=request.sentence_id,
            user_id=current_user.id
        )

    # Obter resposta da IA
    try:
        # Evita que a IA reinicie automaticamente a análise da frase quando o aluno
        # está fazendo uma pergunta objetiva sobre ela.
        teacher_prompt = f"""O aluno fez uma pergunta. Responda diretamente e de forma útil.

Pergunta do aluno:
{request.user_message}

Regras:
- Responda primeiro à pergunta.
- Use o contexto da frase somente se ajudar a responder.
- Não reinicie a análise da frase automaticamente.
- Depois, faça no máximo 1 pergunta de acompanhamento (opcional).
"""

        ai_response = await ai_teacher_service.get_ai_response(
            user_message=teacher_prompt,
            context=context,
            db=db,
            cache_operation="sentences.ai.ask",
            cache_scope=f"user:{current_user.id}",
        )

        # Salvar conversa no banco
        conversation = AIConversation(
            user_id=current_user.id,
            sentence_id=request.sentence_id,
            user_message=request.user_message,
            ai_response=ai_response["response"],
            model_used=ai_response["model_used"],
            context=str(context) if context else None
        )
        db.add(conversation)
        db.commit()

        return AITeacherResponse(
            response=ai_response["response"],
            model_used=ai_response["model_used"],
            context_used=context
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar solicitação: {str(e)}"
        )


@router.post("/ai/analyze/{sentence_id}", response_model=AITeacherResponse)
async def analyze_sentence_with_ai(
    sentence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Analisa uma frase específica com o professor de IA"""

    sentence = db.query(Sentence).filter(Sentence.id == sentence_id).first()
    if not sentence:
        raise HTTPException(status_code=404, detail="Frase não encontrada")

    # Obter estatísticas do usuário para personalizar
    user_stats = await rag_service._get_user_stats(db, current_user.id)

    try:
        ai_response = await ai_teacher_service.analyze_sentence(
            sentence_en=sentence.english,
            sentence_pt=sentence.portuguese,
            user_level=user_stats.get("estimated_level", "A1"),
            db=db,
            cache_operation="sentences.ai.analyze",
            cache_scope=f"user:{current_user.id}",
        )

        # Salvar conversa
        conversation = AIConversation(
            user_id=current_user.id,
            sentence_id=sentence_id,
            user_message=f"Analisar frase: {sentence.english}",
            ai_response=ai_response["response"],
            model_used=ai_response["model_used"]
        )
        db.add(conversation)
        db.commit()

        return AITeacherResponse(
            response=ai_response["response"],
            model_used=ai_response["model_used"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao analisar frase: {str(e)}"
        )


@router.get("/ai/history", response_model=List[AIConversationResponse])
def get_ai_conversation_history(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtém histórico de conversas com o professor de IA"""

    conversations = db.query(AIConversation).filter(
        AIConversation.user_id == current_user.id
    ).order_by(AIConversation.created_at.desc()).limit(limit).all()

    return conversations


@router.get("/stats", response_model=dict)
def get_sentence_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtém estatísticas de progresso com frases"""

    now = datetime.utcnow()

    # Total de frases aprendidas (repetitions >= 3)
    total_learned = db.query(UserSentenceProgress).filter(
        UserSentenceProgress.user_id == current_user.id,
        UserSentenceProgress.repetitions >= 3
    ).count()

    # Frases para revisar hoje
    to_review = db.query(UserSentenceProgress).filter(
        UserSentenceProgress.user_id == current_user.id,
        UserSentenceProgress.next_review <= now
    ).count()

    # Frases novas disponíveis
    studied_ids = db.query(UserSentenceProgress.sentence_id).filter(
        UserSentenceProgress.user_id == current_user.id
    ).subquery()

    new_available = db.query(Sentence).filter(
        ~Sentence.id.in_(studied_ids)
    ).count()

    # Total de frases no banco
    total_sentences = db.query(Sentence).count()

    # Frases estudadas (com pelo menos 1 revisão)
    total_studied = db.query(UserSentenceProgress).filter(
        UserSentenceProgress.user_id == current_user.id
    ).count()

    return {
        "total_learned": total_learned,
        "to_review_today": to_review,
        "new_available": new_available,
        "total_sentences": total_sentences,
        "total_studied": total_studied,
        "completion_percentage": round((total_studied / total_sentences * 100), 2) if total_sentences > 0 else 0
    }


@router.get("/recommendations", response_model=dict)
async def get_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtém recomendações personalizadas de frases para estudar"""

    recommendations = await rag_service.get_learning_recommendations(
        db=db,
        user_id=current_user.id,
        limit=10
    )

    return recommendations


@router.post("/ai/speak")
async def text_to_speech(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Converte texto em áudio (Text-to-Speech).
    Usa a voz da professora Sarah (nova - feminina e calorosa).

    Requer: OPENAI_API_KEY configurada no .env
    """
    try:
        text = request.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="Texto não fornecido")

        # Gerar áudio
        audio_bytes = await ai_teacher_service.generate_speech(
            text,
            db=db,
            cache_operation="sentences.ai.tts",
            cache_scope="global",
        )

        # Retornar como stream de áudio
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=teacher_voice.mp3"
            }
        )

    except Exception as e:
        error_msg = str(e)
        # Se o erro for de TTS não disponível, retornar 503 (Service Unavailable)
        if "TTS requer" in error_msg or "OpenAI API Key" in error_msg or "LEMONFOX_API_KEY" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="Text-to-Speech não disponível. Configure LEMONFOX_API_KEY ou OPENAI_API_KEY para usar áudio."
            )
        # Outros erros
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar áudio: {error_msg}"
        )


@router.post("/ai/pronunciation/{sentence_id}")
async def analyze_pronunciation(
    sentence_id: int,
    audio: UploadFile = File(...),
    expected_text: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Recebe áudio do aluno, transcreve (STT) e gera feedback de pronúncia; grava tudo no banco."""

    sentence = db.query(Sentence).filter(Sentence.id == sentence_id).first()
    if not sentence:
        raise HTTPException(status_code=404, detail="Frase não encontrada")

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Arquivo de áudio vazio")

    sha = hashlib.sha256(audio_bytes).hexdigest()

    expected = expected_text or sentence.english
    transcript = ""
    feedback = ""
    similarity = None
    model_used = None

    try:
        transcript = await ai_teacher_service.transcribe_audio(
            audio_bytes=audio_bytes,
            filename=audio.filename or "audio.webm",
            content_type=audio.content_type or "audio/webm",
            language="en",
            prompt=expected,
        )

        def _norm(s: str) -> str:
            return " ".join((s or "").lower().strip().split())

        if expected:
            similarity = int(round(SequenceMatcher(None, _norm(expected), _norm(transcript)).ratio() * 100))

        prompt = f"""Você é uma professora de inglês (Sarah). O aluno gravou um áudio para praticar pronúncia.

TEXTO-ALVO (o que o aluno deveria dizer):
{expected}

TRANSCRIÇÃO DO ÁUDIO (STT):
{transcript}

Com base SOMENTE nessa transcrição (não assuma áudio perfeito), dê feedback em português:
1) Se o aluno parece ter dito certo ou não
2) Quais palavras provavelmente saíram erradas
3) Dicas práticas (ritmo, contrações, finais, etc.)
4) Uma versão "bem falada" para o aluno repetir
"""

        ai = await ai_teacher_service.get_ai_response(
            user_message=prompt,
            context=None,
            conversation_history=None,
            db=db,
            cache_operation="sentences.ai.pronunciation",
            cache_scope=f"user:{current_user.id}",
        )
        feedback = ai.get("response") or ""
        model_used = ai.get("model_used")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao analisar áudio: {str(e)}")
    finally:
        attempt = AudioAttempt(
            user_id=current_user.id,
            sentence_id=sentence_id,
            filename=audio.filename,
            content_type=audio.content_type,
            audio_sha256=sha,
            audio_bytes=audio_bytes,
            expected_text=expected,
            transcript=transcript,
            similarity=similarity,
            ai_feedback=feedback,
            ai_json=None,
            model_used=model_used,
        )
        db.add(attempt)
        db.commit()

    return {
        "sentence_id": sentence_id,
        "expected_text": expected,
        "transcript": transcript,
        "similarity": similarity,
        "feedback": feedback,
        "model_used": model_used,
    }


# ==================== ADMIN ENDPOINTS ====================

@router.post("/admin/create", response_model=SentenceResponse)
def create_sentence_admin(
    sentence_data: SentenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    [ADMIN] Criar nova frase no banco de dados.
    Apenas usuários autorizados podem adicionar frases.
    """

    # Verificar se a frase já existe
    existing = db.query(Sentence).filter(
        or_(
            Sentence.english == sentence_data.english,
            Sentence.portuguese == sentence_data.portuguese
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Frase já existe no banco de dados"
        )

    # Criar nova frase
    new_sentence = Sentence(
        english=sentence_data.english,
        portuguese=sentence_data.portuguese,
        level=sentence_data.level,
        category=sentence_data.category,
        difficulty_score=sentence_data.difficulty_score or 0.0,
        grammar_points=sentence_data.grammar_points,
        vocabulary_used=sentence_data.vocabulary_used
    )

    db.add(new_sentence)
    db.commit()
    db.refresh(new_sentence)

    return new_sentence


@router.put("/admin/{sentence_id}", response_model=SentenceResponse)
def update_sentence_admin(
    sentence_id: int,
    sentence_data: SentenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """[ADMIN] Atualizar frase existente"""

    sentence = db.query(Sentence).filter(Sentence.id == sentence_id).first()
    if not sentence:
        raise HTTPException(status_code=404, detail="Frase não encontrada")

    # Atualizar campos
    sentence.english = sentence_data.english
    sentence.portuguese = sentence_data.portuguese
    sentence.level = sentence_data.level
    sentence.category = sentence_data.category
    sentence.difficulty_score = sentence_data.difficulty_score or 0.0
    sentence.grammar_points = sentence_data.grammar_points
    sentence.vocabulary_used = sentence_data.vocabulary_used
    sentence.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(sentence)

    return sentence


@router.delete("/admin/{sentence_id}")
def delete_sentence_admin(
    sentence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """[ADMIN] Deletar frase"""

    sentence = db.query(Sentence).filter(Sentence.id == sentence_id).first()
    if not sentence:
        raise HTTPException(status_code=404, detail="Frase não encontrada")

    db.delete(sentence)
    db.commit()

    return {"message": "Frase deletada com sucesso"}


@router.post("/admin/bulk-create", response_model=dict)
def bulk_create_sentences_admin(
    sentences: List[SentenceCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    [ADMIN] Criar múltiplas frases de uma vez.
    Útil para importar frases em massa.
    """

    created = []
    skipped = []

    for sentence_data in sentences:
        # Verificar se já existe
        existing = db.query(Sentence).filter(
            or_(
                Sentence.english == sentence_data.english,
                Sentence.portuguese == sentence_data.portuguese
            )
        ).first()

        if existing:
            skipped.append({
                "english": sentence_data.english,
                "reason": "Já existe"
            })
            continue

        # Criar nova frase
        new_sentence = Sentence(
            english=sentence_data.english,
            portuguese=sentence_data.portuguese,
            level=sentence_data.level,
            category=sentence_data.category,
            difficulty_score=sentence_data.difficulty_score or 0.0,
            grammar_points=sentence_data.grammar_points,
            vocabulary_used=sentence_data.vocabulary_used
        )

        db.add(new_sentence)
        created.append(sentence_data.english)

    db.commit()

    return {
        "created_count": len(created),
        "skipped_count": len(skipped),
        "created": created[:10],  # Primeiras 10
        "skipped": skipped[:10]   # Primeiras 10
    }
