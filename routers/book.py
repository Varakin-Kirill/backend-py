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
    Очищает HTML, оставляя только теги title, заголовки (h1-h6) и параграфы (p)
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Разрешенные теги
    allowed_tags = ['title', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br']
    
    # Создаем новый чистый документ
    clean_soup = BeautifulSoup('', 'html.parser')
    
    # Обрабатываем все разрешенные элементы
    for element in soup.find_all(allowed_tags):
        # Создаем новый тег с тем же именем
        clean_element = clean_soup.new_tag(element.name)
        
        # Копируем содержимое, сохраняя br
        for child in element.children:
            if child.name == 'br':
                # Добавляем br как отдельный тег
                br_tag = clean_soup.new_tag('br')
                clean_element.append(br_tag)
            elif child.name is None:  # текстовый узел
                # Добавляем текст
                text = str(child)
                clean_element.append(text)
        
        clean_soup.append(clean_element)
    
    # Нормализуем пробелы в тексте
    for text_node in clean_soup.find_all(text=True):
        normalized_text = re.sub(r'\s+', ' ', text_node)
        text_node.replace_with(normalized_text)
    
    # Получаем очищенный HTML
    cleaned_html = str(clean_soup)
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
    session: Session = Depends(get_session),
    indent_forward: int = Query(0, ge=0, le=10, description="Number of chapters after requested (max 10)"),
    indent_back: int = Query(0, ge=0, le=10, description="Number of chapters before requested (max 10)")
) -> Dict[str, Any]:
    """
    Получить очищенное HTML содержимое определенной главы книги
    с возможностью получить соседние главы
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
    
    # Проверяем валидность параметров indent
    if indent_forward < 0 or indent_back < 0:
        raise HTTPException(
            status_code=400, 
            detail="indent_forward and indent_back must be non-negative integers"
        )
    
    try:
        # Определяем диапазон глав для загрузки
        start_chapter = max(0, chapter_number - indent_back)
        end_chapter = min(total_chapters - 1, chapter_number + indent_forward)
        
        chapters_content = {}
        
        # Загружаем все запрошенные главы
        for chap_num in range(start_chapter, end_chapter + 1):
            chapter_html = extract_chapter_html(book.book_path, chap_num)
            
            # Получаем информацию о количестве параграфов в главе
            chapter_paragraphs = meta_data.get("chapter_paragraphs", {})
            paragraphs_count = chapter_paragraphs.get(f"content{chap_num}", 0)
            
            chapters_content[chap_num] = {
                "chapter_html": chapter_html,
                "paragraphs_count": paragraphs_count
            }
        
        # Формируем ответ
        response = {
            "book_id": book.book_id,
            "book_title": book.name,
            "requested_chapter": chapter_number,
            "total_chapters": total_chapters,
            "chapters_range": {
                "start": start_chapter,
                "end": end_chapter
            },
            "chapters": chapters_content
        }
        
        return response
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Book file not found on server")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chapter: {str(e)}")
