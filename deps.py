import os

from dotenv import load_dotenv
from sqlmodel import Session, create_engine

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:admin@localhost:5432/Abzac",
)

engine = create_engine(DATABASE_URL)


def get_session():
    with Session(engine) as session:
        yield session
