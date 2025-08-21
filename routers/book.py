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

def clean_html_content(html_content: str) -> str:
    """
    Очищает HTML, оставляя только основные теги: заголовки, параграфы, списки, выделение текста
    Включая тег title для названий глав
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Удаляем ненужные элементы, но ОСТАВЛЯЕМ title!
    elements_to_remove = [
        'script', 'style', 'meta', 'link', 'head', 'nav',
        'header', 'footer', 'aside', 'form', 'input', 'button',
        'select', 'textarea', 'iframe', 'object', 'embed', 'canvas',
        'svg', 'img', 'audio', 'video', 'source', 'track', 'map', 'area'
    ]
    
    for element in soup(elements_to_remove):
        element.decompose()
    
    # Разрешенные теги (ДОБАВЛЯЕМ title)
    allowed_tags = [
        'title', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'span',
        'br', 'hr', 'strong', 'em', 'b', 'i', 'u', 'blockquote',
        'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'a'
    ]
    
    # Очищаем атрибуты у всех тегов
    for tag in soup.find_all(True):
        if tag.name not in allowed_tags:
            # Для неразрешенных тегов оставляем только текст
            tag.unwrap()
            continue
        
        # Очищаем атрибуты, оставляя только основные
        clean_attrs = {}
        if tag.name == 'a' and tag.get('href'):
            # Сохраняем ссылки, но очищаем от лишних параметров
            href = tag['href']
            # Убираем якоря и параметры, оставляя только чистые ссылки
            if '#' in href:
                href = href.split('#')[0]
            if '?' in href:
                href = href.split('?')[0]
            clean_attrs['href'] = href
        
        if tag.get('id'):
            clean_attrs['id'] = tag['id']
        
        if tag.get('class'):
            # Оставляем только некоторые классы
            allowed_classes = ['chapter', 'section', 'title', 'subtitle', 'paragraph', 'header']
            clean_classes = [cls for cls in tag['class'] if cls in allowed_classes]
            if clean_classes:
                clean_attrs['class'] = clean_classes
        
        tag.attrs = clean_attrs
    
    # Удаляем пустые теги (кроме title)
    for tag in soup.find_all(True):
        if tag.name != 'title' and not tag.get_text().strip() and not tag.find_all(True):
            tag.decompose()
    
    # Нормализуем пробелы и переносы строк в тексте
    for text_node in soup.find_all(text=True):
        if text_node.parent.name not in ['script', 'style']:
            normalized_text = re.sub(r'\s+', ' ', text_node.string)
            text_node.replace_with(normalized_text)
    
    # Получаем очищенный HTML
    if soup.body:
        cleaned_html = ''.join(str(child) for child in soup.body.children)
    else:
        cleaned_html = str(soup)
    
    # Дополнительная очистка (сохраняем теги title)
    cleaned_html = re.sub(r'<(?!title)(\w+)[^>]*>\s*</\1>', '', cleaned_html)  # Удаляем пустые теги, кроме title
    cleaned_html = re.sub(r'\n\s*\n', '\n\n', cleaned_html)  # Нормализуем переносы строк
    cleaned_html = cleaned_html.strip()
    
    return cleaned_html

def extract_chapter_html(book_path: str, chapter_number: int) -> str:
    """
    Извлекает и очищает HTML содержимое главы, сохраняя заголовки
    """
    try:
        if not os.path.exists(book_path):
            raise FileNotFoundError(f"Book file not found: {book_path}")
        
        book = epub.read_epub(book_path)
        chapters = []
        
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                chapters.append(item)
        
        if chapter_number < 0 or chapter_number >= len(chapters):
            raise IndexError(f"Chapter {chapter_number} not found. Total chapters: {len(chapters)}")
        
        # Получаем оригинальный HTML
        original_html = chapters[chapter_number].get_content().decode('utf-8')
        
        # Очищаем HTML
        cleaned_html = clean_html_content(original_html)
        
        return cleaned_html
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading book: {str(e)}")

@router.get("/{book_id}/chapter/{chapter_number}")
def get_book_chapter_html(
    book_id: int, 
    chapter_number: int, 
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    Получить очищенное HTML содержимое определенной главы книги
    """
    # Получаем книгу из БД
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Проверяем, существует ли глава
    meta_data = book.meta
    total_chapters = meta_data.get("chapters", 0)
    
    if chapter_number < 0 or chapter_number >= total_chapters:
        raise HTTPException(
            status_code=404, 
            detail=f"Chapter {chapter_number} not found. Book has {total_chapters} chapters"
        )
    
    try:
        # Извлекаем очищенное HTML содержимое главы
        chapter_html = extract_chapter_html(book.book_path, chapter_number)
        
        # Получаем информацию о количестве параграфов в главе
        chapter_paragraphs = meta_data.get("chapter_paragraphs", {})
        paragraphs_count = chapter_paragraphs.get(f"content{chapter_number}", 0)
        
        return {
            "book_id": book.book_id,
            "book_title": book.name,
            "chapter_number": chapter_number,
            "chapter_html": chapter_html,
            "paragraphs_count": paragraphs_count,
            "total_chapters": total_chapters
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Book file not found on server")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chapter: {str(e)}")

# Дополнительный эндпоинт для извлечения заголовка главы
@router.get("/{book_id}/chapter/{chapter_number}/title")
def get_chapter_title(
    book_id: int, 
    chapter_number: int, 
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    Получить заголовок определенной главы книги
    """
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    meta_data = book.meta
    total_chapters = meta_data.get("chapters", 0)
    
    if chapter_number < 0 or chapter_number >= total_chapters:
        raise HTTPException(
            status_code=404, 
            detail=f"Chapter {chapter_number} not found. Book has {total_chapters} chapters"
        )
    
    try:
        # Извлекаем HTML
        chapter_html = extract_chapter_html(book.book_path, chapter_number)
        
        # Парсим для извлечения заголовка
        soup = BeautifulSoup(chapter_html, 'html.parser')
        
        # Ищем заголовок в разных местах
        title = None
        
        # 1. Ищем тег title
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
        
        # 2. Если нет title, ищем заголовки h1-h3
        if not title:
            for heading_level in ['h1', 'h2', 'h3']:
                heading = soup.find(heading_level)
                if heading:
                    title = heading.get_text().strip()
                    break
        
        # 3. Если все еще нет, используем номер главы
        if not title:
            title = f"Глава {chapter_number + 1}"
        
        return {
            "book_id": book.book_id,
            "book_title": book.name,
            "chapter_number": chapter_number,
            "chapter_title": title,
            "total_chapters": total_chapters
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chapter: {str(e)}")