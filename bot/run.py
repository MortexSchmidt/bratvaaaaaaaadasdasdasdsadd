from __future__ import annotations
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats, BotCommandScopeDefault
from app import load_config
from app.handlers import basic, fun
from app.handlers import group as group_handlers
from app.handlers import mafia
from app.handlers import drochka  # Renamed from drочка
from app.handlers import rp  # Added RP handler
from app.handlers import ai  # Added AI handler
from app.handlers import tictactoe  # Added Tic Tac Toe handler
from app.handlers import truth_or_dare  # Added Truth or Dare handler
from app.handlers import diagnostic  # Diagnostic tools
from app.utils.broadcast import broadcast
from aiogram.filters import Command
from aiogram.types import Message
from aiogram import BaseMiddleware
from typing import Callable, Awaitable, Any, Dict


async def main():
    config = load_config()
    # В aiogram 3.3.0 ещё нет DefaultBotProperties, передаём parse_mode напрямую
    bot = Bot(token=config.bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher()

    class LogUpdateMiddleware(BaseMiddleware):
        async def __call__(self, handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]], event: Message, data: Dict[str, Any]):
            logging.getLogger("updates").info("Incoming message: chat=%s user=%s text=%r", getattr(event.chat,'id',None), getattr(event.from_user,'id',None), getattr(event,'text',None))
            return await handler(event, data)

    # Подключаем middleware на уровень сообщений
    dp.message.middleware(LogUpdateMiddleware())

    # базовое логирование
    import logging, sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # Initialize the database for drochka system
    try:
        drochka.init_db()
        logging.info("Database initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize database: {e}")

    # регистрация роутеров
    dp.include_router(basic.router)
    dp.include_router(fun.router)
    dp.include_router(group_handlers.router)
    dp.include_router(mafia.router)
    dp.include_router(drochka.router)  # Register drochka router
    dp.include_router(rp.router)  # Register RP router
    dp.include_router(ai.router)  # Register AI router
    dp.include_router(tictactoe.router)  # Register Tic Tac Toe router
    dp.include_router(truth_or_dare.router) # Register Truth or Dare router
    # Диагностика в конце: fallback теперь не блокирует другие
    dp.include_router(diagnostic.router)

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

    async def apply_commands():
        # Сначала чистим, затем ставим новый набор
        try:
            await bot.set_my_commands([], scope=BotCommandScopeDefault())
            await bot.set_my_commands([], scope=BotCommandScopeAllPrivateChats())
            await bot.set_my_commands([], scope=BotCommandScopeAllGroupChats())
        except Exception:
            pass  # очистка не критична
        # Устанавливаем актуальный список
        try:
            await bot.set_my_commands(BASE_COMMANDS, scope=BotCommandScopeDefault())
            await bot.set_my_commands(BASE_COMMANDS, scope=BotCommandScopeAllPrivateChats())
            await bot.set_my_commands(BASE_COMMANDS, scope=BotCommandScopeAllGroupChats())
        except Exception:
            import logging
            logging.getLogger(__name__).warning("Не удалось установить команды")

    @dp.message(Command(commands=["refresh_commands"]))
    async def cmd_refresh_commands(message: Message):
        if message.from_user.id not in config.admins:
            return await message.answer("Недостаточно прав")
        await apply_commands()
        await message.answer("Команды обновлены (очищено и перезаписано). Если не видно — закрой и заново открой меню / в Telegram.")

    # Telegram Bot API: команда может содержать только латиницу/цифры/"_". Поэтому кириллицу убираем из меню,
    # но оставляем обработчики с русскими алиасами.
    BASE_COMMANDS = [
        BotCommand(command="start", description="Запуск бота"),
        BotCommand(command="help", description="Справка"),
        BotCommand(command="profile", description="Профиль"),
        BotCommand(command="drochka", description="Ежедневка"),
        BotCommand(command="daily", description="Ежедневный квест"),
        BotCommand(command="week", description="Прогресс недели"),
        BotCommand(command="recover", description="Восстановить стрик"),
        BotCommand(command="leaders", description="Топ по стрику"),
        BotCommand(command="achievements", description="Мои ачивки"),
        BotCommand(command="top_elo", description="Топ ELO"),
        BotCommand(command="top_level", description="Топ уровней"),
        BotCommand(command="shop", description="Магазин"),
        BotCommand(command="buy", description="Купить"),
        BotCommand(command="titles", description="Титулы"),
        BotCommand(command="equip", description="Надеть титул"),
        BotCommand(command="pet", description="Имя питомца"),
        BotCommand(command="set_status", description="Статус профиля"),
        BotCommand(command="notify_on", description="Вкл. напоминания"),
        BotCommand(command="notify_off", description="Выкл. напоминания"),
        BotCommand(command="truth", description="Правда или действие"),
        BotCommand(command="tod", description="TOD альт"),
        BotCommand(command="tictactoe", description="Крестики-нолики"),
        BotCommand(command="refresh_commands", description="Обновить меню"),
    ]

    async def setup_commands():
        await apply_commands()
        # Логируем что реально установлено по default
        try:
            cmds = await bot.get_my_commands(scope=BotCommandScopeDefault())
            import logging
            logging.getLogger(__name__).info("Bot commands (default) set: %s", [f"/{c.command}" for c in cmds])
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Cannot fetch commands list: %s", e)

    print("Запуск бота...")
    await setup_commands()
    # Запускаем периодический таск проверки перерывов дрочки
    asyncio.create_task(drochka.check_breaks_and_notify(bot))
    await bot.delete_webhook(drop_pending_updates=True)
    # Используем polling в режиме, подходящем для многопоточной среды
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())