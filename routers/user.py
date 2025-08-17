from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import Annotated
from models.user import User, UserPublic, UserCreate, UserUpdate
from deps import get_session
from routers.auth import validate_init_data

router = APIRouter(
    prefix="/user",
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=UserPublic)
def create_user(user: UserCreate, session: Session = Depends(get_session), tg_user: dict = Depends(validate_init_data)):
    
    existing_user = session.exec(
        select(User).where(User.tg_id == tg_user["id"])
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="User with this Telegram ID already exists"
        )
        
    new_user = User(
        name=tg_user["first_name"],
        login=tg_user["username"],
        password="EXAMPLE", #!!!!!ЗАМЕНИТЬ!!!!
        tg_id=tg_user["id"]
    )
 
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user

#Пока не нужен
# @router.patch("/{user_id}", response_model=UserPublic)
# def update_hero(user_id: int, hero: UserUpdate, session: Session = Depends(get_session), tg_user: dict = Depends(validate_init_data)):
    
#     existing_user = session.exec(
#         select(User).where(User.tg_id == tg_user["id"])
#     ).first()
    
#     if existing_user:
#         raise HTTPException(
#             status_code=400,
#             detail="User with this Telegram ID not exist"
#         )
    
    
#     user_db = session.get(User, user_id)
#     if not user_id:
#         raise HTTPException(status_code=404, detail="User not found")
#     user_data = hero.model_dump(exclude_unset=True)
#     user_db.sqlmodel_update(user_data)
#     session.add(user_db)
#     session.commit()
#     session.refresh(user_db)
#     return user_db


@router.get("/", response_model=User)
def get_user(session: Session = Depends(get_session), tg_user: dict = Depends(validate_init_data)):
    
    print(tg_user)
    tg_id = tg_user["id"]
    
    user = session.exec(select(User).where(User.tg_id == tg_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user
    
