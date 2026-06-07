from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlmodel import Session, select  # noqa: E402

from deps import engine  # noqa: E402
from models.book import Book  # noqa: E402
from routers.book import get_book_paragraphs  # noqa: E402


def calculate_total_chars(book: Book) -> int:
    total_chars = 0
    for chapter in range(book.meta.get("chapters", 0)):
        paragraphs, _ = get_book_paragraphs(book.book_path, chapter)
        total_chars += sum(len(paragraph) for paragraph in paragraphs)
    return total_chars


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--book-id", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    with Session(engine) as session:
        statement = select(Book).order_by(Book.book_id)
        if args.book_id is not None:
            statement = statement.where(Book.book_id == args.book_id)
        books = session.exec(statement).all()

        if not books:
            print("No books found")
            return 1

        updated = 0
        skipped = 0
        for book in books:
            if not args.force and book.meta.get("total_chars") is not None:
                skipped += 1
                continue

            total_chars = calculate_total_chars(book)
            book.meta = {**book.meta, "total_chars": total_chars}
            session.add(book)
            updated += 1
            print(f"Book {book.book_id}: total_chars={total_chars}", flush=True)

        session.commit()

    print(f"Updated: {updated}; skipped: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())