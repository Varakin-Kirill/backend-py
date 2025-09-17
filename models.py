from typing import Annotated
from sqlalchemy import JSON, Column
from fastapi import Depends, FastAPI, HTTPException, Query
from datetime import datetime, timezone
from sqlmodel import ARRAY, DateTime, Integer, SQLModel, Field



class User(SQLModel, table=True):
    user_id: int | None = Field(default=None, primary_key=True)
    tg_id: int | None = Field(default=None)
    name: str = Field(index=True)

class Author(SQLModel, table=True):
    author_id: int | None = Field(default=None, primary_key=True)
    name: str
    surname: str
    description: str

class Book(SQLModel, table=True):
    book_id: int | None = Field(default=None, primary_key=True)
    author_id: int | None = Field(default=None, foreign_key="author.author_id")
    name: str
    description: str
    meta: dict = Field(sa_column=Column(JSON), default_factory=dict)
    genre: str
    book_path: str

class Reading(SQLModel, table=True):
    reading_id: int | None = Field(default=None, primary_key=True)
    book_id: int | None = Field(default=None, foreign_key="book.book_id")
    user_id: int | None = Field(default=None, foreign_key="user.user_id")
    current_chapter: int
    current_paragraph: int
    paragraph_offset: int
    total_chars_read: int
    updated_at: datetime
    is_completed: bool = False
    
class Achievement(SQLModel, TABLE=True):
    achievement_id: int | None = Field(default=None, primary_key=True)
    name: str
    image_url: str
    description: str
    counter_level: list[int] = Field(sa_column=Column(ARRAY(Integer)))
    expiring_at: datetime= Field(
        sa_column=Column(DateTime(timezone=True))
    )
    starting_from: datetime = Field(
        sa_column=Column(DateTime(timezone=True))
    )
    # experience_rewards: [int]

# class Achievment(SQLModel, table=True):
#     reading_id: int | None = Field(default=None, primary_key=True)
#     book_id: int | None = Field(default=None, foreign_key="book.book_id")
#     user_id: int | None = Field(default=None, foreign_key="user.user_id")
#     offset: int



    

