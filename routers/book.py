from datetime import datetime
from functools import lru_cache
from typing import Annotated
import re

from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException, Query, Response
import ebooklib
from ebooklib import epub
from sqlalchemy import text
from sqlmodel import Session, select

from deps import get_session
from models.book import Book, BookCreate, BookPublic, BookWithAuthor
from models.favorite import FavoriteStatus, UserBookFavorite
from models.reading import Reading
from models.user import User
from routers.auth import get_current_active_user
from services.gamification import get_or_create_stats, record_reading_session

MAX_CHARS_PER_PAGE = 3000
MAX_LOOKAHEAD = 100

router = APIRouter(
    prefix="/book",
    responses={404: {"description": "Not found"}},
)


def readable_book_clause():
    return text("COALESCE((book.meta->>'total_chars')::integer, 0) > 0")


def is_book_readable(book: Book) -> bool:
    return int((book.meta or {}).get("total_chars", 0) or 0) > 0


def get_epub_item_media_type(item) -> str:
    getter = getattr(item, "get_media_type", None)
    if callable(getter):
        try:
            media_type = getter()
            if media_type:
                return media_type
        except Exception:
            pass
    return getattr(item, "media_type", "") or "application/octet-stream"


@lru_cache(maxsize=256)
def get_book_cover_bytes(book_path: str) -> tuple[bytes, str] | None:
    book = epub.read_epub(book_path)
    images = [item for item in book.get_items() if item.get_type() == ebooklib.ITEM_IMAGE]
    if not images:
        return None

    cover_items = []
    for item in images:
        name = (item.get_name() or "").lower()
        media_type = get_epub_item_media_type(item).lower()
        if "cover" in name or "cover" in media_type:
            cover_items.append(item)

    candidates = cover_items or images
    candidates = [item for item in candidates if item.get_content()]
    if not candidates:
        return None

    image = max(candidates, key=lambda item: len(item.get_content() or b""))
    return image.get_content(), get_epub_item_media_type(image)

@router.post("/", response_model=BookPublic)
def create_book(book: BookCreate, session: Session = Depends(get_session)):
    db_book = Book.model_validate(book)
    session.add(db_book)
    session.commit()
    session.refresh(db_book)
    return db_book


@router.get("/", response_model=list[BookWithAuthor])
def get_books(
    session: Session = Depends(get_session),
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
):
    return session.exec(select(Book).where(readable_book_clause()).offset(offset).limit(limit)).all()


@router.get("/search", response_model=list[BookWithAuthor])
def search_books(
    query: Annotated[str, Query(min_length=1, max_length=100)],
    session: Session = Depends(get_session),
    limit: Annotated[int, Query(ge=1, le=30)] = 20,
):
    term = query.strip()
    if not term:
        return []

    statement = text(
        """
        SELECT b.book_id
        FROM book b
        LEFT JOIN author a ON a.author_id = b.author_id
        WHERE COALESCE((b.meta->>'total_chars')::integer, 0) > 0
          AND (
            word_similarity(immutable_unaccent(lower(:term)), immutable_unaccent(lower(b.name))) >= 0.45
            OR word_similarity(immutable_unaccent(lower(:term)), immutable_unaccent(lower(COALESCE(a.name, '')))) >= 0.6
            OR word_similarity(immutable_unaccent(lower(:term)), immutable_unaccent(lower(COALESCE(a.surname, '')))) >= 0.6
            OR word_similarity(immutable_unaccent(lower(:term)), immutable_unaccent(lower(COALESCE(a.name || ' ' || a.surname, '')))) >= 0.6
            OR immutable_unaccent(lower(b.name)) LIKE immutable_unaccent(lower(:contains))
          )
        ORDER BY GREATEST(
            word_similarity(immutable_unaccent(lower(:term)), immutable_unaccent(lower(b.name))) * 1.2,
            word_similarity(immutable_unaccent(lower(:term)), immutable_unaccent(lower(COALESCE(a.name, '')))),
            word_similarity(immutable_unaccent(lower(:term)), immutable_unaccent(lower(COALESCE(a.surname, '')))),
            word_similarity(immutable_unaccent(lower(:term)), immutable_unaccent(lower(COALESCE(a.name || ' ' || a.surname, ''))))
        ) DESC, b.name
        LIMIT :limit
        """
    )
    rows = session.execute(
        statement,
        {"term": term, "contains": f"%{term}%", "limit": limit},
    ).all()

    books = []
    for (book_id,) in rows:
        book = session.get(Book, book_id)
        if book and is_book_readable(book):
            book.author
            books.append(book)
    return books

@router.get("/reading-progress")
def get_reading_books_progress(
    user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    readings = session.exec(
        select(Reading)
        .where(Reading.user_id == user.user_id)
        .where((Reading.total_chars_read > 0) | (Reading.is_completed == True))
        .order_by(Reading.updated_at.desc())
    ).all()

    result = []
    for reading in readings:
        book = session.get(Book, reading.book_id)
        if not book or not is_book_readable(book):
            continue
        book.author
        progress = 100.0 if reading.is_completed else calculate_progress(
            book,
            reading.total_chars_read,
        )
        result.append(
            {
                "book": book,
                "progress": progress,
                "total_chars_read": reading.total_chars_read,
                "is_completed": reading.is_completed,
                "updated_at": reading.updated_at,
            }
        )
    return result

@router.get("/favorites", response_model=list[BookWithAuthor])
def get_favorite_books(
    user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    statement = (
        select(Book)
        .join(UserBookFavorite, UserBookFavorite.book_id == Book.book_id)
        .where(UserBookFavorite.user_id == user.user_id)
        .where(readable_book_clause())
        .order_by(UserBookFavorite.created_at.desc())
    )
    return session.exec(statement).all()


@router.get("/{book_id}/favorite", response_model=FavoriteStatus)
def get_favorite_status(
    book_id: int,
    user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    favorite = session.get(UserBookFavorite, (user.user_id, book_id))
    return FavoriteStatus(book_id=book_id, is_favorite=favorite is not None)


@router.post("/{book_id}/favorite", response_model=FavoriteStatus)
def add_favorite_book(
    book_id: int,
    user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    book = session.get(Book, book_id)
    if not book or not is_book_readable(book):
        raise HTTPException(status_code=404, detail="Book not found")

    favorite = session.get(UserBookFavorite, (user.user_id, book_id))
    if not favorite:
        session.add(UserBookFavorite(user_id=user.user_id, book_id=book_id))
        session.commit()
    return FavoriteStatus(book_id=book_id, is_favorite=True)


@router.delete("/{book_id}/favorite", response_model=FavoriteStatus)
def remove_favorite_book(
    book_id: int,
    user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    favorite = session.get(UserBookFavorite, (user.user_id, book_id))
    if favorite:
        session.delete(favorite)
        session.commit()
    return FavoriteStatus(book_id=book_id, is_favorite=False)

@router.get("/{book_id}/cover")
def get_book_cover(book_id: int, session: Session = Depends(get_session)):
    book = session.get(Book, book_id)
    if not book or not is_book_readable(book):
        raise HTTPException(status_code=404, detail="Book not found")

    try:
        cover = get_book_cover_bytes(book.book_path)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Book cover not found: {exc}")

    if not cover:
        raise HTTPException(status_code=404, detail="Book cover not found")

    content, media_type = cover
    return Response(
        content=content,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )

@router.get("/{book_id}", response_model=BookWithAuthor)
def get_book(book_id: int, session: Session = Depends(get_session)):
    book = session.get(Book, book_id)
    if not book or not is_book_readable(book):
        raise HTTPException(status_code=404, detail="Book not found")
    book.author
    return book


def clean_html_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


@lru_cache(maxsize=512)
def get_book_paragraphs(book_path: str, chapter_index: int) -> tuple[list[str], int]:
    try:
        book = epub.read_epub(book_path)
        chapters = [
            item for item in book.get_items()
            if item.get_type() == ebooklib.ITEM_DOCUMENT
        ]

        if chapter_index >= len(chapters):
            return [], 0

        chapter_content = chapters[chapter_index].get_content().decode("utf-8")
        soup = BeautifulSoup(chapter_content, "html.parser")

        paragraphs = []
        for paragraph in soup.find_all("p"):
            clean_text = clean_html_text(str(paragraph))
            if clean_text:
                paragraphs.append(clean_text)

        return paragraphs, len(paragraphs)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Book reading error: {exc}")


def _sentence_break_end(text: str, start: int) -> int:
    end = start

    while end < len(text) and text[end] in ".!?\u2026":
        end += 1

    while True:
        while end < len(text) and text[end] in "\"'»«“”‘’)]}:;":
            end += 1

        footnote_match = re.match(r"\[\d+\]", text[end:])
        if not footnote_match:
            break
        end += footnote_match.end()

    return end


def _is_valid_sentence_break(text: str, punctuation_start: int, sentence_end: int) -> bool:
    if sentence_end < len(text) and not text[sentence_end].isspace():
        return False

    if text[punctuation_start] == ".":
        prefix = text[:punctuation_start]
        word_match = re.search(r"([A-Za-zА-Яа-яЁё]{1,2})$", prefix)
        if word_match:
            return False

    return True


def _find_whitespace_break(text: str, max_chars: int, max_lookahead: int) -> int | None:
    prev_break = None
    for match in re.finditer(r"\s+", text):
        if match.start() <= max_chars:
            prev_break = match.start()
            continue

        if match.start() - max_chars <= max_lookahead:
            return match.start()
        break

    return prev_break


def find_best_breakpoint(
    text: str,
    max_chars: int,
    max_lookahead: int = MAX_LOOKAHEAD,
) -> tuple[str | bool, int, bool]:
    if len(text) <= max_chars:
        return text, len(text), False

    sentence_ends: list[int] = []
    for match in re.finditer(r"[.!?…]", text):
        sentence_end = _sentence_break_end(text, match.start())
        if not _is_valid_sentence_break(text, match.start(), sentence_end):
            continue
        if not sentence_ends or sentence_ends[-1] != sentence_end:
            sentence_ends.append(sentence_end)

    prev_end = 0
    next_end = None

    for sentence_end in sentence_ends:
        if sentence_end <= max_chars:
            prev_end = sentence_end
        else:
            next_end = sentence_end
            break

    dist_to_next = next_end - max_chars if next_end else float("inf")

    if next_end and dist_to_next <= max_lookahead:
        return text[:next_end], next_end, True
    if prev_end > 0:
        return text[:prev_end], prev_end, True

    whitespace_end = _find_whitespace_break(text, max_chars, max_lookahead)
    if whitespace_end and whitespace_end > 0:
        return text[:whitespace_end], whitespace_end, True

    return False, 0, False


def get_next_text_fragment(
    book: Book,
    chapter: int,
    paragraph_index: int,
    paragraph_offset: int,
    max_chars: int,
) -> str:
    if max_chars <= 0:
        return ""

    fragment = _calculate_fragment(
        book=book,
        chapter=chapter,
        paragraph=paragraph_index,
        offset=paragraph_offset,
        max_chars=max_chars,
    )
    return fragment["text"]


def get_text_by_char_range(paragraphs: list[str], start_chars: int, end_chars: int) -> str:
    current_chars = 0
    result_text = ""

    for paragraph in paragraphs:
        paragraph_length = len(paragraph)
        if current_chars + paragraph_length >= start_chars and current_chars <= end_chars:
            para_start = max(0, start_chars - current_chars)
            para_end = min(paragraph_length, end_chars - current_chars)
            if para_start < para_end:
                result_text += paragraph[para_start:para_end] + "\n\n"

        current_chars += paragraph_length
        if current_chars >= end_chars:
            break

    return result_text.strip()


def get_or_create_reading(session: Session, book_id: int, user_id: int) -> Reading:
    reading = session.exec(
        select(Reading)
        .where(Reading.book_id == book_id)
        .where(Reading.user_id == user_id)
    ).first()

    if reading:
        return reading

    reading = Reading(
        book_id=book_id,
        user_id=user_id,
        current_chapter=0,
        current_paragraph=0,
        paragraph_offset=0,
        prev_chars_read=0,
        total_chars_read=0,
        updated_at=datetime.utcnow(),
    )
    session.add(reading)
    session.commit()
    session.refresh(reading)
    return reading


def _calculate_fragment(
    book: Book,
    chapter: int,
    paragraph: int,
    offset: int,
    max_chars: int = MAX_CHARS_PER_PAGE,
) -> dict:
    current_text = ""
    current_chars = 0
    current_chapter = chapter
    current_paragraph = paragraph
    current_offset = offset
    is_completed = False
    completed_chapter: int | None = None
    all_paragraphs: list[str] = []

    while current_chars < max_chars:
        all_paragraphs, total_paragraphs = get_book_paragraphs(book.book_path, current_chapter)

        if current_paragraph >= total_paragraphs:
            if current_chars > 0:
                completed_chapter = current_chapter
            current_chapter += 1
            current_paragraph = 0
            current_offset = 0

            if current_chapter >= book.meta.get("chapters", 0):
                is_completed = True
                break
            if current_chars > 0:
                break
            continue

        if current_paragraph >= len(all_paragraphs):
            break

        paragraph_text = all_paragraphs[current_paragraph]
        if current_offset > 0:
            paragraph_text = paragraph_text[current_offset:]

        if not paragraph_text:
            current_paragraph += 1
            current_offset = 0
            continue

        remaining_chars = max_chars - current_chars
        text_to_take, chars_taken, was_split = find_best_breakpoint(
            paragraph_text,
            remaining_chars,
        )

        if text_to_take is False:
            if current_chars == 0:
                text_to_take = paragraph_text[:remaining_chars]
                chars_taken = remaining_chars
                was_split = True
            else:
                break

        current_text += text_to_take + "\n\n"
        current_chars += chars_taken
        current_offset += chars_taken

        if current_offset >= len(all_paragraphs[current_paragraph]) and not was_split:
            current_paragraph += 1
            current_offset = 0

        if was_split:
            break

    return {
        "text": current_text.strip(),
        "chars": current_chars,
        "chapter": current_chapter,
        "paragraph": current_paragraph,
        "offset": current_offset,
        "is_completed": is_completed,
        "completed_chapter": completed_chapter,
        "chapter_paragraphs": all_paragraphs,
    }


def calculate_progress(book: Book, chars_read: int) -> float:
    total_chars = book.meta.get("total_chars", 0)
    if total_chars <= 0:
        return 0.0

    return round(min(chars_read / total_chars, 1.0) * 100, 1)


def build_read_response(
    book: Book,
    reading: Reading,
    fragment: dict,
    context_chars: int,
    *,
    new_achievements: list[dict] | None = None,
    streak_days: int | None = None,
) -> dict:
    saved_progress = calculate_progress(book, reading.total_chars_read)
    pending_progress = calculate_progress(
        book,
        reading.total_chars_read + fragment["chars"],
    )

    next_text = get_next_text_fragment(
        book,
        fragment["chapter"],
        fragment["paragraph"],
        fragment["offset"],
        context_chars,
    )

    return {
        "reading_id": reading.reading_id,
        "text": fragment["text"],
        "next_text": next_text,
        "current_chapter": reading.current_chapter,
        "current_paragraph": reading.current_paragraph,
        "paragraph_offset": reading.paragraph_offset,
        "next_chapter": fragment["chapter"],
        "next_paragraph": fragment["paragraph"],
        "next_paragraph_offset": fragment["offset"],
        "fragment_chars": fragment["chars"],
        "total_chars_read": reading.total_chars_read,
        "prev_chars_read": reading.prev_chars_read,
        "is_completed": reading.is_completed,
        "will_complete": fragment["is_completed"],
        "progress": f"{saved_progress}%",
        "pending_progress": f"{pending_progress}%",
        "streak_days": streak_days,
        "new_achievements": new_achievements or [],
    }


@router.get("/{book_id}/reading-progress")
def get_book_reading_progress(
    book_id: int,
    user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[Session, Depends(get_session)],
):
    book = session.get(Book, book_id)
    if not book or not is_book_readable(book):
        raise HTTPException(status_code=404, detail="Book not found")

    reading = session.exec(
        select(Reading)
        .where(Reading.book_id == book_id)
        .where(Reading.user_id == user.user_id)
    ).first()
    stats = get_or_create_stats(session, user.user_id)

    if not reading:
        return {
            "has_started": False,
            "progress": 0.0,
            "total_chars_read": 0,
            "current_streak_days": stats.current_streak_days,
            "is_completed": False,
        }

    progress = 100.0 if reading.is_completed else calculate_progress(
        book,
        reading.total_chars_read,
    )
    return {
        "has_started": reading.total_chars_read > 0 or reading.is_completed,
        "progress": progress,
        "total_chars_read": reading.total_chars_read,
        "current_streak_days": stats.current_streak_days,
        "is_completed": reading.is_completed,
    }


@router.get("/{book_id}/read")
async def read_book(
    book_id: int,
    user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[Session, Depends(get_session)],
    fragment_chars: int = Query(MAX_CHARS_PER_PAGE, ge=500, le=10000),
    context_chars: int = Query(3000, ge=0, le=10000),
):
    book = session.get(Book, book_id)
    if not book or not is_book_readable(book):
        raise HTTPException(status_code=404, detail="Book not found")

    reading = get_or_create_reading(session, book_id, user.user_id)
    stats = get_or_create_stats(session, user.user_id)

    if reading.is_completed:
        return {
            "reading_id": reading.reading_id,
            "message": "Book completed",
            "is_completed": True,
            "text": "",
            "next_text": "",
            "current_chapter": reading.current_chapter,
            "current_paragraph": reading.current_paragraph,
            "paragraph_offset": reading.paragraph_offset,
            "total_chars_read": reading.total_chars_read,
            "progress": "100%",
            "streak_days": stats.current_streak_days,
            "new_achievements": [],
        }

    fragment = _calculate_fragment(
        book=book,
        chapter=reading.current_chapter,
        paragraph=reading.current_paragraph,
        offset=reading.paragraph_offset,
        max_chars=fragment_chars,
    )

    return build_read_response(
        book=book,
        reading=reading,
        fragment=fragment,
        context_chars=context_chars,
        streak_days=stats.current_streak_days,
    )


@router.post("/{book_id}/read/complete")
async def complete_read_fragment(
    book_id: int,
    user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[Session, Depends(get_session)],
    fragment_chars: int = Query(MAX_CHARS_PER_PAGE, ge=500, le=10000),
    context_chars: int = Query(3000, ge=0, le=10000),
):
    book = session.get(Book, book_id)
    if not book or not is_book_readable(book):
        raise HTTPException(status_code=404, detail="Book not found")

    reading = get_or_create_reading(session, book_id, user.user_id)
    if reading.is_completed:
        stats = get_or_create_stats(session, user.user_id)
        return {
            "reading_id": reading.reading_id,
            "message": "Book already completed",
            "is_completed": True,
            "text": "",
            "next_text": "",
            "current_chapter": reading.current_chapter,
            "current_paragraph": reading.current_paragraph,
            "paragraph_offset": reading.paragraph_offset,
            "total_chars_read": reading.total_chars_read,
            "progress": "100%",
            "streak_days": stats.current_streak_days,
            "new_achievements": [],
        }

    fragment = _calculate_fragment(
        book=book,
        chapter=reading.current_chapter,
        paragraph=reading.current_paragraph,
        offset=reading.paragraph_offset,
        max_chars=fragment_chars,
    )

    was_completed_before = reading.is_completed
    chars_read_before = reading.total_chars_read

    reading.current_chapter = fragment["chapter"]
    reading.current_paragraph = fragment["paragraph"]
    reading.paragraph_offset = fragment["offset"]
    reading.prev_chars_read = chars_read_before
    reading.total_chars_read += fragment["chars"]
    reading.is_completed = fragment["is_completed"]
    reading.updated_at = datetime.utcnow()
    session.add(reading)
    session.commit()
    session.refresh(reading)

    book_just_completed = reading.is_completed and not was_completed_before
    stats, new_achievements = record_reading_session(
        session=session,
        user_id=user.user_id,
        chars_delta=fragment["chars"],
        book_just_completed=book_just_completed,
    )

    next_fragment = _calculate_fragment(
        book=book,
        chapter=reading.current_chapter,
        paragraph=reading.current_paragraph,
        offset=reading.paragraph_offset,
        max_chars=fragment_chars,
    )

    response = build_read_response(
        book=book,
        reading=reading,
        fragment=next_fragment,
        context_chars=context_chars,
        new_achievements=new_achievements,
        streak_days=stats.current_streak_days,
    )
    response["completed_fragment_chars"] = fragment["chars"]
    response["quiz_chapter"] = fragment["completed_chapter"]
    return response















