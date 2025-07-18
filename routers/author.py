from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from typing import Annotated
from ..models.author import Author, AuthorPublic, AuthorCreate, AuthorWithBooks
from ..deps import get_session

router = APIRouter(
    prefix="/author",
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=AuthorPublic)
def create_author(author: AuthorCreate, session: Session = Depends(get_session)):
    db_author = Author.model_validate(author)
    session.add(db_author)
    session.commit()
    session.refresh(db_author)
    return db_author


@router.get("/", response_model=list[AuthorWithBooks])
def get_authors(
    session: Session = Depends(get_session),
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
):
    authors = session.exec(select(Author).offset(offset).limit(limit)).all()
    return authors

@router.get("/{author_id}", response_model=AuthorWithBooks)
def get_author(author_id: int, session: Session = Depends(get_session)):
    author = session.get(Author, author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    return author