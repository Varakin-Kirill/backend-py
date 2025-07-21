import json
import os
from ebooklib import epub
import ftfy
from bs4 import BeautifulSoup
import psycopg2

from config import DB_NAME, HOST, PASSWORD, PORT, USER


class DataBase:
    def __init__(self):
        self.connection = psycopg2.connect(
            dbname=DB_NAME,
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
        )

    def insert_author_and_book(self, author, book_data):
        with self.connection as conn:
            with conn.cursor() as cursor:
                
                cursor.execute(
                    """SELECT * from author where name=%s and surname=%s""",
                    (author[0], author[1])
                )
                author_id = cursor.fetchone()[0]
                
                if author_id==0:
                    cursor.execute(
                        """INSERT INTO author (name, surname, description) 
                            VALUES (%s, %s, %s) 
                            RETURNING author_id""",
                            (author[0], author[1], "тест")
                    )
                else:
                    print("Автор",author[0]+" "+author[1]+" уже существует")
                    
                cursor.execute(
                    """SELECT * from book where name=%s""",
                    (book_data['name'],)
                )
                if cursor.fetchone()[0]==0:
                    cursor.execute(
                        """INSERT INTO book (name, description, meta, author_id, book_path, genre) 
                        VALUES (%s, %s, %s, %s, %s, %s)""",
                        (
                            book_data['name'],
                            book_data['description'],
                            json.dumps(book_data['meta'], ensure_ascii=False),
                            author_id,
                            book_data['file_path'],
                            "ХУЙ"
                        )
                    )
                else:
                    print("Книга", book_data['name']+" уже существует")
                conn.commit()
                

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
        exit()
    
    for filename in os.listdir(folder_path):
        if filename.endswith('.epub'):
            file_path = os.path.join(folder_path, filename)
        
            try:
                book = epub.read_epub(file_path)
                
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
                    'meta':{
                        'date': date,
                        'subjects': subjects,
                        'chapters': chapters,
                        'chapter_paragraphs':chapter_paragraphs,
                        'total_paragraphs': total_paragraphs
                    },
                    'file_path': file_path
                }
                db= DataBase()
                
                db.insert_author_and_book(author, book_data)
                
            except Exception as e:
                print(f"Ошибка при обработке {filename}: {e}")

if __name__ == "__main__":
    books_parser()