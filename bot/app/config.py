from __future__ import annotations
from dataclasses import dataclass
from typing import List
import os
from dotenv import load_dotenv

@dataclass
class Config:
    bot_token: str
    admins: List[int]
    openai_api_key: str


def load_config(env_file: str = ".env") -> Config:
    if os.path.exists(env_file):
        load_dotenv(env_file)

    token = os.getenv("BOT_TOKEN", "")
    if not token:
        raise RuntimeError("BOT_TOKEN не задан. Добавьте его в .env")

    admins_raw = os.getenv("ADMINS", "")
    admins = [int(x) for x in admins_raw.split(',') if x.strip().isdigit()]

    openai_key = os.getenv("OPENAI_API_KEY", "")
    print(f"DEBUG: OPENAI_API_KEY loaded: {bool(openai_key)} (length: {len(openai_key) if openai_key else 0})")

    return Config(bot_token=token, admins=admins, openai_api_key=openai_key)


def format_user_mention(user) -> str:
    """Format user mention as clickable link"""
    username = user.username or user.first_name or "Неизвестный"
    return f"<a href='tg://user?id={user.id}'>{username}</a>"

def format_user_mention_from_id(user_id: int, username: str) -> str:
    """Format user mention from user_id and username"""
    return f"<a href='tg://user?id={user_id}'>{username}</a>"
