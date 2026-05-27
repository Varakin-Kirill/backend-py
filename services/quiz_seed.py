from sqlmodel import Session, select

from models.book import Book
from models.quiz import QuizOption, QuizQuestion, QuizQuestionType

DEMO_BOOK_ID = 135

DEMO_QUESTIONS = [
    {
        "chapter": 1,
        "paragraph_from": 0,
        "paragraph_to": 25,
        "question_text": "В каком году происходят события, упоминаемые в начале фрагмента?",
        "question_type": QuizQuestionType.SINGLE_CHOICE,
        "explanation": "В начале фрагмента говорится о событиях 1572 года.",
        "options": [
            ("1572", True),
            ("1812", False),
            ("1492", False),
            ("1613", False),
        ],
    },
    {
        "chapter": 1,
        "paragraph_from": 0,
        "paragraph_to": 25,
        "question_text": "Какое историческое событие является важным фоном начала повествования?",
        "question_type": QuizQuestionType.SINGLE_CHOICE,
        "explanation": "Фрагмент связан с напряженной исторической обстановкой вокруг Варфоломеевской ночи.",
        "options": [
            ("Варфоломеевская ночь", True),
            ("Отечественная война", False),
            ("Крещение Руси", False),
            ("Петровские реформы", False),
        ],
    },
    {
        "chapter": 1,
        "paragraph_from": 0,
        "paragraph_to": 25,
        "question_text": "Какая тема особенно заметна в начале фрагмента?",
        "question_type": QuizQuestionType.SINGLE_CHOICE,
        "explanation": "Начало строится вокруг политического и религиозного напряжения между группами.",
        "options": [
            ("Политическое и религиозное напряжение", True),
            ("Морское путешествие", False),
            ("Школьная жизнь героя", False),
            ("Научный эксперимент", False),
        ],
    },
    {
        "chapter": 1,
        "paragraph_from": 0,
        "paragraph_to": 25,
        "question_text": "Какая династическая линия упоминается в контексте французского двора?",
        "question_type": QuizQuestionType.SINGLE_CHOICE,
        "explanation": "В романе важен конфликт вокруг французского двора и династии Валуа.",
        "options": [
            ("Валуа", True),
            ("Романовы", False),
            ("Тюдоры", False),
            ("Габсбурги", False),
        ],
    },
    {
        "chapter": 1,
        "paragraph_from": 0,
        "paragraph_to": 25,
        "question_text": "Почему начало фрагмента создает ощущение тревоги?",
        "question_type": QuizQuestionType.SINGLE_CHOICE,
        "explanation": "Тревожность создается упоминанием политического противостояния и ожиданием насилия.",
        "options": [
            ("Из-за политического противостояния и ожидания насилия", True),
            ("Из-за описания непогоды в море", False),
            ("Из-за болезни главного героя", False),
            ("Из-за бытовой ссоры в семье", False),
        ],
    },
]


def seed_demo_quiz_questions(session: Session, book_id: int = DEMO_BOOK_ID) -> int:
    book = session.get(Book, book_id)
    if not book:
        return 0

    created = 0
    for item in DEMO_QUESTIONS:
        exists = session.exec(
            select(QuizQuestion).where(
                QuizQuestion.book_id == book_id,
                QuizQuestion.question_text == item["question_text"],
            )
        ).first()
        if exists:
            continue

        question = QuizQuestion(
            book_id=book_id,
            chapter=item["chapter"],
            paragraph_from=item["paragraph_from"],
            paragraph_to=item["paragraph_to"],
            question_text=item["question_text"],
            question_type=item["question_type"],
            explanation=item["explanation"],
        )
        session.add(question)
        session.commit()
        session.refresh(question)

        for option_text, is_correct in item["options"]:
            session.add(
                QuizOption(
                    question_id=question.question_id,
                    option_text=option_text,
                    is_correct=is_correct,
                )
            )
        session.commit()
        created += 1

    return created
