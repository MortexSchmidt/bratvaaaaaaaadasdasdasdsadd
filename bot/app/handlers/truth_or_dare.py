"""Remaster Truth or Dare (чистая версия без mini-app и лишнего кода)."""

from __future__ import annotations
import json, random
from pathlib import Path
from typing import Dict, List
from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router(name="truth_or_dare")

DATA_FILE = Path(__file__).parent / "truth_or_dare_content.json"
DEFAULT_TRUTHS = [
    "Какой самый странный факт обо мне (по твоему)?",
    "Чего ты сейчас боишься больше всего?",
    "Что бы ты сделал(а), будь у тебя один свободный день без ограничений?",
    "Какой самый бессмысленный предмет ты когда‑либо покупал(а)?",
    "Что из последнего тебя реально насмешило?",
]
DEFAULT_DARES = [
    "Сделай 10 приседаний и скажи 'я мощь'",
    "Изобрази робота в своём следующем сообщении",
    "Скажи любую фразу ЗЛЫМ шёпотом",
    "Поставь любую смайлу и объясни почему именно она — философски",
    "Напиши сообщение только эмодзи (минимум 5 штук)",
]

def load_content():
    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            return (data.get("truths") or []) or DEFAULT_TRUTHS, (data.get("dares") or []) or DEFAULT_DARES
        except Exception:
            return DEFAULT_TRUTHS, DEFAULT_DARES
    return DEFAULT_TRUTHS, DEFAULT_DARES

TRUTHS, DARES = load_content()

class TruthOrDareGame:
    def __init__(self, chat_id: int, players: List[int], player_names: Dict[int,str], creator_id: int):
        self.chat_id = chat_id
        self.players = players
        self.player_names = player_names
        self.creator_id = creator_id
        self.current_index = 0
        self.passes_used = {pid:0 for pid in players}
        self.phase = "waiting_action"  # waiting_action | task_active
        self.current_task = None
        self.current_task_type = None
    def current_player_id(self): return self.players[self.current_index]
    def current_player_name(self): return self.player_names.get(self.current_player_id(), f"Игрок {self.current_player_id()}")
    def next_player(self):
        self.current_index = (self.current_index + 1) % len(self.players)
        self.phase = "waiting_action"; self.current_task=None; self.current_task_type=None
    def pass_available(self, pid:int): return self.passes_used.get(pid,0) < 1
    def use_pass(self, pid:int): self.passes_used[pid]= self.passes_used.get(pid,0)+1

lobbies: Dict[int, dict] = {}
active_games: Dict[int, TruthOrDareGame] = {}

def lobby_keyboard(is_creator: bool):
    kb=InlineKeyboardBuilder(); kb.button(text="Присоединиться", callback_data="tod:lobby:join")
    if is_creator: kb.button(text="Старт", callback_data="tod:lobby:start"); kb.button(text="Отмена", callback_data="tod:lobby:cancel")
    kb.adjust(2,1); return kb
def action_keyboard(game: TruthOrDareGame):
    kb=InlineKeyboardBuilder();
    kb.button(text="Правда", callback_data="tod:act:truth"); kb.button(text="Действие", callback_data="tod:act:dare"); kb.button(text="Random", callback_data="tod:act:random")
    if game.pass_available(game.current_player_id()): kb.button(text="Пас", callback_data="tod:act:pass")
    if game.creator_id == game.current_player_id(): kb.button(text="Завершить", callback_data="tod:act:end")
    kb.adjust(3,2); return kb
def next_keyboard(game: TruthOrDareGame):
    kb=InlineKeyboardBuilder(); kb.button(text="Далее ▶", callback_data="tod:next")
    if game.creator_id == game.current_player_id(): kb.button(text="Завершить", callback_data="tod:act:end")
    kb.adjust(2); return kb

def mention_name(uid:int, name:str): return f"<a href='tg://user?id={uid}'>{name}</a>"
def render_lobby_text(lobby:dict):
    lines=["🎉 <b>Лобби 'Правда или Действие'</b>","",f"👥 Игроки ({len(lobby['players'])}):"]
    for pid in lobby['players']: lines.append(f"• {lobby['player_names'][pid]}")
    lines.append("\nСоздатель нажимает 'Старт', когда все готовы."); return "\n".join(lines)
def random_truth(): return random.choice(TRUTHS)
def random_dare(): return random.choice(DARES)

@router.message(Command(commands=["truthordare","tod"]))
async def cmd_truth_or_dare(message: Message):
    chat_id=message.chat.id; user_id=message.from_user.id
    if message.chat.type not in {"group","supergroup"}: return await message.answer("Эта игра только в группах")
    if chat_id in active_games: return await message.answer("Игра уже идёт")
    if chat_id in lobbies: return await message.answer("Лобби уже создано")
    name= message.from_user.first_name or message.from_user.username or "Игрок"
    lobby={"creator":user_id,"players":[user_id],"player_names":{user_id:name},"message_id":None}
    lobbies[chat_id]=lobby
    msg= await message.answer(render_lobby_text(lobby), parse_mode="HTML", reply_markup=lobby_keyboard(True).as_markup())
    lobby["message_id"]=msg.message_id

@router.callback_query()
async def tod_callbacks(cb: CallbackQuery, bot: Bot):
    if not cb.data or not cb.data.startswith("tod:"): return await cb.answer()
    parts=cb.data.split(":"); chat_id= cb.message.chat.id if cb.message else None; user_id= cb.from_user.id
    # lobby
    if parts[1]=="lobby":
        if chat_id not in lobbies: return await cb.answer("Лобби не найдено", show_alert=True)
        lobby=lobbies[chat_id]; sub=parts[2]
        if sub=="join":
            if user_id not in lobby['players']:
                lobby['players'].append(user_id); lobby['player_names'][user_id]= cb.from_user.first_name or cb.from_user.username or "Игрок"; await cb.answer("Готово ✅")
            else: await cb.answer("Вы уже в лобби")
            try:
                await bot.edit_message_text(chat_id=chat_id, message_id=lobby['message_id'], text=render_lobby_text(lobby), reply_markup=lobby_keyboard(lobby['creator']==cb.from_user.id).as_markup(), parse_mode="HTML")
            except Exception: pass
        elif sub=="start":
            if user_id!=lobby['creator']: return await cb.answer("Не ты создавал")
            if len(lobby['players'])<2: return await cb.answer("Минимум 2 игрока")
            game= TruthOrDareGame(chat_id,lobby['players'],lobby['player_names'],lobby['creator']); active_games[chat_id]=game; del lobbies[chat_id]
            await cb.message.edit_text(f"🚀 <b>Игра началась!</b>\n\nХод: {mention_name(game.current_player_id(), game.current_player_name())}\nВыбирай действие.", parse_mode="HTML", reply_markup=action_keyboard(game).as_markup())
            await cb.answer()
        elif sub=="cancel":
            if user_id!=lobby['creator']: return await cb.answer("Только создатель")
            del lobbies[chat_id]; await cb.message.edit_text("Лобби закрыто."); await cb.answer()
        return
    # action
    if parts[1]=="act":
        if chat_id not in active_games: return await cb.answer("Игры нет", show_alert=True)
        game=active_games[chat_id]
        if user_id!=game.current_player_id(): return await cb.answer("Не твой ход")
        action=parts[2]
        if action=="end":
            if user_id!=game.creator_id: return await cb.answer("Только создатель")
            del active_games[chat_id]; await cb.message.edit_text("Игра завершена."); return await cb.answer()
        if action=="pass":
            if not game.pass_available(user_id): return await cb.answer("Пас уже использован")
            game.use_pass(user_id); game.next_player()
            await cb.message.edit_text(f"⏭ Пас! Ход: {mention_name(game.current_player_id(), game.current_player_name())}", parse_mode="HTML", reply_markup=action_keyboard(game).as_markup()); return await cb.answer("Пропущено")
        if action in {"truth","dare","random"}:
            if action=="random": action=random.choice(["truth","dare"])
            game.current_task_type=action; game.phase="task_active"; label="Правда" if action=="truth" else "Действие"
            game.current_task= random_truth() if action=="truth" else random_dare()
            await cb.message.edit_text(f"🎲 <b>{label}</b> для {mention_name(user_id, game.current_player_name())}:\n\n<i>{game.current_task}</i>\n\nНапиши ответ / выполни и жми 'Далее'.", parse_mode="HTML", reply_markup=next_keyboard(game).as_markup()); await cb.answer()
        return
    if parts[1]=="next":
        if chat_id not in active_games: return await cb.answer()
        game=active_games[chat_id]
        if user_id!=game.current_player_id(): return await cb.answer("Не ты выполнял")
        if game.phase!="task_active": return await cb.answer()
        game.next_player()
        await cb.message.edit_text(f"✅ Задание завершено! Теперь ход: {mention_name(game.current_player_id(), game.current_player_name())}", parse_mode="HTML", reply_markup=action_keyboard(game).as_markup()); return await cb.answer()
    await cb.answer()

@router.message(Command(commands=["end_tod","stop_tod"]))
async def cmd_end(message: Message):
    chat_id=message.chat.id; user_id=message.from_user.id
    if chat_id in active_games:
        game=active_games[chat_id]
        if user_id!=game.creator_id: return await message.answer("Завершить может только создатель")
        del active_games[chat_id]; return await message.answer("Игра остановлена.")
    if chat_id in lobbies:
        lobby=lobbies[chat_id]
        if user_id!=lobby['creator']: return await message.answer("Только создатель лобби")
        del lobbies[chat_id]; return await message.answer("Лобби закрыто.")
    await message.answer("Нет активной игры или лобби.")

@router.message(Command(commands=["tod_help"]))
async def cmd_tod_help(message: Message):
    await message.answer("<b>Правда или Действие (ремастер)</b>\n\n/truthordare — создать лобби\n/end_tod — завершить (создатель)\n/tod_help — помощь\n\nХод: выбрать задание — выполнить — Далее.", parse_mode="HTML")
