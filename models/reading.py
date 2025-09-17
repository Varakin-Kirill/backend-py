from typing import Annotated, Optional
from sqlalchemy import JSON, Column
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select
from datetime import datetime


class ReadingBase(SQLModel):
    book_id: int | None = Field(default=None, foreign_key="book.book_id")
    user_id: int | None = Field(default=None, foreign_key="user.user_id")

class Reading(ReadingBase, table=True):
    reading_id: int | None = Field(default=None, primary_key=True)
    current_chapter: int = 0
    current_paragraph: int = 0
    paragraph_offset: int = 0
    total_chars_read: int = 0
    updated_at: datetime
    is_completed: bool = False  

class ReadingCreate(ReadingBase):
    current_chapter: int = 0
    current_paragraph: int = 0
    paragraph_offset: int = 0
    total_chars_read: int = 0
    updated_at: datetime
    is_completed: bool = False

class ReadingPublic(ReadingBase):
    reading_id: int | None = Field(default=None, primary_key=True)
    current_chapter: int = 0
    current_paragraph: int = 0
    paragraph_offset: int = 0
    total_chars_read: int = 0
    updated_at: datetime
    is_completed: bool = False  

class ReadingUpdate(SQLModel):
    current_chapter: int = 0
    current_paragraph: int = 0
    paragraph_offset: int = 0
    total_chars_read: int = 0
    updated_at: datetime
    is_completed: bool = False  