from typing import List

from sqlmodel import Field, Relationship, SQLModel

from models.achievement import Achievement, UserAchievement


class UserBase(SQLModel):
    name: str
    login: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)


class User(UserBase, table=True):
    user_id: int | None = Field(default=None, primary_key=True)
    tg_id: int | None = Field(default=None)
    password: str
    achievements: List[Achievement] | None = Relationship(
        back_populates="users",
        link_model=UserAchievement,
    )


class UserPublic(UserBase):
    user_id: int


class UserCreate(UserBase):
    password: str


class UserUpdate(SQLModel):
    name: str | None = None
    login: str | None = None
    email: str | None = None
    password: str | None = None
