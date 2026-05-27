from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.book import Book


class QuizQuestionType(str, Enum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    SHORT_ANSWER = "short_answer"


class QuizQuestionBase(SQLModel):
    book_id: int = Field(foreign_key="book.book_id")
    chapter: int | None = Field(
        default=None,
        description="Р“Р»Р°РІР°; NULL вЂ” РІРѕРїСЂРѕСЃ РЅР° РІСЃСЋ РєРЅРёРіСѓ",
    )
    paragraph_from: int | None = Field(
        default=None,
        description="РќР°С‡Р°Р»СЊРЅС‹Р№ Р°Р±Р·Р°С† РґРёР°РїР°Р·РѕРЅР° (РІРєР»СЋС‡РёС‚РµР»СЊРЅРѕ)",
    )
    paragraph_to: int | None = Field(
        default=None,
        description="РљРѕРЅРµС‡РЅС‹Р№ Р°Р±Р·Р°С† РґРёР°РїР°Р·РѕРЅР° (РІРєР»СЋС‡РёС‚РµР»СЊРЅРѕ)",
    )
    question_text: str
    question_type: QuizQuestionType = QuizQuestionType.SINGLE_CHOICE
    correct_answer_text: str | None = Field(
        default=None,
        description="Р­С‚Р°Р»РѕРЅ РґР»СЏ short_answer (Р±РµР· СѓС‡С‘С‚Р° СЂРµРіРёСЃС‚СЂР°)",
    )
    explanation: str | None = None


class QuizQuestion(QuizQuestionBase, table=True):
    __tablename__ = "quiz_question"

    question_id: int | None = Field(default=None, primary_key=True)
    options: List["QuizOption"] = Relationship(back_populates="question")


class QuizOption(SQLModel, table=True):
    __tablename__ = "quiz_option"

    option_id: int | None = Field(default=None, primary_key=True)
    question_id: int = Field(foreign_key="quiz_question.question_id")
    option_text: str
    is_correct: bool = Field(default=False)
    question: QuizQuestion | None = Relationship(back_populates="options")


class QuizAttempt(SQLModel, table=True):
    __tablename__ = "quiz_attempt"

    attempt_id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.user_id")
    book_id: int = Field(foreign_key="book.book_id")
    reading_id: int | None = Field(default=None, foreign_key="reading.reading_id")
    question_id: int = Field(foreign_key="quiz_question.question_id")
    option_id: int | None = Field(default=None, foreign_key="quiz_option.option_id")
    answer_text: str | None = None
    is_correct: bool
    chapter: int = 0
    current_paragraph: int = 0
    paragraph_offset: int = 0
    answered_at: datetime = Field(default_factory=datetime.utcnow)


class QuizOptionPublic(SQLModel):
    option_id: int
    option_text: str


class QuizQuestionPublic(SQLModel):
    question_id: int
    question_text: str
    question_type: QuizQuestionType
    options: List[QuizOptionPublic] = Field(default_factory=list)


class QuizAnswerSubmit(SQLModel):
    question_id: int
    option_id: int | None = None
    answer_text: str | None = None


class QuizSubmitRequest(SQLModel):
    reading_id: int | None = None
    chapter: int
    current_paragraph: int
    paragraph_offset: int = 0
    answers: List[QuizAnswerSubmit]


class QuizAnswerResult(SQLModel):
    question_id: int
    is_correct: bool
    explanation: str | None = None


class QuizSubmitResponse(SQLModel):
    total: int
    correct: int
    results: List[QuizAnswerResult]
    score_percent: float
    new_achievements: List[dict] = Field(default_factory=list)


class QuizOptionCreate(SQLModel):
    option_text: str
    is_correct: bool = False


class QuizQuestionCreate(QuizQuestionBase):
    options: List[QuizOptionCreate] = Field(default_factory=list)



