from __future__ import annotations
from aiogram import Router
from aiogram.types import Message
import re
import random
import logging
from app.config import load_config

router = Router(name="ai")
config = load_config()


# Pattern to detect when someone is talking to Milana
MILANA_PATTERNS = [
    # Direct mentions and questions to Milana
    r"^милан[а|у|ой|е][,?\s]",
    r"^милан[а|у|ой|е]$",
    r".*милан[а|у|ой|е].*[,?\s]*$",

    # Questions directed at Milana
    r".*милан[а|у|ой|е]\??\s*$",
    r"^милан[а|у|ой|е].*\?$",

    # Common requests to Milana
    r".*милан[а|у|ой|е].*помоги.*",
    r".*милан[а|у|ой|е].*домашк[а|у|ой|е|и].*",
    r".*милан[а|у|ой|е].*задани[е|ю|я|ем|и|й].*",
    r".*милан[а|у|ой|е].*учеб[а|у|ой|е|ы|ников|ника].*",
    r".*помоги.*милан[а|у|ой|е].*",
    r".*милан[а|у|ой|е].*не могу.*",
    r".*милан[а|у|ой|е].*не знаю.*",
    r".*милан[а|у|ой|е].*объясни.*",
    r".*объясни.*милан[а|у|ой|е].*",
    r".*милан[а|у|ой|е].*что.*",
    r".*милан[а|у|ой|е].*как.*",
    r".*милан[а|у|ой|е].*почему.*",
    r".*милан[а|у|ой|е].*зачем.*",
]

@router.message(lambda message: message.text and any(re.match(pattern, message.text.lower()) for pattern in MILANA_PATTERNS))
async def ai_milana(message: Message):
    try:
        # Get user info for personalized response
        user_name = message.from_user.first_name or "друг"
        user_mention = f"<a href='tg://user?id={message.from_user.id}'>{user_name}</a>"

        # Extract the request from the message
        user_text = message.text

        # Try to get a more specific request by removing the mention of Milana
        request_text = user_text
        for pattern in MILANA_PATTERNS:
            match = re.match(pattern, user_text.lower())
            if match:
                # Try to get a cleaner request text
                request_text = re.sub(r"милан[а|у|ой|е]", "", user_text, flags=re.IGNORECASE).strip()
                break

        # Get real AI response
        ai_response = get_ai_response(request_text, user_name)

        # Format the final response with user mention
        if ai_response.startswith("Извини") or "проблемы" in ai_response:
            # Error message - don't add extra formatting
            final_response = ai_response
        else:
            # Normal response - add user mention at the beginning
            final_response = f"{user_mention}, {ai_response}"

        # Send the response
        await message.answer(final_response, parse_mode="HTML")

    except Exception as e:
        logging.error(f"Error in AI Milana handler: {e}")
        # Fallback response with user mention
        user_name = message.from_user.first_name or "друг"
        user_mention = f"<a href='tg://user?id={message.from_user.id}'>{user_name}</a>"
        await message.answer(f"{user_mention}, извини, у меня технические проблемы с ИИ. Попробуй позже.", parse_mode="HTML")

def get_ai_response(request_text: str, user_name: str) -> str:
    """
    Get simulated AI response with varied templates
    """
    # Analyze the request to give appropriate response
    request_lower = request_text.lower()

    # Greetings and simple requests
    if any(word in request_lower for word in ["привет", "здравствуй", "добро пожаловать", "хай", "hello", "hi"]):
        greetings = [
            f"Привет, {user_name}! Чем могу помочь сегодня?",
            f"Здравствуй, {user_name}! Рад тебя видеть!",
            f"Приветик! Что будем делать сегодня?",
            f"Хай, {user_name}! Готова к новым приключениям!",
        ]
        return random.choice(greetings)

    # Questions about help
    elif any(word in request_lower for word in ["помоги", "помощь", "не могу", "как", "что делать"]):
        help_responses = [
            f"Конечно помогу, {user_name}! Расскажи подробнее, что случилось?",
            f"Не переживай, {user_name}, вместе разберемся! Что именно не получается?",
            f"Я здесь чтобы помочь! Опиши проблему и найдем решение.",
            f"Расскажи мне подробнее, {user_name}, и я постараюсь помочь!",
        ]
        return random.choice(help_responses)

    # Math related questions
    elif any(word in request_lower for word in ["матем", "счет", "цифр", "чисел", "пример"]):
        math_responses = [
            f"Математика - это интересно! Покажи задачу, {user_name}, разберем вместе.",
            f"Люблю решать примеры! Расскажи, что за задача у тебя?",
            f"Математика не так сложна, как кажется. Давай посмотрим вместе!",
            f"Покажи пример, {user_name}, и мы его решим шаг за шагом!",
        ]
        return random.choice(math_responses)

    # School/homework related
    elif any(word in request_lower for word in ["домашк", "урок", "школа", "задани", "учеб"]):
        homework_responses = [
            f"Домашка? Я помогу! Расскажи, что именно нужно сделать.",
            f"Уроки могут быть сложными, но мы справимся! Что за предмет?",
            f"Домашнее задание - это важно! Давай разберемся вместе.",
            f"Покажи задание, {user_name}, и я постараюсь объяснить!",
        ]
        return random.choice(homework_responses)

    # Questions and curiosity
    elif any(request_lower.startswith(word) for word in ["что ", "как ", "почему ", "зачем ", "когда ", "где "]):
        question_responses = [
            f"Хороший вопрос, {user_name}! Давай разберемся вместе.",
            f"Интересно! Попробую объяснить как можно проще.",
            f"Вопросы - это всегда хорошо! Слушаю внимательно.",
            f"Давай подумаем вместе над этим вопросом!",
        ]
        return random.choice(question_responses)

    # Gratitude and positive
    elif any(word in request_lower for word in ["спасибо", "благодар", "круто", "отлично", "молодец"]):
        thanks_responses = [
            f"Пожалуйста, {user_name}! Рада была помочь!",
            f"Всегда рада помочь таким как ты!",
            f"Обращайся в любое время! Буду рада помочь снова.",
            f"Рада что смогла помочь, {user_name}!",
        ]
        return random.choice(thanks_responses)

    # General conversation
    else:
        general_responses = [
            f"Интересная тема, {user_name}! Расскажи подробнее.",
            f"Звучит интересно! Что именно тебя беспокоит?",
            f"Я готова выслушать и помочь! О чем хочешь поговорить?",
            f"Расскажи мне больше, {user_name}, я постараюсь помочь!",
            f"Люблю узнавать новое! Поделись своими мыслями.",
            f"С удовольствием послушаю тебя! Что на уме?",
            f"Каждый вопрос важен! Делись своими мыслями.",
            f"Я здесь чтобы помочь! Расскажи, что случилось.",
        ]
        return random.choice(general_responses)

