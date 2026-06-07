import argparse
import os

from bs4 import BeautifulSoup
from ebooklib import epub

try:
    import ftfy
except ModuleNotFoundError:
    ftfy = None

from db import DataBase

DEFAULT_BOOKS_FOLDER = os.getenv("BOOKS_DIR", "downloaded_books")


def fix_encoding(text):
    """Исправляет кодировку текста с помощью ftfy."""
    if not text or not isinstance(text, str):
        return text

    candidates = [text]
    if ftfy is not None:
        candidates.append(ftfy.fix_text(text))

    for encoding in ("cp1251", "latin1"):
        try:
            candidates.append(text.encode(encoding).decode("utf-8"))
        except UnicodeError:
            pass

    def score(value):
        cyrillic_count = sum("\u0400" <= char <= "\u04FF" for char in value)
        mojibake_count = value.count("Р") + value.count("С") + value.count("Ð") + value.count("Ñ")
        return cyrillic_count - mojibake_count

    return max(candidates, key=score)


def count_chapters(book):
    """Подсчитывает количество глав через анализ spine с linear='yes'."""
    if not hasattr(book, "spine"):
        return 0

    chapter_count = 0
    for item in book.spine:
        if len(item) > 1 and item[1] == "yes":
            chapter_count += 1
    return chapter_count


def count_text_stats_in_chapters(book):
    """Counts paragraphs and cleaned text chars in one EPUB pass."""
    if not hasattr(book, "spine"):
        return {}, 0, 0

    chapter_paragraphs = {}
    total_paragraphs = 0
    total_chars = 0

    for item_id, linear in book.spine:
        if linear != "yes":
            continue

        item = book.get_item_with_id(item_id)
        if item is None:
            continue

        soup = BeautifulSoup(item.get_content(), "html.parser")
        paragraphs = [
            " ".join(paragraph.get_text().split())
            for paragraph in soup.find_all("p")
        ]
        paragraphs = [paragraph for paragraph in paragraphs if paragraph]

        chapter_paragraphs[item_id] = len(paragraphs)
        total_paragraphs += len(paragraphs)
        total_chars += sum(len(paragraph) for paragraph in paragraphs)

    return chapter_paragraphs, total_paragraphs, total_chars


def parse_author(full_name):
    """Разделяет полное имя автора на имя и фамилию."""
    full_name = fix_encoding(full_name)
    parts = full_name.split()
    if not parts:
        return "Неизвестный", "Автор"
    if len(parts) == 1:
        return "", parts[0]
    first_name = " ".join(parts[:-1])
    last_name = parts[-1]
    return first_name, last_name


def parse_book_file(file_path):
    book = epub.read_epub(file_path)

    author = parse_author(
        book.get_metadata("DC", "creator")[0][0]
        if book.get_metadata("DC", "creator")
        else "Неизвестный автор"
    )
    name = (
        fix_encoding(book.get_metadata("DC", "title")[0][0])
        if book.get_metadata("DC", "title")
        else "Без названия"
    )
    description = (
        fix_encoding(book.get_metadata("DC", "description")[0][0])
        if book.get_metadata("DC", "description")
        else "Нет описания"
    )
    raw_subjects = book.get_metadata("DC", "subject")
    subjects = [fix_encoding(subject[0]) for subject in raw_subjects] if raw_subjects else []
    chapters = count_chapters(book)
    chapter_paragraphs, total_paragraphs, total_chars = count_text_stats_in_chapters(book)
    date = (
        fix_encoding(book.get_metadata("DC", "date")[0][0])
        if book.get_metadata("DC", "date")
        else "Дата неизвестна"
    )

    return author, {
        "name": name,
        "description": description,
        "meta": {
            "date": date,
            "subjects": subjects,
            "chapters": chapters,
            "chapter_paragraphs": chapter_paragraphs,
            "total_paragraphs": total_paragraphs,
            "total_chars": total_chars,
        },
        "file_path": file_path,
    }


def books_parser(folder_path=None, dry_run=False):
    folder_path = folder_path or DEFAULT_BOOKS_FOLDER

    if not os.path.exists(folder_path):
        print(f"Папка {folder_path} не найдена!")
        return 0

    filenames = sorted(
        filename for filename in os.listdir(folder_path)
        if filename.lower().endswith(".epub")
    )
    if not filenames:
        print(f"В папке {folder_path} нет EPUB-файлов")
        return 0

    db = None if dry_run else DataBase()
    processed = 0

    for filename in filenames:
        file_path = os.path.join(folder_path, filename)
        print(f"Обработка файла: {filename}")

        try:
            author, book_data = parse_book_file(file_path)
            meta = book_data["meta"]
            print(
                "Книга: {name} | автор: {author} | главы: {chapters} | символы: {chars}".format(
                    name=book_data["name"],
                    author=" ".join(author).strip(),
                    chapters=meta["chapters"],
                    chars=meta["total_chars"],
                )
            )

            if not dry_run and db is not None:
                db.insert_author_and_book(author, book_data)
                print(f"Успешно обработана книга: {book_data['name']}")

            processed += 1
        except Exception as exc:
            print(f"Ошибка при обработке {filename}: {exc}")

    print(f"Обработано EPUB-файлов: {processed}")
    return processed


def parse_args():
    parser = argparse.ArgumentParser(description="Parse EPUB books into ABZAC database")
    parser.add_argument(
        "--folder",
        default=DEFAULT_BOOKS_FOLDER,
        help="Папка с EPUB-файлами. По умолчанию: BOOKS_DIR или downloaded_books",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только проверить EPUB и вывести статистику, без записи в БД",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    books_parser(args.folder, dry_run=args.dry_run)


