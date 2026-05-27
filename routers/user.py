from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, or_, select

from deps import get_session
from models.user import User, UserCreate, UserPublic
from routers.auth import (
    ACCESS_TOKEN_EXPIRE_DAYS,
    Token,
    authenticate_user,
    create_access_token,
    get_current_active_user,
    get_password_hash,
)

router = APIRouter(
    prefix="/user",
    tags=["user"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=UserPublic)
def create_user(
    user: UserCreate,
    session: Session = Depends(get_session),
):
    existing_user = session.exec(
        select(User).where(or_(User.login == user.login, User.email == user.email))
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="User with this login or email already exists",
        )

    new_user = User(
        name=user.name,
        email=user.email,
        login=user.login,
        password=get_password_hash(user.password),
    )

    session.add(new_user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=400,
            detail="User with this login or email already exists",
        )
    session.refresh(new_user)
    return new_user


@router.post("/login")
async def login_for_access_token(
    login: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Session = Depends(get_session),
) -> Token:
    user = session.exec(
        select(User).where(or_(User.login == login.username, User.email == login.username))
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
        data={"login": user.login, "user_id": user.user_id},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/", response_model=UserPublic)
def get_user(user: Annotated[User, Depends(get_current_active_user)]):
    return user
