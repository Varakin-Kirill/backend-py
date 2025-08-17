from typing import Annotated, TYPE_CHECKING, Optional
from sqlalchemy import JSON, Column
from fastapi import Depends, FastAPI, HTTPException, Query
# from models.author import Author, AuthorPublic
from sqlmodel import Field, Session, SQLModel, create_engine, select, Relationship

if TYPE_CHECKING:
    from .author import AuthorPublic, Author

class BookBase(SQLModel):
    name: str
    description: str
    meta: dict = Field(sa_column=Column(JSON), default_factory=dict)
    author_id: int | None = Field(default=None, foreign_key="author.author_id")
    genre: str
    book_path: str

class Book(BookBase, table=True):
    book_id: int | None = Field(default=None, primary_key=True)
    author:Optional["Author"] = Relationship(back_populates="books")
    # author_id: int | None = Field(default=None, foreign_key="author.author_id")

class BookPublic(BookBase):
    pass
    # book_id: int
    # author: AuthorPublic = Relationship(back_populates="book")

class BookWithAuthor(BookPublic):
    author: Optional["AuthorPublic"] | None = None
    # author: AuthorPublic = Relationship(back_populates="book")


class BookCreate(BookBase):
    pass
    # author_id: int

class BookUpdate(BookBase):
    name: str | None = None
    meta: dict | None = None
    description: str | None = None
    genre: str | None = None
    book_path: str | None = None
    author_id: int | None = None
    
    
from .author import AuthorPublic  # Импорт после объявления BookWithAuthor
BookWithAuthor.model_rebuild()