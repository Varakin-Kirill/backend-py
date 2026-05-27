from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Session

from deps import engine
from models import (  # noqa: F401 - register tables in SQLModel metadata
    Achievement,
    Author,
    Book,
    QuizAttempt,
    QuizOption,
    QuizQuestion,
    Reading,
    User,
    UserAchievement,
    UserReadingStats,
)
from routers import achievement, author, book, quiz, reading, user
from services.gamification import seed_achievements
from services.quiz_seed import seed_demo_quiz_questions

app = FastAPI(title="ABZAC API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081",
        "http://127.0.0.1:8081",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router)
app.include_router(book.router)
app.include_router(author.router)
app.include_router(reading.router)
app.include_router(achievement.router)
app.include_router(quiz.router)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    with Session(engine) as session:
        seed_achievements(session)
        seed_demo_quiz_questions(session)


@app.get("/health")
async def health():
    return "OK"
