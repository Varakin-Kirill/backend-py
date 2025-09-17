from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, Query, HTTPException
import re
from sqlmodel import Session
from typing import Annotated, Any, Dict
from sqlmodel import select
from models.book import Book, BookPublic, BookCreate, BookWithAuthor
from deps import get_session
import ebooklib
import os
from ebooklib import epub

from models.reading import Reading
from models.user import User
from routers.auth import validate_init_data
from routers.reading import get_reading
from datetime import datetime

MAX_CHARS_PER_PAGE = 3000
MAX_CHARS_PER_LINE = 100
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
    books = session.exec(select(Book).offset(offset).limit(limit)).all()
    return books

@router.get("/{book_id}", response_model=BookWithAuthor)
def get_book(book_id: int, session: Session = Depends(get_session)):
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    book.author
    return book

# def clean_html_content(html_content: str) -> str:
#     """
#     Очищает HTML, оставляя только теги title, заголовки (h1-h6) и параграфы (p)
#     """
#     soup = BeautifulSoup(html_content, 'html.parser')
    
#     # Разрешенные теги
#     allowed_tags = ['title', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br']
    
#     # Создаем новый чистый документ
#     clean_soup = BeautifulSoup('', 'html.parser')
    
#     # Обрабатываем все разрешенные элементы
#     for element in soup.find_all(allowed_tags):
#         # Создаем новый тег с тем же именем
#         clean_element = clean_soup.new_tag(element.name)
        
#         # Копируем содержимое, сохраняя br
#         for child in element.children:
#             if child.name == 'br':
#                 # Добавляем br как отдельный тег
#                 br_tag = clean_soup.new_tag('br')
#                 clean_element.append(br_tag)
#             elif child.name is None:  # текстовый узел
#                 # Добавляем текст
#                 text = str(child)
#                 clean_element.append(text)
        
#         clean_soup.append(clean_element)
    
#     # Нормализуем пробелы в тексте
#     for text_node in clean_soup.find_all(text=True):
#         normalized_text = re.sub(r'\s+', ' ', text_node)
#         text_node.replace_with(normalized_text)
    
#     # Получаем очищенный HTML
#     cleaned_html = str(clean_soup)
#     cleaned_html = cleaned_html.strip()
    
#     return cleaned_html



# def extract_chapter_html(book_path: str, chapter_number: int) -> str:
#     """
#     Извлекает и очищает HTML содержимое главы, сохраняя заголовки
#     """
#     try:
#         if not os.path.exists(book_path):
#             raise FileNotFoundError(f"Book file not found: {book_path}")
        
#         book = epub.read_epub(book_path)
#         chapters = []
        
#         for item in book.get_items():
#             if item.get_type() == ebooklib.ITEM_DOCUMENT:
#                 chapters.append(item)
        
#         if chapter_number < 0 or chapter_number >= len(chapters):
#             raise IndexError(f"Chapter {chapter_number} not found. Total chapters: {len(chapters)}")
        
#         # Получаем оригинальный HTML
#         original_html = chapters[chapter_number].get_content().decode('utf-8')
        
#         # Очищаем HTML
#         cleaned_html = clean_html_content(original_html)
        
#         return cleaned_html
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error reading book: {str(e)}")

# @router.get("/{book_id}/chapter/{chapter_number}")
# def get_book_chapter_html(
#     book_id: int, 
#     chapter_number: int, 
#     session: Session = Depends(get_session),
#     indent_forward: int = Query(0, ge=0, le=10, description="Number of chapters after requested (max 10)"),
#     indent_back: int = Query(0, ge=0, le=10, description="Number of chapters before requested (max 10)")
# ) -> Dict[str, Any]:
#     """
#     Получить очищенное HTML содержимое определенной главы книги
#     с возможностью получить соседние главы
#     """
#     # Получаем книгу из БД
#     book = session.get(Book, book_id)
#     if not book:
#         raise HTTPException(status_code=404, detail="Book not found")
    
#     # Проверяем, существует ли глава
#     meta_data = book.meta
#     total_chapters = meta_data.get("chapters", 0)
    
#     if chapter_number < 0 or chapter_number >= total_chapters:
#         raise HTTPException(
#             status_code=404, 
#             detail=f"Chapter {chapter_number} not found. Book has {total_chapters} chapters"
#         )
    
#     # Проверяем валидность параметров indent
#     if indent_forward < 0 or indent_back < 0:
#         raise HTTPException(
#             status_code=400, 
#             detail="indent_forward and indent_back must be non-negative integers"
#         )
    
#     try:
#         # Определяем диапазон глав для загрузки
#         start_chapter = max(0, chapter_number - indent_back)
#         end_chapter = min(total_chapters - 1, chapter_number + indent_forward)
        
#         chapters_content = {}
        
#         # Загружаем все запрошенные главы
#         for chap_num in range(start_chapter, end_chapter + 1):
#             chapter_html = extract_chapter_html(book.book_path, chap_num)
            
#             # Получаем информацию о количестве параграфов в главе
#             chapter_paragraphs = meta_data.get("chapter_paragraphs", {})
#             paragraphs_count = chapter_paragraphs.get(f"content{chap_num}", 0)
            
#             chapters_content[chap_num] = {
#                 "chapter_html": chapter_html,
#                 "paragraphs_count": paragraphs_count
#             }
        
#         # Формируем ответ
#         response = {
#             "book_id": book.book_id,
#             "book_title": book.name,
#             "requested_chapter": chapter_number,
#             "total_chapters": total_chapters,
#             "chapters_range": {
#                 "start": start_chapter,
#                 "end": end_chapter
#             },
#             "chapters": chapters_content
#         }
        
#         return response
        
#     except FileNotFoundError:
#         raise HTTPException(status_code=404, detail="Book file not found on server")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error processing chapter: {str(e)}")

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import re

def clean_html_text(text):
    """Очистка текста от HTML тегов и лишних пробелов"""
    # Удаляем HTML теги
    text = re.sub(r'<[^>]+>', '', text)
    # Заменяем множественные пробелы и переносы
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_book_paragraphs(book_path, chapter_index, start_paragraph=0):
    """Получение абзацев из конкретной главы"""
    try:
        book = epub.read_epub(book_path)
        chapters = [item for item in book.get_items() if item.get_type() == ebooklib.ITEM_DOCUMENT]
        
        if chapter_index >= len(chapters):
            return [], 0
        
        chapter_content = chapters[chapter_index].get_content().decode('utf-8')
        soup = BeautifulSoup(chapter_content, 'html.parser')
        
        # Ищем все абзацы
        paragraphs = []
        for p in soup.find_all('p'):
            clean_text = clean_html_text(str(p))
            if clean_text:  # пропускаем пустые абзацы
                paragraphs.append(clean_text)
            # print(p)
            # print("\n\n")
        total_paragraphs = len(paragraphs)
        if start_paragraph >= total_paragraphs:
            return [], total_paragraphs
        
        # print (paragraphs[start_paragraph:], total_paragraphs)
        return paragraphs[start_paragraph:], total_paragraphs
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка чтения книги: {str(e)}")

MAX_CHARS_PER_PAGE = 3000
MAX_LOOKAHEAD = 100  # максимальное добивание до конца предложения

def find_best_breakpoint(text, max_chars, max_lookahead=100):
    """
    Находит лучшую точку для разрыва текста
    """
    if len(text) <= max_chars:
        return text, len(text), False
    
    # Ищем концы предложений вокруг позиции max_chars
    sentence_end_pattern = r'[.!?]'
    matches = list(re.finditer(sentence_end_pattern, text))
    
    prev_end = 0
    next_end = None
    
    # Находим предыдущий и следующий концы предложений
    for match in matches:
        if match.end() <= max_chars:
            prev_end = match.end()
        else:
            next_end = match.end()
            break
    
    # Рассчитываем расстояния
    dist_to_prev = max_chars - prev_end if prev_end > 0 else float('inf')
    dist_to_next = next_end - max_chars if next_end else float('inf')
    
    
    # Выбираем лучшую точку разрыва
    if dist_to_next <= max_lookahead and next_end:
        # Берем до конца следующего предложения
        return text[:next_end], next_end, True
    elif prev_end > 0:
        # Берем до конца предыдущего предложения
        return text[:prev_end], prev_end, True
    else:
        # Не можем найти подходящий разрыв - возвращаем пустой результат
        # Это заставит перейти к следующему абзацу или выборке
        return False, 0, False

@router.get("/{book_id}/read")
async def read_book(
    book_id: int,
    session: Session = Depends(get_session),
    tg_user: dict = Depends(validate_init_data),
):
    # Проверяем пользователя и книгу
    user = session.exec(select(User).where(User.tg_id == tg_user["id"])).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    book = session.exec(select(Book).where(Book.book_id == book_id)).first()
    if not book:
        raise HTTPException(status_code=404, detail="Книга не найдена")
    
    # Находим или создаем запись о чтении
    reading = session.exec(
        select(Reading)
        .where(Reading.book_id == book_id)
        .where(Reading.user_id == user.user_id)
    ).first()
    
    if not reading:
        reading = Reading(
            book_id=book_id,
            user_id=user.user_id,
            current_chapter=0,
            current_paragraph=0,
            paragraph_offset=0,
            total_chars_read=0,
            updated_at=datetime.utcnow()
        )
        session.add(reading)
        session.commit()
        session.refresh(reading)
    
    # Если книга завершена
    if reading.is_completed:
        return {
            "message": "Книга завершена",
            "is_completed": True,
            "text": "",
            "next_offset": reading.current_offset
        }
    
    current_text = ""
    current_chars = 0
    current_chapter = reading.current_chapter
    current_paragraph = reading.current_paragraph
    current_offset = reading.paragraph_offset
    
    # Получаем ВСЕ абзацы текущей главы ОДИН РАЗ
    all_paragraphs, total_paragraphs = get_book_paragraphs(book.book_path, current_chapter, 0)
    
    # Читаем пока не заполним страницу или не закончим главу
    while current_chars < MAX_CHARS_PER_PAGE:
        # Проверяем, не закончилась ли глава
        if current_paragraph >= total_paragraphs:
            # Переходим к следующей главе
            current_chapter += 1
            current_paragraph = 0
            current_offset = 0
            
            if current_chapter >= book.meta.get('chapters', 0):
                reading.is_completed = True
                break
            
            # Получаем абзацы новой главы
            all_paragraphs, total_paragraphs = get_book_paragraphs(book.book_path, current_chapter, 0)
            continue
        
        # Получаем текущий абзац
        if current_paragraph >= len(all_paragraphs):
            break
            
        paragraph = all_paragraphs[current_paragraph]
        
        # Применяем смещение
        if current_offset > 0:
            paragraph = paragraph[current_offset:]
        
        # Если абзац пустой после смещения, переходим к следующему
        if not paragraph:
            current_paragraph += 1
            current_offset = 0
            continue
        
        # Определяем, сколько символов можем взять
        remaining_chars = MAX_CHARS_PER_PAGE - current_chars
        text_to_take, chars_taken, was_split = find_best_breakpoint(paragraph, remaining_chars)
        
        if text_to_take is False:  # ← Важно: проверяем именно False, а не просто пустую строку
            break
        
        # Добавляем текст
        current_text += text_to_take + "\n\n"
        current_chars += chars_taken
        
        # Обновляем позицию
        current_offset += chars_taken
        
        # Проверяем, дочитали ли абзац до конца
        if current_offset >= len(all_paragraphs[current_paragraph]) and not was_split:
            current_paragraph += 1
            current_offset = 0
        
        # Если абзац был разбит - выходим из цикла
        if was_split:
            break
    
    # Обновляем прогресс
    reading.current_chapter = current_chapter
    reading.current_paragraph = current_paragraph
    reading.paragraph_offset = current_offset
    reading.total_chars_read += current_chars
    reading.updated_at = datetime.utcnow()
    session.commit()
    
    total_chapters = book.meta.get('chapters', 1)
    progress_percent = round((current_chapter / total_chapters) * 100, 1) if total_chapters > 0 else 0
    
    return {
        "text": current_text.strip(),
        "current_chapter": current_chapter,
        "current_paragraph": current_paragraph,
        "paragraph_offset": current_offset,
        "total_chars_read": reading.total_chars_read,
        "is_completed": reading.is_completed,
        "progress": f"{progress_percent}%"
    }