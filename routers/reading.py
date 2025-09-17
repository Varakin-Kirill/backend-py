from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import Annotated
from deps import get_session
from models.reading import ReadingPublic, ReadingCreate, Reading, ReadingUpdate
from routers.auth import validate_init_data

router = APIRouter(
    prefix="/reading",
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=ReadingPublic)
def create_reading(reading: ReadingCreate, session: Session = Depends(get_session)):
    db_reading = Reading.model_validate(reading)
    session.add(db_reading)
    session.commit()
    session.refresh(db_reading)
    return db_reading


@router.get("/", response_model=list[ReadingPublic])
def get_reading(
    session: Session = Depends(get_session),
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
):
    readings = session.exec(select(Reading).offset(offset).limit(limit)).all()
    return readings

@router.get("/{reading_id}", response_model=ReadingPublic)
def get_reading(reading_id: int, session: Session = Depends(get_session)):
    reading = session.get(Reading, reading_id)
    if not reading:
        raise HTTPException(status_code=404, detail="Reading not found")
    return reading

@router.get("/{book_id}", response_model=ReadingPublic)
def get_reading(book_id: int, session: Session = Depends(get_session), tg_user: dict = Depends(validate_init_data)):
    reading = session.get(Reading, book_id, tg_user["id"])
    if not reading:
        raise HTTPException(status_code=404, detail="Reading not found")
    return reading