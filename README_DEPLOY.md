# ABZAC Backend Deploy: Docker Compose + nginx

Схема деплоя:

```text
Пользователь
  -> nginx на VPS + HTTPS
  -> backend container: FastAPI/uvicorn
  -> postgres container: PostgreSQL
```

Frontend можно держать отдельно, например на Vercel.

```text
frontend: https://abzac.example.com
backend:  https://api.abzac.example.com
```

## 1. Подготовить сервер

Ubuntu/VPS:

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx git ca-certificates curl
```

Установить Docker и Compose plugin:

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo tee /etc/apt/keyrings/docker.asc > /dev/null
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

После `usermod` лучше перелогиниться на сервер.

## 2. Скопировать проект

Пример пути:

```bash
sudo mkdir -p /var/www/abzac
sudo chown -R $USER:$USER /var/www/abzac
cd /var/www/abzac
# git clone <repo-url> .
```

Backend должен оказаться здесь:

```text
/var/www/abzac/backend-py
```

Внутри backend должна быть папка:

```text
/var/www/abzac/backend-py/demo-books
```

В ней лежат 5 EPUB для MVP.

## 3. Настроить .env

```bash
cd /var/www/abzac/backend-py
cp .env.example .env
nano .env
```

Минимально заменить:

```env
POSTGRES_PASSWORD=надежный_пароль
FRONTEND_ORIGINS=https://abzac.example.com
BOOKS_DIR=demo-books
```

`FRONTEND_ORIGINS` должен содержать домен frontend. Если frontend будет на Vercel, указываем Vercel URL.

## 4. Собрать и запустить backend + PostgreSQL

```bash
cd /var/www/abzac/backend-py
docker compose up -d --build
```

Проверить контейнеры:

```bash
docker compose ps
docker compose logs -f backend
```

Проверить backend локально на сервере:

```bash
curl http://127.0.0.1:8000/health
```

Ожидаемый ответ:

```text
"OK"
```

## 5. Загрузить demo-books в БД

После первого запуска backend создаст таблицы. Затем выполнить парсер внутри backend-контейнера:

```bash
docker compose exec backend python parser/books_parser.py --folder demo-books
```

Перезапустить backend, чтобы seed самопроверки гарантированно прошел после появления книг:

```bash
docker compose restart backend
```

Проверить, что API отдает 5 книг:

```bash
curl http://127.0.0.1:8000/book/
```

## 6. Настроить nginx вне Docker

В файле:

```text
deploy/nginx-abzac.conf
```

заменить:

```text
api.abzac.example.com
```

на реальный backend-домен.

Скопировать конфиг:

```bash
sudo cp /var/www/abzac/backend-py/deploy/nginx-abzac.conf /etc/nginx/sites-available/abzac-backend
sudo ln -s /etc/nginx/sites-available/abzac-backend /etc/nginx/sites-enabled/abzac-backend
sudo nginx -t
sudo systemctl reload nginx
```

Проверить без HTTPS:

```bash
curl http://api.abzac.example.com/health
```

## 7. Подключить HTTPS

```bash
sudo certbot --nginx -d api.abzac.example.com
```

Проверить:

```bash
curl https://api.abzac.example.com/health
```

## 8. Настроить frontend

Во frontend на Vercel указать env:

```env
EXPO_PUBLIC_API_URL=https://api.abzac.example.com
```

В backend `.env` должен быть frontend-домен:

```env
FRONTEND_ORIGINS=https://abzac.example.com
```

После изменения `.env` перезапустить backend:

```bash
docker compose up -d
```

## 9. Обновление backend на сервере

```bash
cd /var/www/abzac
# git pull
cd backend-py
docker compose up -d --build
```

Если менялись demo-books или база чистая:

```bash
docker compose exec backend python parser/books_parser.py --folder demo-books
docker compose restart backend
```

## 10. Быстрая проверка MVP

После деплоя пройти сценарий:

```text
регистрация/вход
-> библиотека из 5 книг
-> открытие книги
-> обложка отображается
-> чтение первой главы
-> самопроверка
-> результат
-> достижения
-> профиль
```

Полезные команды:

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f postgres
sudo nginx -t
sudo systemctl reload nginx
```
