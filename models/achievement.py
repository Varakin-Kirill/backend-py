from sqlalchemy import JSON, Column
from fastapi import Depends, FastAPI, HTTPException, Query
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON, ARRAY, Integer
from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlmodel import Field, Session, SQLModel, create_engine, DateTime, select, Relationship


if TYPE_CHECKING:
    from models.user import User    
    

class AchievementBase(SQLModel):
    name: str
    image_url: str
    description: str
    

class UsersToAchievements(SQLModel, table=True):
    user_id: int | None = Field(default=None, foreign_key="user.user_id", primary_key=True)
    achievement_id: int | None = Field(default=None, foreign_key="achievement.achievement_id", primary_key=True)
    last_claimed_index: int
    current_counter_value: int

class Achievement(AchievementBase, table=True):
    achievement_id: int | None = Field(default=None, primary_key=True)
    name: str
    image_url: str
    description: str
    counter_level: List[int] = Field(sa_column=Column(ARRAY(Integer)))
    expiring_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True))
    )
    starting_from: datetime = Field(
        sa_column=Column(DateTime(timezone=True))
    )
    users: List["User"] | None = Relationship(back_populates="achievements", link_model=UsersToAchievements)
