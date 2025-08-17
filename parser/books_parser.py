import os
from ebooklib import epub
import ftfy
from bs4 import BeautifulSoup
from db import DataBase


def fix_encoding(text):
    """Исправляет кодировку текста с помощью ftfy."""
    if not text or not isinstance(text, str):
        return text
    
    fixed = ftfy.fix_text(text)
    if any('\u0400' <= char <= '\u04FF' for char in fixed):
        return fixed
    return text


def count_chapters(book):
    """Подсчитывает количество глав через анализ spine с linear='yes'."""
    if not hasattr(book, 'spine'):
        return 0
    
    chapter_count = 0
    for item in book.spine:
        # item[1] содержит атрибут 'linear'
        if len(item) > 1 and item[1] == 'yes':
            chapter_count += 1
    return chapter_count


def count_paragraphs_in_chapters(book):
    """Подсчитывает количество абзацев в каждой главе и общее количество."""
    if not hasattr(book, 'spine'):
        return {}, 0
    
    chapter_paragraphs = {}
    total_paragraphs = 0
    
    for item_id, linear in book.spine:
        if linear == 'yes':
            item = book.get_item_with_id(item_id)
            if item is None:
                continue
                
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            paragraphs = len(soup.find_all('p'))
            
            chapter_paragraphs[item_id] = paragraphs
            total_paragraphs += paragraphs
    
    return chapter_paragraphs, total_paragraphs


def parse_author(full_name):
    """Разделяет полное имя автора на имя и фамилию"""
    parts = full_name.split()
    if not parts:
        return "Неизвестный", "Автор"
    if len(parts) == 1:
        return "", parts[0]
    first_name = parts[0]
    last_name = " ".join(parts[1:])
    return first_name, last_name
    

def books_parser():
    folder_path = 'downloaded_books'
    
    if not os.path.exists(folder_path):
        print(f"Папка {folder_path} не найдена!")
        return
    
    db = DataBase()  # Создаем соединение с БД один раз
    
    for filename in os.listdir(folder_path):
        if not filename.lower().endswith('.epub'):
            continue
            
        file_path = os.path.join(folder_path, filename)
        print(f"Обработка файла: {filename}")
    
        try:
            book = epub.read_epub(file_path)
            
            # Обработка автора
            author = parse_author(book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else "Неизвестный автор")
                
            name = book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else "Без названия"
            description = book.get_metadata('DC', 'description')[0][0] if book.get_metadata('DC', 'description') else "Нет описания"
                
            raw_subjects = book.get_metadata('DC', 'subject')
            subjects = [fix_encoding(subject[0]) for subject in raw_subjects] if raw_subjects else []
            chapters = count_chapters(book)
            chapter_paragraphs, total_paragraphs = count_paragraphs_in_chapters(book)
            date = book.get_metadata('DC', 'date')[0][0] if book.get_metadata('DC', 'date') else "Дата неизвестна"
            
            book_data = {
                'name': name,
                'description': description,
                'meta': {
                    'date': date,
                    'subjects': subjects,
                    'chapters': chapters,
                    'chapter_paragraphs': chapter_paragraphs,
                    'total_paragraphs': total_paragraphs
                },
                'file_path': file_path
            }

            db.insert_author_and_book(author, book_data)
            print(f"Успешно обработана книга: {name}")
            
        except Exception as e:
            print(f"Ошибка при обработке {filename}: {str(e)}")
        finally:
            if 'book' in locals():
                del book


if __name__ == "__main__":
    books_parser()