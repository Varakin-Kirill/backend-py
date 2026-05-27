from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from deps import get_session
from models.achievement import Achievement, UserAchievement, UserAchievementPublic
from models.user import User
from models.user_stats import UserReadingStatsPublic
from routers.auth import get_current_active_user
from services.gamification import build_achievement_public, get_or_create_stats

router = APIRouter(
    prefix="/achievement",
    tags=["achievement"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=list[UserAchievementPublic])
def list_achievements_with_progress(
    user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    achievements = session.exec(select(Achievement)).all()
    result = []
    for a in achievements:
        ua = session.exec(
            select(UserAchievement).where(
                UserAchievement.user_id == user.user_id,
                UserAchievement.achievement_id == a.achievement_id,
            )
        ).first()
        result.append(UserAchievementPublic(**build_achievement_public(a, ua)))
    return result


@router.get("/stats", response_model=UserReadingStatsPublic)
def get_reading_stats(
    user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    stats = get_or_create_stats(session, user.user_id)
    return UserReadingStatsPublic(
        user_id=stats.user_id,
        current_streak_days=stats.current_streak_days,
        longest_streak_days=stats.longest_streak_days,
        last_reading_date=stats.last_reading_date,
        total_fragments_read=stats.total_fragments_read,
        total_chars_read=stats.total_chars_read,
        books_completed=stats.books_completed,
        quiz_correct_total=stats.quiz_correct_total,
    )
