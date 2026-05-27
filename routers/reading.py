from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from typing import Annotated

from deps import get_session
from models.reading import Reading, ReadingCreate, ReadingPublic
from models.user import User
from routers.auth import get_current_active_user

router = APIRouter(
    prefix="/reading",
    tags=["reading"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=ReadingPublic)
def create_reading(
    reading: ReadingCreate,
    user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    existing = session.exec(
        select(Reading)
        .where(Reading.book_id == reading.book_id)
        .where(Reading.user_id == user.user_id)
    ).first()
    if existing:
        return existing

    db_reading = Reading.model_validate(
        reading,
        update={"user_id": user.user_id},
    )
    session.add(db_reading)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.exec(
            select(Reading)
            .where(Reading.book_id == reading.book_id)
            .where(Reading.user_id == user.user_id)
        ).first()
        if existing:
            return existing
        raise
    session.refresh(db_reading)
    return db_reading


@router.get("/", response_model=list[ReadingPublic])
def get_readings(
    user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
):
    return session.exec(
        select(Reading)
        .where(Reading.user_id == user.user_id)
        .offset(offset)
        .limit(limit)
    ).all()


@router.get("/{reading_id}", response_model=ReadingPublic)
def get_reading(
    reading_id: int,
    user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    reading = session.get(Reading, reading_id)
    if not reading or reading.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Reading not found")
    return reading
