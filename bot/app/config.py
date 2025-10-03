from __future__ import annotations
from dataclasses import dataclass
from typing import List
import os
from dotenv import load_dotenv

@dataclass
class Config:
    bot_token: str
    admins: List[int]


def load_config(env_file: str = ".env") -> Config:
    if os.path.exists(env_file):
        load_dotenv(env_file)
    token = os.getenv("BOT_TOKEN", "")
    if not token:
        raise RuntimeError("BOT_TOKEN не задан. Добавьте его в .env")
    admins_raw = os.getenv("ADMINS", "")
    admins = [int(x) for x in admins_raw.split(',') if x.strip().isdigit()]
    return Config(bot_token=token, admins=admins)
