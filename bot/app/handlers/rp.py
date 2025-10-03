from __future__ import annotations
from aiogram import Router
from aiogram.types import Message
import random

router = Router(name="rp")

# RP actions mapping
RP_ACTIONS = {
    "трахнуть": "трахнул",
    "изнасиловать": "изнасиловал",
    "поцеловать": "поцеловал",
    "обнять": "обнял",
    "засосать": "засосал",
    "убить": "убил",
    "пукнуть": "пукнул на",
    "минет": "сделал минет"
}

@router.message(lambda message: message.text and message.text.lower() in RP_ACTIONS.keys())
async def rp_action(message: Message):
    # Get the action that was used
    action = message.text.lower()
    
    # Check if the message is a reply
    if not message.reply_to_message:
        await message.answer("Это действие нужно применять в ответ на сообщение пользователя!")
        return
    
    # Get the users
    initiator = message.from_user
    target = message.reply_to_message.from_user
    
    # Check if user is trying to RP with themselves
    if initiator.id == target.id:
        if action in ["убить", "изнасиловать"]:
            response = f"{initiator.first_name} не смог себя {action} и ушел в депрессию"
        elif action in ["пукнуть"]:
            response = f"{initiator.first_name} пукнул себе под себя. Странный чел"
        else:
            response = f"{initiator.first_name} не смог себя {action}. Ему нужен партнёр!"
        await message.answer(response)
        return
    
    # Generate response based on action
    action_past = RP_ACTIONS[action]
    response = f"{initiator.first_name} {action_past} {target.first_name}"
    
    # Add some randomness to responses
    if action == "пукнуть":
        responses = [
            f"{initiator.first_name} пукнул на {target.first_name}. Воняет же!",
            f"{initiator.first_name} пукнул прямо в лицо {target.first_name}. Не выносимо!",
            f"{initiator.first_name} пукнул, а {target.first_name} получил дозу газа!",
        ]
        response = random.choice(responses)
    elif action == "минет":
        responses = [
            f"{initiator.first_name} сделал минет {target.first_name}. Вот это сервис!",
            f"{initiator.first_name} решил порадовать {target.first_name} минетом!",
            f"{target.first_name} получил удовольствие от {initiator.first_name}!",
        ]
        response = random.choice(responses)
    
    await message.answer(response)