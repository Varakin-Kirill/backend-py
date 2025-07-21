from sqlmodel import Field, Session, SQLModel, create_engine, select

postgresql_url = f"postgresql://postgres:admin@localhost:5432/Abzac"

engine = create_engine(postgresql_url)

def get_session():
    with Session(engine) as session:
        yield session