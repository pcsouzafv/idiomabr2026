"""
Rotas para jogos interativos: Quiz, Hangman, Matching, Dictation.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import random
import uuid
import math
from datetime import datetime, timezone, timedelta

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.word import Word
from app.models.review import Review
from app.models.progress import UserProgress
from app.models.gamification import UserStats, GameSession, Achievement, UserAchievement
from app.services.spaced_repetition import calculate_next_review
from app.schemas.games import (
    QuizSessionResponse, QuizQuestion,
    QuizResultRequest, QuizResultResponse,
    HangmanState, HangmanGuessRequest, HangmanGuessResponse,
    MatchingGameResponse, MatchingCard,
    MatchingResultRequest, MatchingResultResponse,
    DictationSessionResponse, DictationWord,
    DictationResultRequest, DictationResultResponse,
    GameSessionResponse
)

router = APIRouter(prefix="/api/games", tags=["games"])

# Armazenamento temporário de sessões (em produção usar Redis)
game_sessions = {}

# XP por tipo de jogo
XP_REWARDS = {
    "quiz": {"base": 5, "correct": 10, "perfect_bonus": 50},
    "hangman": {"win": 30, "letter": 2},
    "matching": {"base": 20, "time_bonus_per_second": 1, "max_time_bonus": 100},
    "dictation": {"base": 5, "correct": 15, "perfect_bonus": 75}
}


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


def check_achievements(db: Session, user_id: int, stats: UserStats) -> list:
    """Verifica e desbloqueia novas conquistas."""
    new_achievements = []
    
    # Buscar conquistas não desbloqueadas
    unlocked_ids = db.query(UserAchievement.achievement_id).filter(
        UserAchievement.user_id == user_id
    ).all()
    unlocked_ids = [a[0] for a in unlocked_ids]
    
    achievements = db.query(Achievement).filter(
        ~Achievement.id.in_(unlocked_ids) if unlocked_ids else True
    ).all()
    
    for achievement in achievements:
        unlocked = False
        
        if achievement.type == "words" and stats.words_learned >= achievement.requirement:
            unlocked = True
        elif achievement.type == "streak" and stats.longest_streak >= achievement.requirement:
            unlocked = True
        elif achievement.type == "games" and stats.games_played >= achievement.requirement:
            unlocked = True
        elif achievement.type == "level" and stats.level >= achievement.requirement:
            unlocked = True
        
        if unlocked:
            user_achievement = UserAchievement(
                user_id=user_id,
                achievement_id=achievement.id
            )
            db.add(user_achievement)
            stats.total_xp += achievement.xp_reward  # type: ignore[misc]
            new_achievements.append(achievement)
    
    if new_achievements:
        db.commit()
    
    return new_achievements


# ==================== QUIZ ====================

@router.post("/quiz/start", response_model=QuizSessionResponse)
def start_quiz(
    num_questions: int = 10,
    level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Inicia uma sessão de quiz de múltipla escolha."""
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
    
    session_id = str(uuid.uuid4())
    game_sessions[session_id] = {
        "type": "quiz",
        "user_id": current_user.id,
        "questions": questions,
        "created_at": datetime.now(timezone.utc)
    }
    
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
    session_id = request.session_id
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    session = game_sessions[session_id]
    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Sessão não pertence ao usuário")
    
    questions = session["questions"]
    
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
    del game_sessions[session_id]
    
    return QuizResultResponse(
        score=correct,
        total=total,
        percentage=percentage,
        xp_earned=xp,
        correct_words=correct_words,
        incorrect_words=incorrect_words,
        new_achievements=new_achievements
    )


# ==================== HANGMAN ====================

@router.post("/hangman/start", response_model=HangmanState)
def start_hangman(
    level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Inicia um novo jogo da forca."""
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
    
    word = random.choice(valid_words)
    english_clean = word.english.strip()
    session_id = str(uuid.uuid4())
    
    game_sessions[session_id] = {
        "type": "hangman",
        "user_id": current_user.id,
        "word": english_clean.lower(),
        "word_id": word.id,
        "guessed": [],
        "attempts_left": 6,
        "hint": word.portuguese.strip(),
        "ipa": word.ipa or "",
        "created_at": datetime.now(timezone.utc)
    }
    
    display = " ".join(["_" for _ in english_clean])
    
    return HangmanState(
        session_id=session_id,
        word_id=word.id,
        display=display,
        guessed_letters=[],
        attempts_left=6,
        max_attempts=6,
        hint=word.portuguese.strip(),
        ipa=word.ipa or ""
    )


@router.post("/hangman/{session_id}/guess", response_model=HangmanGuessResponse)
def guess_hangman(
    session_id: str,
    request: HangmanGuessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Tenta adivinhar uma letra no jogo da forca."""
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    session = game_sessions[session_id]
    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Sessão não pertence ao usuário")
    
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
        
        del game_sessions[session_id]
    
    return HangmanGuessResponse(
        correct=correct,
        display=display,
        guessed_letters=session["guessed"] if not game_over else [],
        attempts_left=session["attempts_left"] if not game_over else 0,
        game_over=game_over,
        won=won,
        word=word if game_over else None,
        xp_earned=xp_earned
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
    game_sessions[session_id] = {
        "type": "matching",
        "user_id": current_user.id,
        "pairs": num_pairs,
        "words": {w.id: {"en": en, "pt": pt} for (w, en, pt) in picked},
        "created_at": datetime.now(timezone.utc)
    }
    
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
    if request.session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    session = game_sessions[request.session_id]
    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Sessão não pertence ao usuário")
    
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
        word_ids = list(session.get("words", {}).keys())

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
    
    del game_sessions[request.session_id]
    
    return MatchingResultResponse(
        score=pairs if request.completed else 0,
        time_spent=request.time_spent,
        moves=request.moves,
        xp_earned=xp,
        is_best_time=is_best
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
        word_map[word.id] = english_clean.lower()
    
    session_id = str(uuid.uuid4())
    game_sessions[session_id] = {
        "type": "dictation",
        "user_id": current_user.id,
        "words": word_map,
        "created_at": datetime.now(timezone.utc)
    }
    
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
    session_id = request.session_id
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    session = game_sessions[session_id]
    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Sessão não pertence ao usuário")
    
    word_map = session["words"]
    
    correct = 0
    results = []
    
    for answer in request.answers:
        if answer.word_id in word_map:
            correct_word = word_map[answer.word_id]
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
    
    del game_sessions[session_id]
    
    return DictationResultResponse(
        score=correct,
        total=total,
        percentage=percentage,
        xp_earned=xp,
        results=results
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
