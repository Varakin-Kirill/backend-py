from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlmodel import Session, select  # noqa: E402

from deps import engine  # noqa: E402
from models.book import Book  # noqa: E402
from routers import book as book_router  # noqa: E402


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class ParagraphCache:
    def __init__(self, book: Book) -> None:
        self.book = book
        self.by_chapter: dict[int, list[str]] = {}

    def get(self, book_path: str, chapter_index: int) -> tuple[list[str], int]:
        if book_path != self.book.book_path:
            return book_router.get_book_paragraphs(book_path, chapter_index)
        if chapter_index not in self.by_chapter:
            paragraphs, _ = book_router.get_book_paragraphs(book_path, chapter_index)
            self.by_chapter[chapter_index] = paragraphs
        paragraphs = self.by_chapter[chapter_index]
        return paragraphs, len(paragraphs)

    def source_text(self) -> str:
        parts: list[str] = []
        for chapter in range(self.book.meta.get("chapters", 0)):
            paragraphs, _ = self.get(self.book.book_path, chapter)
            parts.extend(paragraphs)
        return "\n\n".join(parts)


def collect_fragmented_text(
    book: Book,
    cache: ParagraphCache,
    max_chars: int,
    max_steps: int,
) -> tuple[str, list[dict]]:
    chapter = 0
    paragraph = 0
    offset = 0
    fragments: list[str] = []
    steps: list[dict] = []

    with patch.object(book_router, "get_book_paragraphs", cache.get):
        for step in range(1, max_steps + 1):
            fragment = book_router._calculate_fragment(
                book=book,
                chapter=chapter,
                paragraph=paragraph,
                offset=offset,
                max_chars=max_chars,
            )

            steps.append(
                {
                    "step": step,
                    "from": (chapter, paragraph, offset),
                    "to": (fragment["chapter"], fragment["paragraph"], fragment["offset"]),
                    "chars": fragment["chars"],
                    "text_len": len(fragment["text"]),
                    "completed": fragment["is_completed"],
                }
            )

            if fragment["text"]:
                fragments.append(fragment["text"])

            if fragment["is_completed"]:
                return "\n\n".join(fragments), steps

            next_pos = (fragment["chapter"], fragment["paragraph"], fragment["offset"])
            if fragment["chars"] <= 0 or next_pos == (chapter, paragraph, offset):
                raise RuntimeError(f"Reading cursor stuck at {next_pos} on step {step}")

            chapter, paragraph, offset = next_pos

    raise RuntimeError(f"Book was not completed after {max_steps} steps")


def first_difference(left: str, right: str) -> int | None:
    limit = min(len(left), len(right))
    for index in range(limit):
        if left[index] != right[index]:
            return index
    if len(left) != len(right):
        return limit
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--book-id", type=int, default=None)
    parser.add_argument("--max-chars", type=int, default=3000)
    parser.add_argument("--max-steps", type=int, default=10000)
    args = parser.parse_args()

    with Session(engine) as session:
        if args.book_id is None:
            books = session.exec(select(Book).order_by(Book.book_id)).all()
        else:
            book = session.get(Book, args.book_id)
            books = [book] if book else []

    if not books:
        print("No books found")
        return 1

    failed = False
    for book in books:
        print(f"\nBook {book.book_id}: {book.name}", flush=True)
        cache = ParagraphCache(book)
        try:
            source = cache.source_text()
            fragmented, steps = collect_fragmented_text(book, cache, args.max_chars, args.max_steps)
        except Exception as exc:
            failed = True
            print(f"FAIL: {exc}", flush=True)
            continue

        source_norm = normalize(source)
        fragmented_norm = normalize(fragmented)
        diff = first_difference(source_norm, fragmented_norm)

        print(f"Fragments: {len(steps)}")
        print(f"Source chars normalized: {len(source_norm)}")
        print(f"Fragment chars normalized: {len(fragmented_norm)}")

        if diff is None:
            print("OK: fragmented text matches source text")
            continue

        failed = True
        print(f"FAIL: first normalized difference at char {diff}")
        print(f"Source snippet:     {source_norm[max(0, diff - 80):diff + 160]!r}")
        print(f"Fragment snippet:   {fragmented_norm[max(0, diff - 80):diff + 160]!r}")
        print(f"Last cursor: {steps[-1]}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())