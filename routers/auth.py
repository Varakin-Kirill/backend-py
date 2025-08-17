import hmac
import hashlib
import json
from urllib.parse import parse_qsl
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session

from config import BOT_TOKEN
from deps import get_session
from models.user import UserPublic


router = APIRouter(
    prefix="/auth",
    responses={404: {"description": "Not found"}},
)

security = HTTPBearer()

def verify_telegram_webapp_data(init_data: str, bot_token: str) -> bool:
    """Проверка подлинности данных от Telegram WebApp"""
    try:
        parsed_data = dict(parse_qsl(init_data))
        received_hash = parsed_data.pop('hash', None)
        
        if not received_hash:
            return False
            
        data_check_string = '\n'.join(
            f"{key}={value}" 
            for key, value in sorted(parsed_data.items()))
        
        secret_key = hmac.new(
            key="WebAppData".encode(),
            msg=bot_token.encode(),
            digestmod=hashlib.sha256
        ).digest()
        
        computed_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return computed_hash == received_hash
    
    except Exception:
        return False

def extract_tg_user_data(init_data: str) -> dict:
    """Извлекает данные пользователя из initData"""
    try:
        parsed_data = dict(parse_qsl(init_data))
        user_data = parsed_data.get('user')
        if user_data:
            return json.loads(user_data)
        return {}
    except Exception:
        return {}

# 🔼 Dependency для проверки initData в любом эндпоинте
async def validate_init_data(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> dict:
    """Основная зависимость для проверки initData в КАЖДОМ запросе"""
    init_data = credentials.credentials
    
    print(init_data)
    print(verify_telegram_webapp_data(init_data, BOT_TOKEN))
    print(extract_tg_user_data(init_data))
    
    
    if not verify_telegram_webapp_data(init_data, BOT_TOKEN):
        raise HTTPException(status_code=403, detail="Invalid Telegram data")
    
    user_data = extract_tg_user_data(init_data)
    if not user_data.get("id"):
        raise HTTPException(status_code=400, detail="User ID not found")
    
    return user_data