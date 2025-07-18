from typing import Annotated
from sqlalchemy import JSON, Column
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select

class ReadingBase(SQLModel):
    book_id: int | None = Field(default=None, foreign_key="book.book_id")
    user_id: int | None = Field(default=None, foreign_key="user.user_id")

class Author(ReadingBase, table=True):
    reading_id: int | None = Field(default=None, primary_key=True)

class AuthorPublic(ReadingBase):
    offset: int

class AuthorCreate(ReadingBase):
    offset: str

class AuthorUpdate(ReadingBase):
    offset: int | None = None