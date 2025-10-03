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
    await message.answer(
        f"ID чата: <code>{message.chat.id}</code>\n"
        f"Тип: {message.chat.type}\n"
        f"Ваш ID: <code>{message.from_user.id}</code>\n"
        "Если бот не видит сообщения — выключите Privacy Mode у BotFather."
    )

# Дополнительный триггер если privacy отключён
@router.message(F.chat.type.in_({"group", "supergroup"}) & F.text.lower().contains("бот"))
async def react_on_word(message: Message):
    await message.reply("Я слышу слово 'бот' – я тут. /help")

@router.message(Command(commands=["zov"]))
async def cmd_zov(message: Message):
    if message.chat.type not in {"group", "supergroup"}:
        return
        
    try:
        # Get chat administrators
        chat_id = message.chat.id
        admins = await message.bot.get_chat_administrators(chat_id)
        mentions = []
        
        for admin in admins:
            user = admin.user
            if user.username:
                # Use username if available (clickable)
                mentions.append(f"@{user.username}")
            else:
                # Use HTML link to user if no username
                name = user.first_name or "Пользователь"
                mentions.append(f"<a href='tg://user?id={user.id}'>{name}</a>")
        
        # Join all mentions with commas
        mentions_text = ", ".join(mentions)
        
        # Send message with mentions
        await message.answer(
            f"сука быстрее все сюда нахуй\n{mentions_text}",
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        if "BUTTON_USER_PRIVACY_RESTRICTED" in str(e):
            await message.answer("сука быстрее все сюда нахуй")
        else:
            logger.error(f"Error in zov command: {e}")
    except Exception as e:
        logger.error(f"Error in zov command: {e}")
        await message.answer("сука быстрее все сюда нахуй")