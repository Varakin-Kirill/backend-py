from typing import Annotated, List, TYPE_CHECKING, Optional
from sqlalchemy import JSON, Column
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select, Relationship
# from .book import BookPublic

if TYPE_CHECKING:
    from .book import BookPublic

class AuthorBase(SQLModel):
    name: str
    surname: str

class Author(AuthorBase, table=True):
    author_id: int | None = Field(default=None, primary_key=True)
    description: str
    books: List["Book"] = Relationship(back_populates="author")

    
class AuthorPublic(AuthorBase):
    pass

class AuthorWithBooks(AuthorPublic):
    # pass
    author_id: int
    description: str
    # books: list["BookPublic"] = None


class AuthorCreate(AuthorBase):
    description: str

class AuthorUpdate(AuthorBase):
    name: str | None = None
    surname: str | None = None
    description: str | None = None