from datetime import date, datetime, timezone

from sqlmodel import Session, select

from models.achievement import (
    Achievement,
    AchievementMetric,
    UserAchievement,
)
from models.user_stats import UserReadingStats

DEFAULT_ACHIEVEMENTS: list[dict] = [
    {
        "code": "first_fragment",
        "name": "Первый абзац",
        "description": "Прочитайте первый фрагмент текста",
        "image_url": "",
        "metric": AchievementMetric.FRAGMENTS_READ,
        "counter_levels": [1],
    },
    {
        "code": "chars_reader",
        "name": "Читатель",
        "description": "Накопите объём прочитанных символов",
        "image_url": "",
        "metric": AchievementMetric.CHARS_READ,
        "counter_levels": [1000, 5000, 10000, 50000],
    },
    {
        "code": "reading_streak",
        "name": "Серия дней",
        "description": "Читайте несколько дней подряд",
        "image_url": "",
        "metric": AchievementMetric.READING_STREAK,
        "counter_levels": [3, 7, 14, 30],
    },
    {
        "code": "book_finished",
        "name": "Книголюб",
        "description": "Дочитайте книги до конца",
        "image_url": "",
        "metric": AchievementMetric.BOOKS_COMPLETED,
        "counter_levels": [1, 3, 5],
    },
    {
        "code": "quiz_master",
        "name": "Знаток",
        "description": "Дайте верные ответы в самопроверке",
        "image_url": "",
        "metric": AchievementMetric.QUIZ_CORRECT,
        "counter_levels": [5, 20, 50],
    },
]


def seed_achievements(session: Session) -> None:
    for item in DEFAULT_ACHIEVEMENTS:
        exists = session.exec(
            select(Achievement).where(Achievement.code == item["code"])
        ).first()
        if exists:
            continue
        session.add(Achievement(**item))
    session.commit()


def get_or_create_stats(session: Session, user_id: int) -> UserReadingStats:
    stats = session.get(UserReadingStats, user_id)
    if stats:
        return stats
    stats = UserReadingStats(user_id=user_id, updated_at=datetime.now(timezone.utc))
    session.add(stats)
    session.commit()
    session.refresh(stats)
    return stats


def _update_streak(stats: UserReadingStats, today: date) -> None:
    last = stats.last_reading_date
    if last is None:
        stats.current_streak_days = 1
    elif last == today:
        pass
    elif (today - last).days == 1:
        stats.current_streak_days += 1
    else:
        stats.current_streak_days = 1

    stats.last_reading_date = today
    if stats.current_streak_days > stats.longest_streak_days:
        stats.longest_streak_days = stats.current_streak_days


def _metric_value(stats: UserReadingStats, metric: AchievementMetric) -> int:
    mapping = {
        AchievementMetric.CHARS_READ: stats.total_chars_read,
        AchievementMetric.FRAGMENTS_READ: stats.total_fragments_read,
        AchievementMetric.BOOKS_COMPLETED: stats.books_completed,
        AchievementMetric.READING_STREAK: stats.current_streak_days,
        AchievementMetric.QUIZ_CORRECT: stats.quiz_correct_total,
    }
    return mapping[metric]


def _sync_user_achievements(
    session: Session,
    user_id: int,
    metric: AchievementMetric,
    value: int,
) -> list[dict]:
    """Обновляет прогресс по всем достижениям с данной метрикой. Возвращает новые уровни."""
    now = datetime.now(timezone.utc)
    newly_claimed: list[dict] = []

    achievements = session.exec(
        select(Achievement).where(Achievement.metric == metric)
    ).all()

    for achievement in achievements:
        if achievement.starting_from and now < achievement.starting_from:
            continue
        if achievement.expiring_at and now > achievement.expiring_at:
            continue

        ua = session.exec(
            select(UserAchievement).where(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement.achievement_id,
            )
        ).first()
        if not ua:
            ua = UserAchievement(
                user_id=user_id,
                achievement_id=achievement.achievement_id,
                current_value=0,
                last_claimed_level_index=-1,
                updated_at=now,
            )
            session.add(ua)

        ua.current_value = value
        ua.updated_at = now

        levels = achievement.counter_levels or []
        for idx, threshold in enumerate(levels):
            if value >= threshold and idx > ua.last_claimed_level_index:
                ua.last_claimed_level_index = idx
                newly_claimed.append(
                    {
                        "code": achievement.code,
                        "name": achievement.name,
                        "level_index": idx,
                        "threshold": threshold,
                    }
                )

    return newly_claimed


def record_reading_session(
    session: Session,
    user_id: int,
    chars_delta: int,
    book_just_completed: bool,
) -> tuple[UserReadingStats, list[dict]]:
    """
    Вызывается после GET /book/{id}/read.
    Обновляет стрики, счётчики и достижения.
    """
    stats = get_or_create_stats(session, user_id)
    today = date.today()

    _update_streak(stats, today)
    stats.total_fragments_read += 1
    stats.total_chars_read += max(0, chars_delta)

    if book_just_completed:
        stats.books_completed += 1

    stats.updated_at = datetime.now(timezone.utc)
    session.add(stats)

    claimed: list[dict] = []
    claimed.extend(
        _sync_user_achievements(
            session, user_id, AchievementMetric.FRAGMENTS_READ, stats.total_fragments_read
        )
    )
    claimed.extend(
        _sync_user_achievements(
            session, user_id, AchievementMetric.CHARS_READ, stats.total_chars_read
        )
    )
    claimed.extend(
        _sync_user_achievements(
            session, user_id, AchievementMetric.READING_STREAK, stats.current_streak_days
        )
    )
    if book_just_completed:
        claimed.extend(
            _sync_user_achievements(
                session, user_id, AchievementMetric.BOOKS_COMPLETED, stats.books_completed
            )
        )

    session.commit()
    session.refresh(stats)
    return stats, claimed


def record_quiz_correct(session: Session, user_id: int, correct_count: int) -> list[dict]:
    stats = get_or_create_stats(session, user_id)
    stats.quiz_correct_total += correct_count
    stats.updated_at = datetime.now(timezone.utc)
    session.add(stats)
    claimed = _sync_user_achievements(
        session,
        user_id,
        AchievementMetric.QUIZ_CORRECT,
        stats.quiz_correct_total,
    )
    session.commit()
    return claimed


def build_achievement_public(
    achievement: Achievement, ua: UserAchievement | None
) -> dict:
    levels = achievement.counter_levels or []
    current = ua.current_value if ua else 0
    claimed_idx = ua.last_claimed_level_index if ua else -1
    next_threshold = None
    for threshold in levels:
        if current < threshold:
            next_threshold = threshold
            break

    return {
        "achievement_id": achievement.achievement_id,
        "code": achievement.code,
        "name": achievement.name,
        "description": achievement.description,
        "image_url": achievement.image_url,
        "metric": achievement.metric,
        "counter_levels": levels,
        "current_value": current,
        "last_claimed_level_index": claimed_idx,
        "next_threshold": next_threshold,
        "levels_claimed": claimed_idx + 1 if claimed_idx >= 0 else 0,
        "levels_total": len(levels),
    }
