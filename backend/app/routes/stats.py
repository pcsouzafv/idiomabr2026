"""
Rotas para gamificação: estatísticas, conquistas, ranking.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.progress import UserProgress
from app.models.gamification import (
    UserStats, Achievement, UserAchievement, 
    DailyChallenge, UserDailyChallenge, GameSession
)
from app.schemas.games import (
    UserStatsResponse, AchievementResponse, UserAchievementResponse,
    DailyChallengeResponse, LeaderboardEntry, LeaderboardResponse
)

router = APIRouter(prefix="/api/stats", tags=["stats"])


def calculate_level(xp: int) -> int:
    """Calcula o nível baseado no XP total."""
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


@router.get("/me", response_model=UserStatsResponse)
def get_my_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna estatísticas do usuário atual."""
    stats = get_or_create_stats(db, current_user.id)

    # Sincroniza contadores derivados para evitar progresso de conquistas defasado.
    learned_words_count = db.query(func.count(UserProgress.id)).filter(
        UserProgress.user_id == current_user.id,
        UserProgress.correct_count >= 3,
    ).scalar() or 0

    max_streak = max(int(stats.longest_streak or 0), int(current_user.current_streak or 0))

    stats_changed = False
    if int(stats.words_learned or 0) != int(learned_words_count):
        stats.words_learned = int(learned_words_count)  # type: ignore[assignment]
        stats_changed = True
    if int(stats.longest_streak or 0) != max_streak:
        stats.longest_streak = max_streak  # type: ignore[assignment]
        stats_changed = True
    if stats_changed:
        db.commit()
        db.refresh(stats)

    # Garante que conquistas sejam avaliadas mesmo fora do fluxo de quiz.
    from app.services.achievements import check_and_unlock_achievements

    newly_unlocked = check_and_unlock_achievements(db, current_user.id)
    if newly_unlocked:
        db.refresh(stats)

    perfect_games_count = db.query(func.count(GameSession.id)).filter(
        GameSession.user_id == current_user.id,
        GameSession.completed.is_(True),
        GameSession.max_score > 0,
        GameSession.score >= GameSession.max_score,
    ).scalar() or 0
    
    # Calcular progresso para próximo nível
    current_level_xp = xp_for_level(stats.level)
    next_level_xp = xp_for_level(stats.level + 1)
    xp_in_level = stats.total_xp - current_level_xp
    xp_needed = next_level_xp - current_level_xp
    
    response = UserStatsResponse(
        id=stats.id,
        user_id=stats.user_id,
        total_xp=stats.total_xp,
        level=stats.level,
        words_learned=stats.words_learned,
        words_mastered=stats.words_mastered,
        total_reviews=stats.total_reviews,
        correct_answers=stats.correct_answers,
        games_played=stats.games_played,
        games_won=stats.games_won,
        longest_streak=stats.longest_streak,
        best_quiz_score=stats.best_quiz_score,
        best_hangman_streak=stats.best_hangman_streak,
        best_matching_time=stats.best_matching_time,
        perfect_games=int(perfect_games_count),
        xp_to_next_level=xp_needed - xp_in_level,
        level_progress=(xp_in_level / xp_needed) * 100 if xp_needed > 0 else 100
    )
    
    return response


@router.get("/achievements", response_model=List[AchievementResponse])
def get_all_achievements(db: Session = Depends(get_db)):
    """Lista todas as conquistas disponíveis."""
    return db.query(Achievement).all()


@router.get("/achievements/me", response_model=List[UserAchievementResponse])
def get_my_achievements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista conquistas desbloqueadas pelo usuário."""
    user_achievements = db.query(UserAchievement).filter(
        UserAchievement.user_id == current_user.id
    ).all()
    
    return [
        UserAchievementResponse(
            achievement=ua.achievement,
            unlocked_at=ua.unlocked_at
        )
        for ua in user_achievements
    ]


@router.get("/leaderboard", response_model=LeaderboardResponse)
def get_leaderboard(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna ranking de jogadores por XP."""
    # Top jogadores
    top_stats = db.query(UserStats, User).join(
        User, User.id == UserStats.user_id
    ).order_by(desc(UserStats.total_xp)).limit(limit).all()
    
    entries = []
    for rank, (stats, user) in enumerate(top_stats, 1):
        entries.append(LeaderboardEntry(
            rank=rank,
            user_id=user.id,
            name=user.name,
            total_xp=stats.total_xp,
            level=stats.level,
            words_learned=stats.words_learned
        ))
    
    # Posição do usuário atual
    user_stats = get_or_create_stats(db, current_user.id)
    user_rank = db.query(func.count(UserStats.id)).filter(
        UserStats.total_xp > user_stats.total_xp
    ).scalar() + 1
    
    return LeaderboardResponse(
        entries=entries,
        user_rank=user_rank
    )


@router.get("/daily-challenge", response_model=DailyChallengeResponse)
def get_daily_challenge(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna o desafio diário atual."""
    today = datetime.now(timezone.utc).date()
    
    # Buscar ou criar desafio do dia
    challenge = db.query(DailyChallenge).filter(
        func.date(DailyChallenge.date) == today
    ).first()
    
    if not challenge:
        # Criar desafio do dia
        import random
        challenges = [
            {"type": "reviews", "target": 20, "desc": "Complete 20 revisões de palavras"},
            {"type": "quiz", "target": 3, "desc": "Jogue 3 partidas de Quiz"},
            {"type": "perfect", "target": 1, "desc": "Consiga uma pontuação perfeita em qualquer jogo"},
            {"type": "words", "target": 10, "desc": "Aprenda 10 novas palavras"},
            {"type": "games", "target": 5, "desc": "Jogue 5 jogos diferentes"},
        ]
        selected = random.choice(challenges)
        
        challenge = DailyChallenge(
            date=datetime.now(timezone.utc),
            challenge_type=selected["type"],
            target=selected["target"],
            xp_reward=100,
            description=selected["desc"]
        )
        db.add(challenge)
        db.commit()
        db.refresh(challenge)
    
    # Buscar progresso do usuário
    user_challenge = db.query(UserDailyChallenge).filter(
        UserDailyChallenge.user_id == current_user.id,
        UserDailyChallenge.challenge_id == challenge.id
    ).first()
    
    progress = 0
    completed = False
    
    if user_challenge:
        progress = user_challenge.progress
        completed = user_challenge.completed
    else:
        # Calcular progresso baseado nas atividades do dia
        if challenge.challenge_type == "games":
            progress = db.query(GameSession).filter(
                GameSession.user_id == current_user.id,
                func.date(GameSession.played_at) == today
            ).count()
        elif challenge.challenge_type == "quiz":
            progress = db.query(GameSession).filter(
                GameSession.user_id == current_user.id,
                GameSession.game_type == "quiz",
                func.date(GameSession.played_at) == today
            ).count()
    
    return DailyChallengeResponse(
        id=challenge.id,
        challenge_type=challenge.challenge_type,
        target=challenge.target,
        xp_reward=challenge.xp_reward,
        description=challenge.description,
        progress=min(progress, challenge.target),
        completed=completed or progress >= challenge.target
    )


@router.get("/summary")
def get_stats_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna um resumo das estatísticas para o dashboard."""
    stats = get_or_create_stats(db, current_user.id)
    
    # Estatísticas dos últimos 7 dias
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    weekly_games = db.query(GameSession).filter(
        GameSession.user_id == current_user.id,
        GameSession.played_at >= week_ago
    ).all()
    
    weekly_xp = sum(g.xp_earned for g in weekly_games)
    weekly_games_count = len(weekly_games)
    
    # Precisão geral
    accuracy = 0
    if stats.total_reviews > 0:
        accuracy = (stats.correct_answers / stats.total_reviews) * 100
    
    # Jogos por tipo
    games_by_type = {}
    for game in weekly_games:
        if game.game_type not in games_by_type:
            games_by_type[game.game_type] = 0
        games_by_type[game.game_type] += 1
    
    return {
        "total_xp": stats.total_xp,
        "level": stats.level,
        "words_learned": stats.words_learned,
        "current_streak": current_user.current_streak,
        "longest_streak": stats.longest_streak,
        "accuracy": round(accuracy, 1),
        "weekly_xp": weekly_xp,
        "weekly_games": weekly_games_count,
        "games_by_type": games_by_type,
        "achievements_count": db.query(UserAchievement).filter(
            UserAchievement.user_id == current_user.id
        ).count()
    }
