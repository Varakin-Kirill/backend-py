from typing import Annotated
from sqlalchemy import JSON, Column
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select


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
    offset: int

# class Achievment(SQLModel, table=True):
#     reading_id: int | None = Field(default=None, primary_key=True)
#     book_id: int | None = Field(default=None, foreign_key="book.book_id")
#     user_id: int | None = Field(default=None, foreign_key="user.user_id")
#     offset: int



    

