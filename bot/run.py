from __future__ import annotations
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats
from app import load_config
from app.handlers import basic, fun
from app.handlers import group as group_handlers
from app.utils.broadcast import broadcast
from aiogram.filters import Command
from aiogram.types import Message


async def main():
    config = load_config()
    # В aiogram 3.3.0 ещё нет DefaultBotProperties, передаём parse_mode напрямую
    bot = Bot(token=config.bot_token, parse_mode=ParseMode.HTML)
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

    async def setup_commands():
        base_cmds = [
            ("start", "Начать"),
            ("help", "Справка"),
            ("ping", "Проверка"),
            ("echo", "Эхо текст"),
            ("fun", "Случайная фраза"),
            ("groupinfo", "Инфо о группе"),
            ("whoami", "Ваш ID"),
            ("id", "То же что /whoami"),
        ]
        await bot.set_my_commands(
            [BotCommand(command=c, description=d) for c, d in base_cmds if c not in {"groupinfo"}],
            scope=BotCommandScopeAllPrivateChats()
        )
        await bot.set_my_commands(
            [BotCommand(command=c, description=d) for c, d in base_cmds],
            scope=BotCommandScopeAllGroupChats()
        )

    print("Запуск бота...")
    await setup_commands()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
