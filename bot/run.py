from __future__ import annotations
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app import load_config
from app.handlers import basic, fun
from app.handlers import group as group_handlers
from app.utils.broadcast import broadcast
from aiogram.filters import Command
from aiogram.types import Message


async def main():
    config = load_config()
    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # базовое логирование
    import logging, sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # регистрация роутеров
    dp.include_router(basic.router)
    dp.include_router(fun.router)
    dp.include_router(group_handlers.router)

    # простая админ-команда /broadcast
    @dp.message(Command(commands=["broadcast"]))
    async def cmd_broadcast(message: Message):
        if message.from_user.id not in config.admins:
            return await message.answer("Недостаточно прав")
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            return await message.answer("Использование: /broadcast <текст>")
        stats = await broadcast(bot, config.admins, parts[1])
        await message.answer(f"Рассылка завершена: {stats}")

    print("Запуск бота...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
