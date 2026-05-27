from typing import List, TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .book import Book


class AuthorBase(SQLModel):
    name: str
    surname: str


class Author(AuthorBase, table=True):
    author_id: int | None = Field(default=None, primary_key=True)
    description: str
    books: List["Book"] = Relationship(back_populates="author")


class AuthorPublic(AuthorBase):
    author_id: int
    description: str


class AuthorWithBooks(AuthorPublic):
    pass


class AuthorCreate(AuthorBase):
    description: str


class AuthorUpdate(SQLModel):
    name: str | None = None
    surname: str | None = None
    description: str | None = None


from .book import BookPublic

AuthorWithBooks.model_rebuild()
