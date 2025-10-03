from __future__ import annotations
import logging
from aiogram import Router, F
from aiogram.types import ChatMemberUpdated, Message
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

router = Router(name="group")
logger = logging.getLogger(__name__)

@router.my_chat_member()
async def bot_membership_changed(event: ChatMemberUpdated):
    old = event.old_chat_member.status
    new = event.new_chat_member.status
    logger.info("Bot membership changed in chat %s (%s): %s -> %s", event.chat.id, event.chat.type, old, new)
    if new in {"member", "administrator"} and event.chat.type in {"group", "supergroup"}:
        try:
            await event.bot.send_message(event.chat.id, "Всем привет! Я онлайн. Используйте /ping или /help. Если я не реагирую на текст — отключите Privacy Mode у BotFather (/setprivacy -> Disable).")
        except Exception as e:
            logger.warning("Cannot send greeting to chat %s: %s", event.chat.id, e)

@router.message(Command(commands=["groupinfo"]))
async def cmd_groupinfo(message: Message):
    if message.chat.type not in {"group", "supergroup"}:
        return await message.answer("Эта команда доступна только в группе")
    chat = message.chat
    await message.answer(
        f"<b>Информация о группе:</b>\n"
        f"ID: <code>{chat.id}</code>\n"
        f"Тип: {chat.type}\n"
        f"Название: {chat.title}\n"
        f"Username: {chat.username or 'Нет'}\n"
        f"Описание: {chat.description or 'Пусто'}"
    )

# Дополнительный триггер если privacy отключён
@router.message(F.chat.type.in_({"group", "supergroup"}) & F.text.lower().contains("бот"))
async def react_on_word(message: Message):
    try:
        # Get all chat members and mention them
        members = []
        async for member in message.bot.get_chat_members(message.chat.id):
            members.append(member.user.id)
        mentions = " ".join([f"<a href='tg://user?id={user_id}'>‌</a>" for user_id in members])
        await message.reply(f"сука быстрее все сюда нахуй{mentions}", parse_mode="HTML")
    except Exception:
        # Fallback to @all
        await message.reply("сука быстрее все сюда нахуй @all")

@router.message(lambda message: message.text and message.text.lower() == "зов")
async def cmd_zov(message: Message):
    if message.chat.type not in {"group", "supergroup"}:
        return

    # Simple version that always uses @all
    await message.answer("сука быстрее все сюда нахуй @all")