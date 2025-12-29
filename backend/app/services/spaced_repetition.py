from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.progress import UserProgress


def calculate_next_review(difficulty: str, progress: UserProgress) -> tuple[datetime, int, float, int]:
    """Calcula próxima revisão usando um modelo inspirado no SM-2.

    Retorna: (next_review_date, new_interval_days, new_ease_factor, new_repetitions)
    """
    now = datetime.now(timezone.utc)
    ease = float(progress.ease_factor or 2.5)
    interval_days = max(progress.interval or 0, 0)
    repetitions = progress.repetitions or 0

    if difficulty == "hard":
        repetitions = 0
        ease = max(1.3, ease - 0.3)
        interval_days = 0
        next_review = now + timedelta(hours=4)
    elif difficulty == "medium":
        repetitions += 1
        ease = max(1.3, ease - 0.05)
        if repetitions <= 1:
            interval_days = 1
        else:
            interval_days = max(1, round(max(interval_days, 1) * ease))
        next_review = now + timedelta(days=interval_days)
    else:  # easy
        repetitions += 1
        ease = min(2.6, ease + 0.1)
        if repetitions == 1:
            interval_days = 1
        elif repetitions == 2:
            interval_days = 3
        else:
            interval_days = max(3, round(max(interval_days, 1) * ease * 1.2))
        next_review = now + timedelta(days=interval_days)

    return next_review, interval_days, ease, repetitions
