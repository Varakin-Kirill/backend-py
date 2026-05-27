from datetime import date, datetime

from sqlalchemy import Column, Date
from sqlmodel import Field, SQLModel


class UserReadingStats(SQLModel, table=True):
    """Агрегаты чтения и стрики — обновляются при каждом запросе /read."""

    __tablename__ = "user_reading_stats"

    user_id: int = Field(foreign_key="user.user_id", primary_key=True)
    current_streak_days: int = Field(default=0)
    longest_streak_days: int = Field(default=0)
    last_reading_date: date | None = Field(
        default=None,
        sa_column=Column(Date, nullable=True),
    )
    total_fragments_read: int = Field(default=0)
    total_chars_read: int = Field(default=0)
    books_completed: int = Field(default=0)
    quiz_correct_total: int = Field(default=0)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserReadingStatsPublic(SQLModel):
    user_id: int
    current_streak_days: int
    longest_streak_days: int
    last_reading_date: date | None
    total_fragments_read: int
    total_chars_read: int
    books_completed: int
    quiz_correct_total: int
