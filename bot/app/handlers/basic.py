from __future__ import annotations
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command

router = Router(name="basic")

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("салам пополам я хуеглотка")

@router.message(Command(commands=["help"]))
async def cmd_help(message: Message):
    await message.answer(
        "Доступные команды:\n"
        "/start - приветствие\n"
        "/help - это сообщение\n"
        "/ping - проверка жив ли бот\n"
        "/echo <текст> - повторю\n"
        "/fun - случайная фраза\n"
        "/mafia - информация о мафии\n"
        "/mafia_start - начать игру в мафию (в группах)\n"
        "/дрочка или /drochka - поработать рукой\n"
        "/дрочка_статы или /drochka_stats - статистика дрочки\n"
        "\nRP-отыгровки (отправьте в ответ на сообщение пользователя):\n"
        "трахнуть, изнасиловать, поцеловать, обнять, засосать, убить, пукнуть, минет\n"
        "/broadcast <текст> (админы) - рассылка"
    )

@router.message(Command(commands=["ping"]))
async def cmd_ping(message: Message):
    await message.answer("pong")

@router.message(Command(commands=["whoami", "id"]))
async def cmd_whoami(message: Message):
    user = message.from_user
    chat = message.chat
    await message.answer(
        f"<b>User ID:</b> <code>{user.id}</code>\n" \
        f"<b>Chat ID:</b> <code>{chat.id}</code>\n" \
        f"Тип чата: {chat.type}\n" \
        "Если бот не ловит сообщения в группе — отключи privacy у BotFather."
    )

@router.message(Command(commands=["echo"]))
async def cmd_echo(message: Message):
    # удаляем саму команду
    text = message.text.split(maxsplit=1)
    if len(text) < 2:
        await message.answer("Нужно передать текст: /echo <текст>")
    else:
        await message.answer(text[1])

@router.message(F.text.contains("бот"))
async def mention_react(message: Message):
    if message.from_user and not message.from_user.is_bot:
        await message.reply("Кто звал? Я тут!")
