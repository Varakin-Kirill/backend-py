from sqlalchemy import JSON, Column
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select, DateTime
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON, ARRAY, Integer
from datetime import datetime
from typing import List


class AchievementBase(SQLModel):
    name: str
    image_url: str
    description: str
    
    

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