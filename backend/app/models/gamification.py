# cspell:ignore Modelos gamificacao conquistas Baseado palavras aprendidas seguidos jogos jogados Pontuacoes perfeitas Velocidade Nivel Estatisticas usuario gerais maximo segundos onupdate disponiveis icone necessario desbloquear ganho Relacionamento Relacionamentos desbloqueadas pelo sessoes Desafios diarios Progresso Registro
"""
Modelos para sistema de gamificacao: XP, conquistas, rankings.
"""
from datetime import datetime, timezone
import enum

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base  # type: ignore[attr-defined]


class AchievementType(str, enum.Enum):
    WORDS = "words"           # Baseado em palavras aprendidas
    STREAK = "streak"         # Baseado em dias seguidos
    GAMES = "games"           # Baseado em jogos jogados
    PERFECT = "perfect"       # Pontuacoes perfeitas
    SPEED = "speed"           # Velocidade
    LEVEL = "level"           # Nivel de XP


class UserStats(Base):  # type: ignore[misc]
    """Estatisticas do usuario para gamificacao."""
    __tablename__ = "user_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # XP e Nivel
    total_xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    
    # Estatisticas gerais
    words_learned = Column(Integer, default=0)
    words_mastered = Column(Integer, default=0)  # Palavras com nivel maximo
    total_reviews = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    
    # Jogos
    games_played = Column(Integer, default=0)
    games_won = Column(Integer, default=0)
    best_quiz_score = Column(Integer, default=0)
    best_hangman_streak = Column(Integer, default=0)
    best_matching_time = Column(Integer, nullable=True)  # Em segundos
    
    # Streaks
    longest_streak = Column(Integer, default=0)
    
    # Timestamps
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda _: datetime.now(timezone.utc)  # type: ignore[misc]
    )


class Achievement(Base):  # type: ignore[misc]
    """Conquistas disponiveis no sistema."""
    __tablename__ = "achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=False)
    icon = Column(String(50), default=":trophy:")  # Emoji ou nome do icone
    type = Column(String(20), default="words")
    requirement = Column(Integer, default=1)  # Valor necessario para desbloquear
    xp_reward = Column(Integer, default=50)  # XP ganho ao desbloquear
    
    # Relacionamento
    user_achievements = relationship(  # type: ignore[misc]
        "UserAchievement",
        back_populates="achievement"
    )


class UserAchievement(Base):  # type: ignore[misc]
    """Conquistas desbloqueadas pelo usuario."""
    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    achievement_id = Column(Integer, ForeignKey("achievements.id"), nullable=False)
    unlocked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relacionamentos
    achievement = relationship(  # type: ignore[misc]
        "Achievement",
        back_populates="user_achievements"
    )
    user = relationship("User")  # type: ignore[misc]


class GameSession(Base):  # type: ignore[misc]
    """Registro de sessoes de jogos."""
    __tablename__ = "game_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    game_type = Column(String(50), nullable=False)  # quiz, hangman, matching, dictation
    score = Column(Integer, default=0)
    max_score = Column(Integer, default=0)
    time_spent = Column(Integer, default=0)  # Segundos
    xp_earned = Column(Integer, default=0)
    level_filter = Column(String(10), nullable=True)  # A1, A2, etc.
    completed = Column(Boolean, default=True)
    played_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class DailyChallenge(Base):  # type: ignore[misc]
    """Desafios diarios."""
    __tablename__ = "daily_challenges"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False, index=True)
    challenge_type = Column(String(50), nullable=False)
    target = Column(Integer, default=10)
    xp_reward = Column(Integer, default=100)
    description = Column(String(500), nullable=False)


class UserDailyChallenge(Base):  # type: ignore[misc]
    """Progresso do usuario em desafios diarios."""
    __tablename__ = "user_daily_challenges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    challenge_id = Column(Integer, ForeignKey("daily_challenges.id"), nullable=False)
    progress = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
