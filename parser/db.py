from config import DB_NAME, HOST, PASSWORD, PORT, USER
import psycopg2
import json
from psycopg2.extras import DictCursor


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
                    """SELECT author_id from author where name=%s and surname=%s""",
                    (author[0], author[1],)
                )
                author_result = cursor.fetchone()
                
                if not author_result:
                    cursor.execute(
                        """INSERT INTO author (name, surname, description) 
                            VALUES (%s, %s, %s) 
                            RETURNING author_id""",
                            (author[0], author[1], "тест",)
                    )
                    author_id = cursor.fetchone()[0]
                else:
                    author_id = author_result[0]
                    print("Автор",author[0]+" "+author[1]+" уже существует")
                    
                cursor.execute(
                    """SELECT * from book where name=%s AND author_id=%s""",
                    (book_data['name'], author_id)
                )
                book_result = cursor.fetchone()
                
                if not book_result:
                    cursor.execute(
                        """INSERT INTO book (name, description, meta, author_id, book_path, genre) 
                        VALUES (%s, %s, %s, %s, %s, %s)""",
                        (
                            book_data['name'],
                            book_data['description'],
                            json.dumps(book_data['meta'], ensure_ascii=False),
                            author_id,
                            book_data['file_path'],
                            book_data.get('genre', 'unknown')
                        )
                    )
                else:
                    print("Книга", book_data['name']+" уже существует")
                conn.commit()
                
    def search_books_and_authors(self, search_term, limit=10):
        """
        Нечеткий поиск книг и авторов с учетом опечаток
        
        :param search_term: Строка для поиска
        :param limit: Максимальное количество результатов
        :return: Список найденных книг с авторами
        """
        query = """
        WITH search_matches AS (
            -- Поиск по названию книги
            SELECT 
                b.book_id AS book_id,
                b.name AS book_name,
                a.author_id AS author_id,
                a.name AS author_name,
                a.surname AS author_surname,
                similarity(immutable_unaccent(lower(b.name)), immutable_unaccent(lower(%s))) AS score
            FROM book b
            JOIN author a ON b.author_id = a.author_id
            WHERE immutable_unaccent(lower(b.name)) %% immutable_unaccent(lower(%s))
            
            UNION ALL
            
            -- Поиск по имени автора
            SELECT 
                b.book_id, b.name, a.author_id, a.name, a.surname,
                similarity(immutable_unaccent(lower(a.name)), immutable_unaccent(lower(%s))) AS score
            FROM book b
            JOIN author a ON b.author_id = a.author_id
            WHERE immutable_unaccent(lower(a.name)) %% immutable_unaccent(lower(%s))
            
            UNION ALL
            
            -- Поиск по фамилии автора
            SELECT 
                b.book_id, b.name, a.author_id, a.name, a.surname,
                similarity(immutable_unaccent(lower(a.surname)), immutable_unaccent(lower(%s))) AS score
            FROM book b
            JOIN author a ON b.author_id = a.author_id
            WHERE immutable_unaccent(lower(a.surname)) %% immutable_unaccent(lower(%s))
            
            UNION ALL
            
            -- Поиск по полному имени автора
            SELECT 
                b.book_id, b.name, a.author_id, a.name, a.surname,
                similarity(immutable_unaccent(lower(a.name || ' ' || a.surname)), immutable_unaccent(lower(%s))) AS score
            FROM book b
            JOIN author a ON b.author_id = a.author_id
            WHERE immutable_unaccent(lower(a.name || ' ' || a.surname)) %% immutable_unaccent(lower(%s))
        )
        SELECT 
            book_id,
            book_name,
            author_id,
            author_name,
            author_surname,
            MAX(score) AS match_score
        FROM search_matches
        GROUP BY book_id, book_name, author_id, author_name, author_surname
        ORDER BY match_score DESC
        LIMIT %s
        """
        with self.connection as conn:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute(query, [search_term]*8 + [limit])
                return [dict(row) for row in cursor.fetchall()]
            