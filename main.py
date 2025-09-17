from fastapi import Depends, FastAPI, HTTPException, Query
from typing import Annotated
from sqlmodel import Field, Session, SQLModel, create_engine, select
from routers import book, user, author
from deps import engine
# from models import User, Author, Book, Reading

app = FastAPI()

app.include_router(user.router)
app.include_router(book.router)
app.include_router(author.router)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# def get_session():
#     with Session(engine) as session:
#         yield session

# SessionDep = Annotated[Session, Depends(get_session)]

@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/health")
async def root():
    return "OK"




# @app.get("/user/{hero_id}", response_model=HeroPublic)
# def read_hero(hero_id: int, session: SessionDep):
#     hero = session.get(Hero, hero_id)
#     if not hero:
#         raise HTTPException(status_code=404, detail="Hero not found")
#     return hero


# 1. User 
# get by login returning jwt
# get stats for user
# update password + name

# 2. Authors
# Get all
# Get one with list of books

# 3. Books
# Get all
# Get one
# Upload?

# 4. Readings
# Start read (create)
# Get (book_id + user_id)
# Update 

# 5. Search
# Get