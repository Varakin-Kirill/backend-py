from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.user import User


class AchievementMetric(str, Enum):
    CHARS_READ = "chars_read"
    FRAGMENTS_READ = "fragments_read"
    BOOKS_COMPLETED = "books_completed"
    READING_STREAK = "reading_streak"
    QUIZ_CORRECT = "quiz_correct"


class UserAchievement(SQLModel, table=True):
    __tablename__ = "user_achievement"

    user_id: int = Field(foreign_key="user.user_id", primary_key=True)
    achievement_id: int = Field(foreign_key="achievement.achievement_id", primary_key=True)
    current_value: int = Field(default=0)
    last_claimed_level_index: int = Field(default=-1)
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True)))


class AchievementBase(SQLModel):
    code: str = Field(index=True, unique=True)
    name: str
    description: str
    image_url: str = ""
    metric: AchievementMetric
    counter_levels: List[int] = Field(sa_column=Column(ARRAY(Integer)))


class Achievement(AchievementBase, table=True):
    achievement_id: int | None = Field(default=None, primary_key=True)
    starting_from: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    expiring_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    users: List["User"] = Relationship(
        back_populates="achievements",
        link_model=UserAchievement,
    )


class UserAchievementPublic(SQLModel):
    achievement_id: int
    code: str
    name: str
    description: str
    image_url: str
    metric: AchievementMetric
    counter_levels: List[int]
    current_value: int
    last_claimed_level_index: int
    next_threshold: int | None = None
    levels_claimed: int = 0
    levels_total: int = 0
