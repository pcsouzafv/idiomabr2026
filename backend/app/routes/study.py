from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.word import Word
from app.models.review import Review
from app.models.progress import UserProgress
from app.services.spaced_repetition import calculate_next_review
from app.schemas.review import ReviewCreate, ReviewResponse, StudySession, StudyCard, ProgressStats
from app.schemas.word import WordResponse
from app.services.word_examples import get_best_word_example, needs_example_regeneration

router = APIRouter(prefix="/api/study", tags=["Study"])


@router.get("/session", response_model=StudySession)
async def get_study_session(
    size: int = Query(10, ge=5, le=50, description="Número de cartões na sessão"),
    direction: str = Query("mixed", description="Direção: en_to_pt, pt_to_en, ou mixed"),
    mode: Literal["mixed", "new", "review"] = Query(
        "mixed",
        description="Modo: mixed (novas + revisões), new (apenas novas), review (apenas revisões)",
    ),
    level: Optional[str] = Query(None, description="Filtrar por nível (ex: A1, A2, B1...)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obter sessão de estudo com cartões para revisão e novas palavras.
    Prioridade: palavras para revisar hoje > novas palavras
    """
    cards = []
    today = datetime.now(timezone.utc)
    changed_any = False
    
    # 1. Buscar palavras que precisam de revisão (next_review <= hoje)
    if mode in ["mixed", "review"]:
        review_query = db.query(UserProgress, Word).join(
            Word, UserProgress.word_id == Word.id
        ).filter(
            UserProgress.user_id == current_user.id,
            UserProgress.next_review <= today,
        )

        if level:
            review_query = review_query.filter(Word.level == level)

        review_words = (
            review_query.order_by(UserProgress.next_review)
            .limit(size)
            .all()
        )

        for progress, word in review_words:
            if needs_example_regeneration(word):
                example_en, example_pt = await get_best_word_example(word, db)
                if example_en and example_pt:
                    word.example_en = example_en  # type: ignore[assignment]
                    word.example_pt = example_pt  # type: ignore[assignment]
                    changed_any = True

            card_direction = direction
            if direction == "mixed":
                # Alternar direção
                card_direction = "en_to_pt" if len(cards) % 2 == 0 else "pt_to_en"

            cards.append(
                StudyCard(
                    word=WordResponse.model_validate(word),
                    direction=card_direction,
                    is_new=False,
                )
            )
    
    # 2. Se ainda há espaço, adicionar novas palavras (a menos que seja modo review)
    remaining = size - len(cards)
    if remaining > 0 and mode in ["mixed", "new"]:
        # IDs das palavras já estudadas
        studied_ids = select(UserProgress.word_id).where(
            UserProgress.user_id == current_user.id
        )

        # Buscar palavras novas (não estudadas)
        new_query = db.query(Word).filter(~Word.id.in_(studied_ids))

        if level:
            new_query = new_query.filter(Word.level == level)

        new_words = (
            new_query.order_by(func.random())
            .limit(remaining)
            .all()
        )

        for word in new_words:
            if needs_example_regeneration(word):
                example_en, example_pt = await get_best_word_example(word, db)
                if example_en and example_pt:
                    word.example_en = example_en  # type: ignore[assignment]
                    word.example_pt = example_pt  # type: ignore[assignment]
                    changed_any = True

            card_direction = direction
            if direction == "mixed":
                card_direction = "en_to_pt" if len(cards) % 2 == 0 else "pt_to_en"

            cards.append(
                StudyCard(
                    word=WordResponse.model_validate(word),
                    direction=card_direction,
                    is_new=True,
                )
            )
    
    if changed_any:
        db.commit()

    return StudySession(
        cards=cards,
        total_new=sum(1 for c in cards if c.is_new),
        total_review=sum(1 for c in cards if not c.is_new),
        session_size=len(cards)
    )


@router.post("/review", response_model=ReviewResponse)
def submit_review(
    review_data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Registrar resultado de uma revisão e atualizar progresso.
    """
    # Criar registro de revisão
    review = Review(
        user_id=current_user.id,
        word_id=review_data.word_id,
        difficulty=review_data.difficulty,
        direction=review_data.direction
    )
    db.add(review)
    
    # Buscar ou criar progresso
    progress = db.query(UserProgress).filter(
        UserProgress.user_id == current_user.id,
        UserProgress.word_id == review_data.word_id
    ).first()
    
    if not progress:
        progress = UserProgress(
            user_id=current_user.id,
            word_id=review_data.word_id
        )
        db.add(progress)
        db.flush()
    
    # Calcular próxima revisão
    next_review, interval, ease, reps = calculate_next_review(review_data.difficulty, progress)

    progress.next_review = next_review  # type: ignore[assignment]
    progress.interval = interval  # type: ignore[assignment]
    progress.ease_factor = ease  # type: ignore[assignment]
    progress.repetitions = reps  # type: ignore[assignment]
    progress.last_review = datetime.now(timezone.utc)  # type: ignore[assignment]
    progress.total_reviews += 1  # type: ignore[assignment]

    if review_data.difficulty in ["easy", "medium"]:
        progress.correct_count += 1  # type: ignore[assignment]
    
    # Atualizar streak do usuário
    today = datetime.now(timezone.utc).date()
    if current_user.last_study_date:
        last_date = current_user.last_study_date.date()
        if last_date == today - timedelta(days=1):
            current_user.current_streak += 1  # type: ignore[assignment]
        elif last_date != today:
            current_user.current_streak = 1  # type: ignore[assignment]
    else:
        current_user.current_streak = 1  # type: ignore[assignment]

    current_user.last_study_date = datetime.now(timezone.utc)  # type: ignore[assignment]
    
    db.commit()
    db.refresh(review)
    
    return review


@router.get("/stats", response_model=ProgressStats)
def get_progress_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obter estatísticas de progresso do usuário.
    """
    today = datetime.now(timezone.utc)
    today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Total de palavras estudadas (já possuem registro de progresso)
    total_studied = db.query(UserProgress).filter(
        UserProgress.user_id == current_user.id
    ).count()

    # Total de palavras aprendidas/dominadas (repetitions >= 3)
    total_learned = db.query(UserProgress).filter(
        UserProgress.user_id == current_user.id,
        UserProgress.repetitions >= 3
    ).count()
    
    # Palavras estudadas hoje
    words_today = db.query(Review).filter(
        Review.user_id == current_user.id,
        Review.reviewed_at >= today_start
    ).distinct(Review.word_id).count()
    
    # Palavras para revisar hoje
    to_review = db.query(UserProgress).filter(
        UserProgress.user_id == current_user.id,
        UserProgress.next_review <= today
    ).count()
    
    # Novas palavras disponíveis
    studied_ids = db.query(UserProgress.word_id).filter(
        UserProgress.user_id == current_user.id
    ).subquery()
    
    new_available = db.query(Word).filter(
        ~Word.id.in_(studied_ids)
    ).count()
    
    # Calcular progresso da meta diária
    daily_progress = min(100, (words_today / current_user.daily_goal) * 100) if current_user.daily_goal > 0 else 0
    
    return ProgressStats(
        total_words_studied=total_studied,
        total_words_learned=total_learned,
        words_studied_today=words_today,
        current_streak=current_user.current_streak,
        words_to_review_today=to_review,
        new_words_available=new_available,
        daily_goal=current_user.daily_goal,
        daily_goal_progress=daily_progress
    )


@router.get("/history")
def get_study_history(
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obter histórico de estudo dos últimos X dias.
    """
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Agrupar revisões por dia
    reviews = db.query(
        func.date(Review.reviewed_at).label('date'),
        func.count(Review.id).label('count')
    ).filter(
        Review.user_id == current_user.id,
        Review.reviewed_at >= start_date
    ).group_by(func.date(Review.reviewed_at)).all()
    
    history = {str(r.date): r.count for r in reviews}
    
    return {
        "history": history,
        "period_days": days
    }
