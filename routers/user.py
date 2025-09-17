from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import Annotated
from models.user import User, UserPublic, UserCreate
from deps import get_session
from fastapi.security import OAuth2PasswordRequestForm
from routers.auth import get_password_hash, authenticate_user, create_access_token, ACCESS_TOKEN_EXPIRE_DAYS, Token, get_current_active_user
from datetime import timedelta

router = APIRouter(
    prefix="/user",
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=UserPublic)
def create_user(
    user: UserCreate, 
    session: Session = Depends(get_session), 
):
    existing_user = session.exec(
        select(User).where(User.login == user.login)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="User with this login already exists"
        )
        
    new_user = User(
        name=user.name,
        email=user.email,
        login=user.login,
        password=get_password_hash(user.password),
    )
 
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user

@router.post("/login")
async def login_for_access_token(
    login: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Session = Depends(get_session), 
) -> Token:
    user = session.exec(
        # Maybe add email OR login
        select(User).where(User.login == login.username)
    ).first()
    user = authenticate_user(user, login.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    access_token = create_access_token(
        data={"login": user.login, "user_id": user.user_id}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")



@router.get("/", response_model=User)
def get_user(user: Annotated[User, Depends(get_current_active_user)]):
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user
    
