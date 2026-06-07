from datetime import datetime

from sqlmodel import Field, SQLModel


class UserBookFavorite(SQLModel, table=True):
    __tablename__ = "user_book_favorite"

    user_id: int = Field(foreign_key="user.user_id", primary_key=True)
    book_id: int = Field(foreign_key="book.book_id", primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FavoriteStatus(SQLModel):
    book_id: int
    is_favorite: bool
