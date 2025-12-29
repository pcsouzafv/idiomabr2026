"""
Serviço para verificar e desbloquear conquistas automaticamente.
"""
from sqlalchemy.orm import Session
from app.models.gamification import (
    Achievement, UserAchievement, AchievementType
)
from app.routes.stats import get_or_create_stats


def check_and_unlock_achievements(db: Session, user_id: int) -> list[Achievement]:
    """
    Verifica e desbloqueia conquistas para um usuário.
    Retorna lista de conquistas recém-desbloqueadas.
    """
    newly_unlocked = []

    # Obter estatísticas do usuário
    stats = get_or_create_stats(db, user_id)

    # Obter todas as conquistas
    all_achievements = db.query(Achievement).all()

    # Obter conquistas já desbloqueadas
    unlocked_ids = {
        ua.achievement_id
        for ua in db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id
        ).all()
    }

    for achievement in all_achievements:
        # Pular se já desbloqueada
        if achievement.id in unlocked_ids:
            continue

        # Verificar se atende aos requisitos
        should_unlock = False

        if achievement.type == AchievementType.WORDS:
            should_unlock = stats.words_learned >= achievement.requirement
        elif achievement.type == AchievementType.STREAK:
            should_unlock = stats.longest_streak >= achievement.requirement
        elif achievement.type == AchievementType.GAMES:
            should_unlock = stats.games_played >= achievement.requirement
        elif achievement.type == AchievementType.PERFECT:
            # TODO: Track perfect scores separately
            pass
        elif achievement.type == AchievementType.SPEED:
            if stats.best_matching_time:
                should_unlock = stats.best_matching_time <= achievement.requirement
        elif achievement.type == AchievementType.LEVEL:
            should_unlock = stats.level >= achievement.requirement

        # Desbloquear conquista
        if should_unlock:
            user_achievement = UserAchievement(
                user_id=user_id,
                achievement_id=achievement.id
            )
            db.add(user_achievement)

            # Adicionar XP da conquista
            stats.total_xp += achievement.xp_reward  # type: ignore[assignment]

            newly_unlocked.append(achievement)

    if newly_unlocked:
        # Recalcular nível baseado no novo XP
        from app.routes.stats import calculate_level
        stats.level = calculate_level(int(stats.total_xp))  # type: ignore[assignment,arg-type]

        db.commit()

    return newly_unlocked


def award_xp(db: Session, user_id: int, xp_amount: int) -> dict:
    """
    Adiciona XP ao usuário e atualiza o nível.
    Retorna informações sobre XP e nível.
    """
    stats = get_or_create_stats(db, user_id)

    old_level = stats.level
    old_xp = stats.total_xp

    # Adicionar XP
    stats.total_xp += xp_amount  # type: ignore[assignment]

    # Recalcular nível
    from app.routes.stats import calculate_level
    stats.level = calculate_level(int(stats.total_xp))  # type: ignore[assignment,arg-type]

    db.commit()

    # Verificar conquistas após adicionar XP
    newly_unlocked = check_and_unlock_achievements(db, user_id)

    return {
        "old_xp": old_xp,
        "new_xp": stats.total_xp,
        "xp_gained": xp_amount,
        "old_level": old_level,
        "new_level": stats.level,
        "level_up": stats.level > old_level,
        "newly_unlocked_achievements": [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "icon": a.icon,
                "xp_reward": a.xp_reward
            }
            for a in newly_unlocked
        ]
    }


def update_game_stats(
    db: Session,
    user_id: int,
    game_type: str,
    score: int,
    max_score: int,
    time_spent: int,
    completed: bool = True
) -> dict:
    """
    Atualiza estatísticas de jogos e concede XP.
    """
    stats = get_or_create_stats(db, user_id)

    # Atualizar contadores
    stats.games_played += 1  # type: ignore[assignment]
    if completed and score == max_score:
        stats.games_won += 1  # type: ignore[assignment]

    # Calcular XP baseado no desempenho
    base_xp = 10

    # Bônus por completar
    if completed:
        base_xp += 10

    # Bônus por pontuação perfeita
    if score == max_score and max_score > 0:
        base_xp += 20

    # Bônus por proporção de acertos
    if max_score > 0:
        accuracy = score / max_score
        base_xp += int(accuracy * 20)

    # Atualizar melhores pontuações
    if game_type == "quiz" and score > stats.best_quiz_score:
        stats.best_quiz_score = score  # type: ignore[assignment]

    if game_type == "matching":
        if stats.best_matching_time is None or time_spent < stats.best_matching_time:
            stats.best_matching_time = time_spent  # type: ignore[assignment]

    db.commit()

    # Conceder XP e verificar conquistas
    xp_info = award_xp(db, user_id, base_xp)

    return {
        **xp_info,
        "game_stats_updated": True
    }


def update_word_stats(db: Session, user_id: int, word_learned: bool = False) -> None:
    """
    Atualiza estatísticas de palavras.
    """
    stats = get_or_create_stats(db, user_id)

    if word_learned:
        stats.words_learned += 1  # type: ignore[assignment]

    stats.total_reviews += 1  # type: ignore[assignment]

    db.commit()

    # Verificar conquistas
    check_and_unlock_achievements(db, user_id)
