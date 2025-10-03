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
    
    # Create mentions for both users to ensure notifications
    initiator_mention = f"<a href='tg://user?id={initiator.id}'>{initiator.first_name}</a>"
    target_mention = f"<a href='tg://user?id={target.id}'>{target.first_name}</a>"
    
    response = f"{initiator_mention} {action_past} {target_mention}"
    
    # Add some randomness to responses
    if action == "пукнуть":
        responses = [
            f"{initiator_mention} пукнул на {target_mention}. Воняет же!",
            f"{initiator_mention} пукнул прямо в лицо {target_mention}. Не выносимо!",
            f"{initiator_mention} пукнул, а {target_mention} получил дозу газа!",
        ]
        response = random.choice(responses)
    elif action == "минет":
        responses = [
            f"{initiator_mention} сделал минет {target_mention}. Вот это сервис!",
            f"{initiator_mention} решил порадовать {target_mention} минетом!",
            f"{target_mention} получил удовольствие от {initiator_mention}!",
        ]
        response = random.choice(responses)
    
    # Send the message with HTML parsing to make mentions clickable
    await message.answer(response, parse_mode="HTML")