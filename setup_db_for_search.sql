-- -- Включение расширений (выполнить один раз в БД)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Создание IMMUTABLE-функции для unaccent
CREATE OR REPLACE FUNCTION immutable_unaccent(text)
RETURNS text AS $$
BEGIN
    RETURN unaccent('unaccent', $1);
END
$$ LANGUAGE plpgsql IMMUTABLE;

-- Индексы для таблицы book
CREATE INDEX IF NOT EXISTS trgm_book_name_idx 
ON book USING gin (immutable_unaccent(lower(name)) gin_trgm_ops);

-- Индексы для таблицы author
CREATE INDEX IF NOT EXISTS trgm_author_name_idx 
ON author USING gin (immutable_unaccent(lower(name)) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS trgm_author_surname_idx 
ON author USING gin (immutable_unaccent(lower(surname)) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS trgm_author_fullname_idx 
ON author USING gin (immutable_unaccent(lower(name || ' ' || surname)) gin_trgm_ops);