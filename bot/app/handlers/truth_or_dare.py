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

MODE_CLOCKWISE = "clockwise"
MODE_ANYONE = "anyone"
RULES_WITH = "with_rules"
RULES_WITHOUT = "no_rules"

class TruthOrDareGame:
    def __init__(self, chat_id: int, players: List[int], player_names: Dict[int,str], creator_id: int, mode: str, rules_mode: str):
        self.chat_id = chat_id
        self.players = players
        self.player_names = player_names
        self.creator_id = creator_id
        self.mode = mode  # clockwise | anyone
        self.rules_mode = rules_mode  # with_rules | no_rules
        self.current_index = 0
        self.passes_used = {pid:0 for pid in players}
        self.phase = "waiting_action"  # waiting_action | select_target | task_active
        self.current_task: str | None = None
        self.current_task_type: str | None = None
        self.target_player_id: int | None = None
    def current_player_id(self): return self.players[self.current_index]
    def current_player_name(self): return self.player_names.get(self.current_player_id(), f"Игрок {self.current_player_id()}")
    def next_player(self):
        self.current_index = (self.current_index + 1) % len(self.players)
        self.phase = "waiting_action"; self.current_task=None; self.current_task_type=None
    def pass_available(self, pid:int):
        if self.rules_mode == RULES_WITH:
            return self.passes_used.get(pid,0) < 1  # один пас
        # без правил пасов бесконечно
        return True
    def use_pass(self, pid:int): self.passes_used[pid]= self.passes_used.get(pid,0)+1

lobbies: Dict[int, dict] = {}
active_games: Dict[int, TruthOrDareGame] = {}
waiting_for_input: Dict[int, dict] = {}

def lobby_keyboard(is_creator: bool, mode: str, rules: str):
    kb=InlineKeyboardBuilder(); kb.button(text="Присоединиться", callback_data="tod:lobby:join")
    mode_label = "Режим: По кругу" if mode == MODE_CLOCKWISE else "Режим: Кому угодно"
    rules_label = "Правила: Вкл" if rules == RULES_WITH else "Правила: Выкл"
    if is_creator:
        kb.button(text=mode_label, callback_data="tod:lobby:mode")
        kb.button(text=rules_label, callback_data="tod:lobby:rules")
        kb.button(text="Старт", callback_data="tod:lobby:start")
        kb.button(text="Отмена", callback_data="tod:lobby:cancel")
        kb.adjust(2,2)
    else:
        kb.adjust(1)
    return kb
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

def waiting_task_keyboard():
    kb=InlineKeyboardBuilder(); kb.button(text="Задание выполнено", callback_data="tod:done")
    return kb

def mention_name(uid:int, name:str): return f"<a href='tg://user?id={uid}'>{name}</a>"
def render_lobby_text(lobby:dict):
    lines=["🎉 <b>Лобби 'Правда или Действие'</b>",""]
    mode_txt = "По кругу ⏱" if lobby['mode']==MODE_CLOCKWISE else "Кому угодно 🎯"
    rules_txt = "С правилами ✅ (1 пас)" if lobby['rules']==RULES_WITH else "Без правил ♾ (пасы беск.)"
    lines.append(f"⚙️ Режим: <b>{mode_txt}</b>")
    lines.append(f"🧷 Правила: <b>{rules_txt}</b>")
    lines.append("")
    lines.append(f"👥 Игроки ({len(lobby['players'])}):")
    for pid in lobby['players']:
        nm = lobby['player_names'][pid]
        lines.append(f"• {mention_name(pid, nm)}")
    lines.append("\nСоздатель может переключать режим и стартовать игру.")
    return "\n".join(lines)
def random_truth(): return random.choice(TRUTHS)
def random_dare(): return random.choice(DARES)

@router.message(Command(commands=["truthordare","tod"]))
async def cmd_truth_or_dare(message: Message):
    chat_id=message.chat.id; user_id=message.from_user.id
    if message.chat.type not in {"group","supergroup"}: return await message.answer("Эта игра только в группах")
    if chat_id in active_games: return await message.answer("Игра уже идёт")
    if chat_id in lobbies: return await message.answer("Лобби уже создано")
    name= message.from_user.first_name or message.from_user.username or "Игрок"
    lobby={"creator":user_id,"players":[user_id],"player_names":{user_id:name},"message_id":None, "mode": MODE_CLOCKWISE, "rules": RULES_WITH}
    lobbies[chat_id]=lobby
    msg= await message.answer(render_lobby_text(lobby), parse_mode="HTML", reply_markup=lobby_keyboard(True, lobby['mode'], lobby['rules']).as_markup())
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
                lobby['players'].append(user_id)
                lobby['player_names'][user_id]= cb.from_user.first_name or cb.from_user.username or "Игрок"
                await cb.answer("Готово ✅")
            else:
                await cb.answer("Вы уже в лобби")
            # ВАЖНО: групповое сообщение одно для всех, поэтому всегда показываем клавиатуру создателя,
            # иначе при входе обычного игрока пропадают кнопки 'Старт' / 'Правила' / 'Режим'.
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=lobby['message_id'],
                    text=render_lobby_text(lobby),
                    reply_markup=lobby_keyboard(True, lobby['mode'], lobby['rules']).as_markup(),
                    parse_mode="HTML"
                )
            except Exception:
                pass
        elif sub=="mode":
            if user_id!=lobby['creator']: return await cb.answer("Только создатель")
            lobby['mode'] = MODE_ANYONE if lobby['mode']==MODE_CLOCKWISE else MODE_CLOCKWISE
            try:
                await bot.edit_message_text(chat_id=chat_id, message_id=lobby['message_id'], text=render_lobby_text(lobby), reply_markup=lobby_keyboard(True, lobby['mode'], lobby['rules']).as_markup(), parse_mode="HTML")
            except Exception: pass
            return await cb.answer("Режим переключен")
        elif sub=="rules":
            if user_id!=lobby['creator']: return await cb.answer("Только создатель")
            lobby['rules'] = RULES_WITHOUT if lobby['rules']==RULES_WITH else RULES_WITH
            try:
                await bot.edit_message_text(chat_id=chat_id, message_id=lobby['message_id'], text=render_lobby_text(lobby), reply_markup=lobby_keyboard(True, lobby['mode'], lobby['rules']).as_markup(), parse_mode="HTML")
            except Exception: pass
            return await cb.answer("Правила переключены")
        elif sub=="start":
            if user_id!=lobby['creator']: return await cb.answer("Не ты создавал")
            if len(lobby['players'])<2: return await cb.answer("Минимум 2 игрока")
            game= TruthOrDareGame(chat_id,lobby['players'],lobby['player_names'],lobby['creator'], lobby['mode'], lobby['rules'])
            active_games[chat_id]=game; del lobbies[chat_id]
            mode_txt = "По кругу ⏱" if game.mode==MODE_CLOCKWISE else "Кому угодно 🎯"
            rules_txt = "1 пас (осторожно)" if game.rules_mode==RULES_WITH else "Неограниченные пасы"
            await cb.message.edit_text(
                f"🚀 <b>Игра началась!</b>\n\n" \
                f"Режим: <b>{mode_txt}</b>\n" \
                f"Правила: <b>{rules_txt}</b>\n" \
                f"Ход: {mention_name(game.current_player_id(), game.current_player_name())}\nВыбирай действие.",
                parse_mode="HTML", reply_markup=action_keyboard(game).as_markup())
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
            game.current_task_type=action
            # CLOCKWISE: секретный ввод / авто случайное
            if game.mode==MODE_CLOCKWISE:
                target = game.players[(game.current_index+1)%len(game.players)]
                game.target_player_id = target
                if action == "random":
                    # уже преобразовано в truth/dare выше
                    game.current_task = random_truth() if game.current_task_type=="truth" else random_dare()
                    game.phase="task_active"
                    await cb.message.edit_text(
                        f"🎲 Случайное задание отправлено {mention_name(target, game.player_names[target])} в личку (если бот не может написать — пусть нажмёт /start в ЛС).\n\nОжидаем выполнения…",
                        parse_mode="HTML"
                    )
                    # попытка отправить приватно
                    try:
                        await cb.bot.send_message(target,
                            f"🤫 Вам пришло <b>{'Правда' if game.current_task_type=='truth' else 'Действие'}</b> (случайное):\n\n{game.current_task}\n\nКогда выполните — вернитесь в чат и нажмите 'Задание выполнено'.",
                            parse_mode="HTML")
                        await cb.bot.send_message(game.chat_id,
                            f"📨 {mention_name(target, game.player_names[target])} получил(а) секретное задание!",
                            parse_mode="HTML")
                    except Exception:
                        await cb.bot.send_message(game.chat_id,
                            f"⚠️ Не удалось отправить ЛС {mention_name(target, game.player_names[target])}. Он/она должен(а) написать боту /start в ЛС.",
                            parse_mode="HTML")
                    # показать кнопки ожидания
                    await cb.message.answer(
                        f"⏳ Ждём {mention_name(target, game.player_names[target])}…",
                        parse_mode="HTML",
                        reply_markup=waiting_task_keyboard().as_markup()
                    )
                    return await cb.answer()
                else:
                    # попросить текущего игрока в ЛС ввести содержимое
                    game.phase = "awaiting_content"
                    waiting_for_input[user_id] = {
                        "type": game.current_task_type,
                        "target": target,
                        "chat_id": chat_id
                    }
                    await cb.answer("Жду текст в ЛС")
                    try:
                        await cb.bot.send_message(user_id,
                            f"✍️ Введи {'вопрос (Правда)' if action=='truth' else 'задание (Действие)'} для игрока {game.player_names[target]}\n\nОтправь одним сообщением.")
                    except Exception:
                        await cb.message.answer("⚠️ Напиши боту в ЛС /start чтобы я мог принять текст.")
                    await cb.message.edit_text(
                        f"🕵️ {mention_name(user_id, game.player_names[user_id])} пишет секретное задание для {mention_name(target, game.player_names[target])}…",
                        parse_mode="HTML"
                    )
                    return
            # ANYONE: сначала выбор цели
            if game.mode==MODE_ANYONE:
                game.phase="select_target"
                # строим клавиатуру игроков
                kb=InlineKeyboardBuilder()
                for pid in game.players:
                    if pid==user_id: continue
                    kb.button(text=game.player_names[pid], callback_data=f"tod:target:{pid}")
                kb.button(text="Отмена", callback_data="tod:act:cancel")
                kb.adjust(2)
                label = "Правда" if action=="truth" else "Действие"
                await cb.message.edit_text(
                    f"🎯 Выберите цель для: <b>{label}</b>\n",
                    parse_mode="HTML", reply_markup=kb.as_markup())
                return await cb.answer()
            # CLOCKWISE — цель следующий игрок
            target = game.players[(game.current_index+1)%len(game.players)]
            game.target_player_id = target
            game.current_task = random_truth() if action=="truth" else random_dare()
            game.phase="task_active"
            label = "Правда" if action=="truth" else "Действие"
            await cb.message.edit_text(
                f"🎲 <b>{label}</b> для {mention_name(target, game.player_names[target])}:\n\n<i>{game.current_task}</i>\n\nПосле выполнения нажмите 'Далее'.",
                parse_mode="HTML", reply_markup=next_keyboard(game).as_markup())
            return await cb.answer()
        return
    # выбор цели в режиме ANYONE
    if parts[1]=="target":
        if chat_id not in active_games: return await cb.answer()
        game=active_games[chat_id]
        if user_id!=game.current_player_id(): return await cb.answer("Не твой ход")
        if game.mode!=MODE_ANYONE or game.phase!="select_target": return await cb.answer()
        try:
            target_id = int(parts[2])
        except ValueError:
            return await cb.answer()
        if target_id not in game.players or target_id==user_id: return await cb.answer()
        game.target_player_id = target_id
        game.current_task = random_truth() if game.current_task_type=="truth" else random_dare()
        game.phase="task_active"
        label = "Правда" if game.current_task_type=="truth" else "Действие"
        await cb.message.edit_text(
            f"🎲 <b>{label}</b> для {mention_name(target_id, game.player_names[target_id])}:\n\n<i>{game.current_task}</i>\n\nПосле выполнения нажмите 'Далее'.",
            parse_mode="HTML", reply_markup=next_keyboard(game).as_markup())
        return await cb.answer()
    if parts[1]=="next":
        if chat_id not in active_games: return await cb.answer()
        game=active_games[chat_id]
        if user_id!=game.current_player_id(): return await cb.answer("Не ты выполнял")
        if game.phase!="task_active": return await cb.answer()
        # после выполнения: ход получает тот, кто был целью (и только потом двигается на следующем раунде)
        if game.target_player_id and game.target_player_id in game.players:
            game.current_index = game.players.index(game.target_player_id)
        # сброс состояния без продвижения дальше
        game.phase = "waiting_action"
        game.current_task = None
        game.current_task_type = None
        game.target_player_id = None
        await cb.message.edit_text(f"✅ Задание завершено! Теперь ход: {mention_name(game.current_player_id(), game.current_player_name())}", parse_mode="HTML", reply_markup=action_keyboard(game).as_markup()); return await cb.answer()
    if parts[1]=="done":
        if chat_id not in active_games: return await cb.answer()
        game=active_games[chat_id]
        # кнопку 'Задание выполнено' должен жать цель
        if game.target_player_id != user_id: return await cb.answer("Не ты цель")
        if game.phase!="task_active": return await cb.answer()
        # аналогично next
        game.current_index = game.players.index(user_id)
        game.phase = "waiting_action"
        game.current_task=None; game.current_task_type=None; game.target_player_id=None
        await cb.message.edit_text(f"✅ {mention_name(user_id, game.player_names[user_id])} выполнил(а) задание! Ход: {mention_name(game.current_player_id(), game.current_player_name())}", parse_mode="HTML", reply_markup=action_keyboard(game).as_markup())
        return await cb.answer("Готово")
    await cb.answer()

@router.message()
async def private_task_input(message: Message, bot: Bot):
    # Обрабатываем приватный ввод задания
    if message.chat.type != 'private':
        return
    uid = message.from_user.id
    if uid not in waiting_for_input:
        return
    info = waiting_for_input.pop(uid)
    chat_id = info['chat_id']
    if chat_id not in active_games:
        return
    game = active_games[chat_id]
    # только если всё ещё его ход и ожидается контент
    if game.current_player_id() != uid or game.phase != 'awaiting_content':
        return
    target = info['target']
    game.target_player_id = target
    game.current_task_type = info['type']
    game.current_task = message.text.strip()
    game.phase = 'task_active'
    # отправка цели в ЛС
    try:
        await bot.send_message(target,
            f"🤫 Вам пришло секретное <b>{'Правда' if game.current_task_type=='truth' else 'Действие'}</b>:\n\n{game.current_task}\n\nКогда выполните — вернитесь в чат и нажмите 'Задание выполнено'.",
            parse_mode='HTML')
    except Exception:
        await bot.send_message(chat_id,
            f"⚠️ Не удалось отправить ЛС {mention_name(target, game.player_names[target])}. Он/она должен(а) написать боту /start в ЛС.",
            parse_mode='HTML')
    # уведомление в чате
    await bot.send_message(chat_id,
        f"📨 {mention_name(target, game.player_names[target])} получил(а) секретное задание!",
        parse_mode='HTML')
    await bot.send_message(chat_id,
        f"⏳ Ждём {mention_name(target, game.player_names[target])}…",
        parse_mode='HTML', reply_markup=waiting_task_keyboard().as_markup())
    # подтверждение автору
    await message.answer("✅ Отправлено цели. Ждём выполнения.")

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
    await message.answer(
        "<b>Правда или Действие (ремастер)</b>\n\n"
        "/truthordare — создать лобби\n"
        "Переключатели: режим (по кругу / кому угодно), правила (1 пас / бесконечно).\n"
        "/end_tod — завершить (создатель)\n"
        "/tod_help — помощь\n\n"
        "Ход: выбрать задание — (выбрать цель если нужно) — выполнить — Далее.",
        parse_mode="HTML")
