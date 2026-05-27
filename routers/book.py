from datetime import datetime
from typing import Annotated
import re

from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException, Query
import ebooklib
from ebooklib import epub
from sqlmodel import Session, select

from deps import get_session
from models.book import Book, BookCreate, BookPublic, BookWithAuthor
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
    return session.exec(select(Book).offset(offset).limit(limit)).all()


@router.get("/{book_id}", response_model=BookWithAuthor)
def get_book(book_id: int, session: Session = Depends(get_session)):
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    book.author
    return book


def clean_html_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


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


def find_best_breakpoint(
    text: str,
    max_chars: int,
    max_lookahead: int = MAX_LOOKAHEAD,
) -> tuple[str | bool, int, bool]:
    if len(text) <= max_chars:
        return text, len(text), False

    matches = list(re.finditer(r"[.!?]", text))
    prev_end = 0
    next_end = None

    for match in matches:
        if match.end() <= max_chars:
            prev_end = match.end()
        else:
            next_end = match.end()
            break

    dist_to_next = next_end - max_chars if next_end else float("inf")

    if next_end and dist_to_next <= max_lookahead:
        return text[:next_end], next_end, True
    if prev_end > 0:
        return text[:prev_end], prev_end, True
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
    all_paragraphs: list[str] = []

    while current_chars < max_chars:
        all_paragraphs, total_paragraphs = get_book_paragraphs(book.book_path, current_chapter)

        if current_paragraph >= total_paragraphs:
            current_chapter += 1
            current_paragraph = 0
            current_offset = 0

            if current_chapter >= book.meta.get("chapters", 0):
                is_completed = True
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
        "chapter_paragraphs": all_paragraphs,
    }


def calculate_progress(book: Book, chapter: int, paragraph: int) -> float:
    total_paragraphs_global = book.meta.get("total_paragraphs", 0)
    if total_paragraphs_global <= 0:
        return 0.0

    chapter_paragraphs = book.meta.get("chapter_paragraphs", {})
    current_paragraph_global = 0

    for chapter_idx in range(chapter):
        current_paragraph_global += chapter_paragraphs.get(f"content{chapter_idx}", 0)

    current_paragraph_global += paragraph
    return round((current_paragraph_global / total_paragraphs_global) * 100, 1)


def build_read_response(
    book: Book,
    reading: Reading,
    fragment: dict,
    context_chars: int,
    *,
    new_achievements: list[dict] | None = None,
    streak_days: int | None = None,
) -> dict:
    saved_progress = calculate_progress(
        book,
        reading.current_chapter,
        reading.current_paragraph,
    )
    pending_progress = calculate_progress(
        book,
        fragment["chapter"],
        fragment["paragraph"],
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


@router.get("/{book_id}/read")
async def read_book(
    book_id: int,
    user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[Session, Depends(get_session)],
    context_chars: int = Query(3000, ge=0, le=10000),
):
    book = session.get(Book, book_id)
    if not book:
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
    context_chars: int = Query(3000, ge=0, le=10000),
):
    book = session.get(Book, book_id)
    if not book:
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
    return response
