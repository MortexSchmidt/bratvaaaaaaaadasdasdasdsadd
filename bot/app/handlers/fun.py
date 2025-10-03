from __future__ import annotations
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import random

router = Router(name="fun")

FUN_PHRASES = [
    "Код — это поэзия, только без рифмы.",
    "Пятница — маленький релиз счастья.",
    "Если ничего не работает — выключи и включи кофе.",
    "Scrum — это когда все бегают, но кто-то все равно фиксит прод.",
    "Тесты — это письма в будущее самому себе." ,
]

@router.message(Command(commands=["fun"]))
async def cmd_fun(message: Message):
    await message.answer(random.choice(FUN_PHRASES))
