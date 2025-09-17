from typing import Annotated, List, TYPE_CHECKING
from sqlalchemy import JSON, Column
from models.achievement import Achievement
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select, Relationship
from models.achievement import UsersToAchievements
if TYPE_CHECKING:
    from models.achievement import Achievement

class UserBase(SQLModel):
    name: str
    login: str
    email: str
    password: str
    
class User(UserBase, table=True):
    user_id: int | None = Field(default=None, primary_key=True)
    achievements: List['Achievement'] | None = Relationship(back_populates="users", link_model=UsersToAchievements)

class UserPublic(UserBase):
    user_id: int

class UserCreate(UserBase):
    pass

class UserUpdate(UserBase):
    name: str | None = None
    password: str | None = None