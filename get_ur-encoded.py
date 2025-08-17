import hmac
import hashlib
from urllib.parse import quote
import json

bot_token = "AAGal29wlrtG-lWAcFqTe-dM9aK9q0b94mc"

# Исходные данные
data = {
    "auth_date": 1730000000,  # Заменяем строку на Unix timestamp
    "query_id": "AAF2Sd3vAAAAAN0XohDq",  # Добавляем обязательный параметр
    "chat_type": "private",
    "chat_instance": "-1489880302870856401",
    "user": {
        "allows_write_to_pm": True,
        "first_name": "yzned",
        "id": 639868185,
        "is_premium": True,
        "last_name": "",
        "language_code": "ru",
        "photo_url": "https://t.me/i/userpic/320/wHNtVjSM9__-_Kqu4Ulpx_IVlZCa0GCRRScz8OQDjXo.svg",
        "username": "yzned"
    }
}

# 1. Преобразуем данные в URL-параметры
params = {
    "auth_date": str(data["auth_date"]),
    "query_id": data["query_id"],
    "chat_type": data["chat_type"],
    "chat_instance": data["chat_instance"],
    "user": json.dumps(data["user"], separators=(',', ':'))
}

# 2. Сортируем параметры и формируем строку для хэширования
data_check_string = "\n".join([f"{k}={v}" for k, v in sorted(params.items())])

# 3. Генерируем секретный ключ
secret_key = hmac.new(
    key=b"WebAppData",
    msg=bot_token.encode(),
    digestmod=hashlib.sha256
).digest()

# 4. Вычисляем хэш
computed_hash = hmac.new(
    key=secret_key,
    msg=data_check_string.encode(),
    digestmod=hashlib.sha256
).hexdigest()

# 5. Добавляем хэш в параметры
params["hash"] = computed_hash

# 6. URL-кодируем все параметры
init_data = "&".join([f"{k}={quote(str(v))}" for k, v in params.items()])

print("Для использования в заголовке Authorization:")
print(f"Bearer {init_data}")