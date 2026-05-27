from fastapi import HTTPException
from sqlmodel import Session, select

from models.quiz import (
    QuizAnswerResult,
    QuizAnswerSubmit,
    QuizAttempt,
    QuizOption,
    QuizQuestion,
    QuizQuestionPublic,
    QuizQuestionType,
    QuizOptionPublic,
    QuizSubmitResponse,
)
from models.reading import Reading
from services.gamification import record_quiz_correct


def _paragraph_in_range(
    paragraph: int,
    chapter: int,
    q_chapter: int | None,
    p_from: int | None,
    p_to: int | None,
) -> bool:
    if q_chapter is not None and q_chapter != chapter:
        return False
    if p_from is None and p_to is None:
        return True
    start = p_from if p_from is not None else 0
    end = p_to if p_to is not None else 10**9
    return start <= paragraph <= end


def get_questions_for_position(
    session: Session,
    book_id: int,
    chapter: int,
    current_paragraph: int,
    limit: int = 5,
) -> list[QuizQuestionPublic]:
    questions = session.exec(
        select(QuizQuestion).where(QuizQuestion.book_id == book_id)
    ).all()

    matched: list[QuizQuestion] = []
    for question in questions:
        if _paragraph_in_range(
            current_paragraph,
            chapter,
            question.chapter,
            question.paragraph_from,
            question.paragraph_to,
        ):
            matched.append(question)
        if len(matched) >= limit:
            break

    result: list[QuizQuestionPublic] = []
    for question in matched:
        options = session.exec(
            select(QuizOption).where(QuizOption.question_id == question.question_id)
        ).all()
        if question.question_type == QuizQuestionType.SHORT_ANSWER:
            public_options = []
        else:
            public_options = [
                QuizOptionPublic(option_id=option.option_id, option_text=option.option_text)
                for option in options
            ]
        result.append(
            QuizQuestionPublic(
                question_id=question.question_id,
                question_text=question.question_text,
                question_type=question.question_type,
                options=public_options,
            )
        )
    return result


def _check_answer(
    question: QuizQuestion,
    options: list[QuizOption],
    answer: QuizAnswerSubmit,
) -> tuple[bool, int | None]:
    if question.question_type == QuizQuestionType.SHORT_ANSWER:
        if not answer.answer_text or not question.correct_answer_text:
            return False, None
        ok = answer.answer_text.strip().lower() == question.correct_answer_text.strip().lower()
        return ok, None

    if answer.option_id is None:
        return False, None
    option = next((item for item in options if item.option_id == answer.option_id), None)
    if not option:
        return False, answer.option_id
    return option.is_correct, answer.option_id


def submit_answers(
    session: Session,
    user_id: int,
    book_id: int,
    reading_id: int | None,
    chapter: int,
    current_paragraph: int,
    paragraph_offset: int,
    answers: list[QuizAnswerSubmit],
) -> QuizSubmitResponse:
    if reading_id is not None:
        reading = session.get(Reading, reading_id)
        if not reading or reading.user_id != user_id or reading.book_id != book_id:
            raise HTTPException(status_code=400, detail="Invalid reading_id")

    results: list[QuizAnswerResult] = []
    correct_count = 0

    for answer in answers:
        question = session.get(QuizQuestion, answer.question_id)
        if not question or question.book_id != book_id:
            results.append(
                QuizAnswerResult(
                    question_id=answer.question_id,
                    is_correct=False,
                    explanation="Вопрос не найден",
                )
            )
            continue

        options = session.exec(
            select(QuizOption).where(QuizOption.question_id == question.question_id)
        ).all()
        is_correct, option_id = _check_answer(question, options, answer)
        if is_correct:
            correct_count += 1

        session.add(
            QuizAttempt(
                user_id=user_id,
                book_id=book_id,
                reading_id=reading_id,
                question_id=question.question_id,
                option_id=option_id,
                answer_text=answer.answer_text,
                is_correct=is_correct,
                chapter=chapter,
                current_paragraph=current_paragraph,
                paragraph_offset=paragraph_offset,
            )
        )
        results.append(
            QuizAnswerResult(
                question_id=question.question_id,
                is_correct=is_correct,
                explanation=question.explanation if not is_correct else None,
            )
        )

    session.commit()
    new_achievements = []
    if correct_count:
        new_achievements = record_quiz_correct(session, user_id, correct_count)

    total = len(results)
    score = round((correct_count / total) * 100, 1) if total else 0.0
    return QuizSubmitResponse(
        total=total,
        correct=correct_count,
        results=results,
        score_percent=score,
        new_achievements=new_achievements,
    )
