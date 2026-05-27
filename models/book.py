from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .author import Author


class BookBase(SQLModel):
    name: str
    description: str
    meta: dict = Field(sa_column=Column(JSON), default_factory=dict)
    author_id: int | None = Field(default=None, foreign_key="author.author_id")
    genre: str
    book_path: str


class Book(BookBase, table=True):
    book_id: int | None = Field(default=None, primary_key=True)
    author: Optional["Author"] = Relationship(back_populates="books")


class BookPublic(BookBase):
    book_id: int


class BookWithAuthor(BookPublic):
    author: Optional["AuthorPublic"] | None = None


class BookCreate(BookBase):
    pass


class BookUpdate(SQLModel):
    name: str | None = None
    meta: dict | None = None
    description: str | None = None
    genre: str | None = None
    book_path: str | None = None
    author_id: int | None = None


from .author import AuthorPublic

BookWithAuthor.model_rebuild()
