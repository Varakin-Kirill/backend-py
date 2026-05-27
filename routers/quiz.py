from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from deps import get_session
from models.quiz import (
    QuizQuestion,
    QuizOption,
    QuizQuestionCreate,
    QuizSubmitRequest,
    QuizSubmitResponse,
    QuizQuestionPublic,
)
from models.user import User
from routers.auth import get_current_active_user
from services.quiz import get_questions_for_position, submit_answers

router = APIRouter(
    prefix="/quiz",
    tags=["quiz"],
    responses={404: {"description": "Not found"}},
)


@router.get("/book/{book_id}/questions", response_model=list[QuizQuestionPublic])
def get_quiz_questions(
    book_id: int,
    user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
    chapter: int = Query(0, ge=0),
    current_paragraph: int = Query(0, ge=0),
    limit: Annotated[int, Query(le=10)] = 5,
):
    return get_questions_for_position(
        session, book_id, chapter, current_paragraph, limit=limit
    )


@router.post("/book/{book_id}/questions", response_model=QuizQuestionPublic)
def create_quiz_question(
    book_id: int,
    body: QuizQuestionCreate,
    user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    """Добавление вопроса в банк (для наполнения каталога самопроверки)."""
    if body.book_id != book_id:
        raise HTTPException(status_code=400, detail="book_id в теле и в URL должны совпадать")
    q = QuizQuestion(**body.model_dump(exclude={"options"}))
    session.add(q)
    session.commit()
    session.refresh(q)
    for opt in body.options:
        session.add(
            QuizOption(
                question_id=q.question_id,
                option_text=opt.option_text,
                is_correct=opt.is_correct,
            )
        )
    session.commit()
    items = get_questions_for_position(
        session, book_id, body.chapter or 0, body.paragraph_from or 0, limit=1
    )
    return items[0] if items else QuizQuestionPublic(
        question_id=q.question_id,
        question_text=q.question_text,
        question_type=q.question_type,
        options=[],
    )


@router.post("/book/{book_id}/submit", response_model=QuizSubmitResponse)
def submit_quiz(
    book_id: int,
    body: QuizSubmitRequest,
    user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    if not body.answers:
        raise HTTPException(status_code=400, detail="Список ответов пуст")
    return submit_answers(
        session=session,
        user_id=user.user_id,
        book_id=book_id,
        reading_id=body.reading_id,
        chapter=body.chapter,
        current_paragraph=body.current_paragraph,
        paragraph_offset=body.paragraph_offset,
        answers=body.answers,
    )
