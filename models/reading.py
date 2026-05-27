from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class ReadingBase(SQLModel):
    book_id: int = Field(foreign_key="book.book_id")
    user_id: int = Field(foreign_key="user.user_id")


class Reading(ReadingBase, table=True):
    __table_args__ = (UniqueConstraint("book_id", "user_id", name="uq_reading_book_user"),)

    reading_id: int | None = Field(default=None, primary_key=True)
    current_chapter: int = 0
    current_paragraph: int = 0
    paragraph_offset: int = 0
    prev_chars_read: int = 0
    total_chars_read: int = 0
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_completed: bool = False


class ReadingCreate(ReadingBase):
    current_chapter: int = 0
    current_paragraph: int = 0
    paragraph_offset: int = 0
    prev_chars_read: int = 0
    total_chars_read: int = 0
    updated_at: datetime | None = None
    is_completed: bool = False


class ReadingPublic(ReadingBase):
    reading_id: int
    current_chapter: int = 0
    current_paragraph: int = 0
    paragraph_offset: int = 0
    prev_chars_read: int = 0
    total_chars_read: int = 0
    updated_at: datetime
    is_completed: bool = False


class ReadingUpdate(SQLModel):
    current_chapter: int | None = None
    current_paragraph: int | None = None
    paragraph_offset: int | None = None
    prev_chars_read: int | None = None
    total_chars_read: int | None = None
    updated_at: datetime | None = None
    is_completed: bool | None = None
