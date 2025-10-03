from __future__ import annotations
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
import asyncio
from typing import Iterable

async def broadcast(bot: Bot, user_ids: Iterable[int], text: str) -> dict:
    stats = {"ok": 0, "forbidden": 0, "errors": 0}
    for uid in user_ids:
        try:
            await bot.send_message(uid, text)
            stats["ok"] += 1
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await bot.send_message(uid, text)
                stats["ok"] += 1
            except Exception:
                stats["errors"] += 1
        except TelegramForbiddenError:
            stats["forbidden"] += 1
        except Exception:
            stats["errors"] += 1
        await asyncio.sleep(0.05)
    return stats
