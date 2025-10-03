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
    
    try:
        # Получаем список администраторов чата
        admins = await message.bot.get_chat_administrators(message.chat.id)
        mentions = []
        
        for admin in admins:
            user = admin.user
            # Создаем корректные упоминания
            if user.username:
                # Для пользователей с username используем прямое упоминание
                mentions.append(f"@{user.username}")
            else:
                # Для пользователей без username создаем HTML-ссылку
                first_name = user.first_name or 'Пользователь'
                mentions.append(f"<a href='tg://user?id={user.id}'>{first_name}</a>")
        
        # Объединяем упоминания через запятую
        mentions_text = ", ".join(mentions)
        
        # Отправляем сообщение с упоминаниями используя HTML разметку
        response_text = f"сука быстрее все сюда нахуй\n{mentions_text}"
        await message.answer(response_text, parse_mode="HTML")
        
    except TelegramBadRequest as e:
        # Если возникает ошибка при отправке, пробуем отправить без HTML-разметки
        logger.error(f"TelegramBadRequest in zov command: {e}")
        try:
            # Резервный вариант: отправка без HTML с обычными упоминаниями
            admins = await message.bot.get_chat_administrators(message.chat.id)
            plain_mentions = []
            
            for admin in admins:
                user = admin.user
                if user.username:
                    plain_mentions.append(f"@{user.username}")
                else:
                    plain_mentions.append(user.first_name or "Пользователь")
            
            plain_mentions_text = ", ".join(plain_mentions)
            response_text = f"сука быстрее все сюда нахуй {plain_mentions_text}"
            await message.answer(response_text)
        except Exception as fallback_error:
            logger.error(f"Fallback error in zov command: {fallback_error}")
            await message.answer("сука быстрее все сюда нахуй")
            
    except Exception as e:
        logger.error(f"Error in zov command: {e}")
        await message.answer("сука быстрее все сюда нахуй")