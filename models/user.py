from typing import Annotated
from sqlalchemy import JSON, Column
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select

class UserBase(SQLModel):
    name: str
    login: str
    password: str

class User(UserBase, table=True):
    user_id: int | None = Field(default=None, primary_key=True)
    tg_id: int | None = Field(default=None)

class UserPublic(UserBase):
    user_id: int

class UserCreate(UserBase):
    tg_id: int | None

class UserUpdate(UserBase):
    name: str | None = None
    password: str | None = None