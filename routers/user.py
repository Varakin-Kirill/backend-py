from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from typing import Annotated
from ..models.user import User, UserPublic, UserCreate, UserUpdate
from ..deps import get_session

router = APIRouter(
    prefix="/user",
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=UserPublic)
def create_user(user: UserCreate, session: Session = Depends(get_session)):
    db_user = User.model_validate(user)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

@router.patch("/{user_id}", response_model=UserPublic)
def update_hero(user_id: int, hero: UserUpdate, session: Session = Depends(get_session)):
    user_db = session.get(User, user_id)
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")
    user_data = hero.model_dump(exclude_unset=True)
    user_db.sqlmodel_update(user_data)
    session.add(user_db)
    session.commit()
    session.refresh(user_db)
    return user_db