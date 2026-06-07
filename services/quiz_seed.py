from sqlmodel import Session, select

from models.author import Author
from models.book import Book
from models.quiz import QuizOption, QuizQuestion, QuizQuestionType

DEMO_BOOKS = [{'legacy_book_id': 135,
  'title': 'Королева Марго',
  'author_name': 'Александр',
  'author_surname': 'Дюма',
  'questions': [{'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'В каком году происходят события, упоминаемые в начале фрагмента?',
                 'question_type': 'single_choice',
                 'explanation': 'Начало романа связано с событиями 1572 года во Франции.',
                 'options': [('1572', True), ('1812', False), ('1492', False), ('1613', False)]},
                {'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Какое историческое событие является важным фоном начала повествования?',
                 'question_type': 'single_choice',
                 'explanation': 'В начале романа ощущается напряжение, связанное с религиозным конфликтом и '
                                'Варфоломеевской ночью.',
                 'options': [('Варфоломеевская ночь', True),
                             ('Отечественная война', False),
                             ('Крещение Руси', False),
                             ('Петровские реформы', False)]},
                {'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Какая тема особенно заметна в начале фрагмента?',
                 'question_type': 'single_choice',
                 'explanation': 'Начало строится вокруг политического и религиозного напряжения между группами.',
                 'options': [('Политическое и религиозное напряжение', True),
                             ('Морское путешествие', False),
                             ('Школьная жизнь героя', False),
                             ('Научный эксперимент', False)]},
                {'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Какая династическая линия упоминается в контексте французского двора?',
                 'question_type': 'single_choice',
                 'explanation': 'Роман показывает французский двор эпохи Валуа.',
                 'options': [('Валуа', True), ('Романовы', False), ('Тюдоры', False), ('Габсбурги', False)]},
                {'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Почему начало фрагмента создает ощущение тревоги?',
                 'question_type': 'single_choice',
                 'explanation': 'Тревожность создается политическим противостоянием и ожиданием насилия.',
                 'options': [('Из-за политического противостояния и ожидания насилия', True),
                             ('Из-за описания непогоды в море', False),
                             ('Из-за болезни главного героя', False),
                             ('Из-за бытовой ссоры в семье', False)]}]},
 {'legacy_book_id': 137,
  'title': 'Алые паруса',
  'author_name': 'Александр',
  'author_surname': 'Грин',
  'questions': [{'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Как зовут главную героиню повести «Алые паруса»?',
                 'question_type': 'single_choice',
                 'explanation': 'Главная героиня повести — Ассоль.',
                 'options': [('Ассоль', True), ('Ася', False), ('Маргарита', False), ('Софья', False)]},
                {'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Кем является Лонгрен для Ассоль?',
                 'question_type': 'single_choice',
                 'explanation': 'Лонгрен — отец Ассоль, один из ключевых персонажей начала повести.',
                 'options': [('Отцом', True), ('Братом', False), ('Учителем', False), ('Капитаном корабля', False)]},
                {'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Какая мечта связана с образом алых парусов?',
                 'question_type': 'single_choice',
                 'explanation': 'Алые паруса становятся символом надежды, мечты и ожидания чуда.',
                 'options': [('Мечта о чуде и счастливой встрече', True),
                             ('Желание разбогатеть', False),
                             ('Стремление стать ученым', False),
                             ('Победа в военном походе', False)]},
                {'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Как жители обычно относятся к Ассоль и ее семье?',
                 'question_type': 'single_choice',
                 'explanation': 'В начале повести заметна отчужденность жителей по отношению к Ассоль и Лонгрену.',
                 'options': [('С недоверием и отчуждением', True),
                             ('С безусловным восхищением', False),
                             ('Как к богатым покровителям', False),
                             ('Как к царской семье', False)]},
                {'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Что особенно важно для настроения начала повести?',
                 'question_type': 'single_choice',
                 'explanation': 'Начало сочетает бытовую суровость с романтической верой в мечту.',
                 'options': [('Контраст сурового быта и романтической мечты', True),
                             ('Описание научной лаборатории', False),
                             ('Военная хроника', False),
                             ('Комическая сатира на чиновников', False)]}]},
 {'legacy_book_id': 258,
  'title': 'Маугли',
  'author_name': 'Редьярд',
  'author_surname': 'Джозеф Киплинг',
  'questions': [{'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Где разворачиваются основные события историй о Маугли?',
                 'question_type': 'single_choice',
                 'explanation': 'Истории о Маугли связаны с жизнью в джунглях.',
                 'options': [('В джунглях', True),
                             ('В северном городе', False),
                             ('В подземелье замка', False),
                             ('На космическом корабле', False)]},
                {'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Кто такой Маугли?',
                 'question_type': 'single_choice',
                 'explanation': 'Маугли — человеческий ребенок, выросший среди зверей.',
                 'options': [('Человеческий ребенок среди зверей', True),
                             ('Старый охотник', False),
                             ('Морской капитан', False),
                             ('Король соседней страны', False)]},
                {'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Какая тема важна для первых историй о Маугли?',
                 'question_type': 'single_choice',
                 'explanation': 'Важная тема — правила стаи и жизнь по законам джунглей.',
                 'options': [('Законы джунглей и жизнь стаи', True),
                             ('Строительство железной дороги', False),
                             ('Придворные интриги', False),
                             ('Судебный процесс', False)]},
                {'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Какую роль играют животные в повествовании?',
                 'question_type': 'single_choice',
                 'explanation': 'Животные выступают полноценными персонажами со своими характерами и правилами.',
                 'options': [('Они являются полноценными персонажами', True),
                             ('Они появляются только в описании еды', False),
                             ('Они не влияют на сюжет', False),
                             ('Они существуют только во сне героя', False)]},
                {'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Что помогает Маугли выживать среди зверей?',
                 'question_type': 'single_choice',
                 'explanation': 'Маугли выживает благодаря принятию законов джунглей и поддержке тех, кто его '
                                'защищает.',
                 'options': [('Знание законов джунглей и поддержка защитников', True),
                             ('Большое богатство', False),
                             ('Военный чин', False),
                             ('Магическая книга', False)]}]},
 {'legacy_book_id': 212,
  'title': 'Ася',
  'author_name': 'Иван',
  'author_surname': 'Сергеевич Тургенев',
  'questions': [{'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Кто рассказывает историю в повести «Ася»?',
                 'question_type': 'single_choice',
                 'explanation': 'Повествование ведется от лица рассказчика, вспоминающего события молодости.',
                 'options': [('Рассказчик, вспоминающий молодость', True),
                             ('Сама Ася', False),
                             ('Случайный чиновник', False),
                             ('Неизвестный летописец', False)]},
                {'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Где происходит значительная часть событий повести?',
                 'question_type': 'single_choice',
                 'explanation': 'Действие связано с путешествием рассказчика по Германии, у Рейна.',
                 'options': [('В Германии, у Рейна', True),
                             ('В Сибири', False),
                             ('В Испании', False),
                             ('В древнем Риме', False)]},
                {'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Какое чувство особенно важно для атмосферы начала повести?',
                 'question_type': 'single_choice',
                 'explanation': 'Начало окрашено воспоминанием, одиночеством и ожиданием встречи.',
                 'options': [('Воспоминание и ожидание встречи', True),
                             ('Военная тревога', False),
                             ('Страх перед чудовищем', False),
                             ('Комическое разоблачение', False)]},
                {'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'С кем рассказчик знакомится в повести?',
                 'question_type': 'single_choice',
                 'explanation': 'Важными персонажами становятся Гагин и его сестра Ася.',
                 'options': [('С Гагиным и Асей', True),
                             ('С капитаном Немо', False),
                             ('С Шерлоком Холмсом', False),
                             ('С князем Мышкиным', False)]},
                {'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Какая тема является одной из главных в «Асе»?',
                 'question_type': 'single_choice',
                 'explanation': 'Повесть сосредоточена на любви, нерешительности и последствиях упущенного момента.',
                 'options': [('Любовь и упущенная возможность', True),
                             ('Завоевание новых земель', False),
                             ('Научное открытие', False),
                             ('Судьба пиратского клада', False)]}]},
 {'legacy_book_id': 195,
  'title': 'Человек-невидимка',
  'author_name': 'Герберт',
  'author_surname': 'Джордж Уэллс',
  'questions': [{'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Кто появляется в начале романа «Человек-невидимка»?',
                 'question_type': 'single_choice',
                 'explanation': 'В начале появляется таинственный незнакомец, вызывающий любопытство окружающих.',
                 'options': [('Таинственный незнакомец', True),
                             ('Королевский посол', False),
                             ('Мальчик из джунглей', False),
                             ('Пожилой моряк', False)]},
                {'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Какое время года подчеркивается в начале романа?',
                 'question_type': 'single_choice',
                 'explanation': 'Начало связано с холодом, зимой и метелью.',
                 'options': [('Зима', True), ('Весна', False), ('Лето', False), ('Ранняя осень', False)]},
                {'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Почему внешний вид незнакомца кажется странным?',
                 'question_type': 'single_choice',
                 'explanation': 'Он скрывает лицо и тело, что сразу создает ощущение тайны.',
                 'options': [('Он тщательно скрывает лицо и тело', True),
                             ('Он носит корону', False),
                             ('Он одет как средневековый рыцарь', False),
                             ('Он появляется в водолазном костюме', False)]},
                {'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Какую атмосферу создает начало романа?',
                 'question_type': 'single_choice',
                 'explanation': 'Начало строится на тайне, настороженности и необычности поведения героя.',
                 'options': [('Таинственную и настороженную', True),
                             ('Праздничную и беззаботную', False),
                             ('Пасторальную и спокойную', False),
                             ('Официально-деловую', False)]},
                {'chapter': 1,
                 'paragraph_from': None,
                 'paragraph_to': None,
                 'question_text': 'Какой жанровый элемент особенно заметен в романе Уэллса?',
                 'question_type': 'single_choice',
                 'explanation': 'Роман сочетает фантастическую идею с социальным и психологическим напряжением.',
                 'options': [('Научная фантастика', True),
                             ('Бытовая комедия', False),
                             ('Рыцарский эпос', False),
                             ('Древняя летопись', False)]}]}]


def normalize_text(value: str | None) -> str:
    return " ".join((value or "").casefold().replace("?", "?").split())


def find_demo_book(session: Session, item: dict, fallback_book_id: int | None = None) -> Book | None:
    if fallback_book_id is not None:
        book = session.get(Book, fallback_book_id)
        if book:
            return book

    title = normalize_text(item["title"])
    author_name = normalize_text(item["author_name"])
    author_surname = normalize_text(item["author_surname"])

    books = session.exec(select(Book)).all()
    for book in books:
        if normalize_text(book.name) != title:
            continue

        author = session.get(Author, book.author_id) if book.author_id else None
        if not author:
            continue

        if normalize_text(author.name) == author_name and normalize_text(author.surname) == author_surname:
            return book

    return None


def _upsert_options(session: Session, question: QuizQuestion, options: list[tuple[str, bool]]) -> None:
    existing = session.exec(
        select(QuizOption).where(QuizOption.question_id == question.question_id)
    ).all()
    by_text = {option.option_text: option for option in existing}

    for option_text, is_correct in options:
        option = by_text.get(option_text)
        if option:
            option.is_correct = is_correct
            session.add(option)
        else:
            session.add(
                QuizOption(
                    question_id=question.question_id,
                    option_text=option_text,
                    is_correct=is_correct,
                )
            )


def seed_demo_quiz_questions(session: Session, book_id: int | None = None) -> int:
    created = 0

    for demo_book in DEMO_BOOKS:
        fallback_book_id = book_id if book_id == demo_book.get("legacy_book_id") else None
        book = find_demo_book(session, demo_book, fallback_book_id=fallback_book_id)
        if not book:
            continue

        for item in demo_book["questions"]:
            question_type = QuizQuestionType(item.get("question_type", QuizQuestionType.SINGLE_CHOICE))
            question = session.exec(
                select(QuizQuestion).where(
                    QuizQuestion.book_id == book.book_id,
                    QuizQuestion.question_text == item["question_text"],
                )
            ).first()

            if question:
                question.chapter = item["chapter"]
                question.paragraph_from = item["paragraph_from"]
                question.paragraph_to = item["paragraph_to"]
                question.question_type = question_type
                question.explanation = item["explanation"]
                session.add(question)
            else:
                question = QuizQuestion(
                    book_id=book.book_id,
                    chapter=item["chapter"],
                    paragraph_from=item["paragraph_from"],
                    paragraph_to=item["paragraph_to"],
                    question_text=item["question_text"],
                    question_type=question_type,
                    explanation=item["explanation"],
                )
                session.add(question)
                session.commit()
                session.refresh(question)
                created += 1

            _upsert_options(session, question, item["options"])
            session.commit()

    return created
