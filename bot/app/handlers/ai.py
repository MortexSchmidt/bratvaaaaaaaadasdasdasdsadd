from __future__ import annotations
from aiogram import Router
from aiogram.types import Message
import re
import random
import logging

router = Router(name="ai")

# Some example responses for when we can't reach a real AI API
EXAMPLE_RESPONSES = [
    "Я подумаю над этим и дам тебе знать позже",
    "Интересный вопрос! Дай мне немного времени",
    "Я бы с радостью помогла, но сейчас немного занята. Попробуй позже",
    "Хм, неплохой вопрос. Что ты уже знаешь об этом?",
    "Я не эксперт в этом, но могу попробовать помочь. Расскажи подробнее",
    "Отличный вопрос! Я посмотрю, что можно сделать",
    "Я бы хотела помочь, но мне нужно больше информации",
    "Это заставляет задуматься. Что ты хочешь узнать конкретно?",
    "Звучит интересно! Давай разберемся вместе",
    "Хорошая тема для обсуждения! Поделись мыслями",
]

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

        # For now, we'll use simulated responses since we don't have a real AI API key
        # In a real implementation, you would connect to an AI API like OpenAI here
        response = get_simulated_ai_response(request_text)

        # Add some personality to responses
        personality_responses = [
            f"{user_mention}, {response.lower()}",
            f"{response} {user_mention} 😉",
            f"{user_mention}, давай разберемся! {response.lower()}",
        ]

        # Choose response with some randomness
        final_response = random.choice(personality_responses)

        # Send the response
        await message.answer(final_response, parse_mode="HTML")

    except Exception as e:
        logging.error(f"Error in AI Milana handler: {e}")
        # Fallback response with user mention
        user_name = message.from_user.first_name or "друг"
        user_mention = f"<a href='tg://user?id={message.from_user.id}'>{user_name}</a>"
        await message.answer(f"{user_mention}, извини, у меня технические проблемы. Попробуй позже.", parse_mode="HTML")

def get_simulated_ai_response(request_text: str) -> str:
    """
    Simulate an AI response. In a real implementation, this would connect to an AI API.
    """
    # Clean the request text
    clean_request = request_text.lower().strip()

    # Homework and study related
    if any(word in clean_request for word in ["домашк", "задани", "урок", "учеб"]):
        homework_responses = [
            f"Домашка? Я помогу! Расскажи, что именно нужно сделать с '{clean_request}'.",
            f"С домашним заданием разберемся вместе. Что у тебя за предмет?",
            f"Я люблю помогать с уроками! Покажи задание, разберем по шагам.",
            f"Домашка - это важно! Давай посмотрим, что у тебя не получается.",
        ]
        return random.choice(homework_responses)

    # Math related
    elif any(word in clean_request for word in ["матем", "алгебр", "геометр", "пример", "задач", "уравн"]):
        math_responses = [
            "Математика - это интересно! Покажи задачу, решим вместе.",
            "С числами я на ты! Что за пример нужно решить?",
            "Математика любит терпеливых. Давай разберем задачу шаг за шагом.",
            "Геометрия или алгебра? Я помогу с любым разделом математики!",
        ]
        return random.choice(math_responses)

    # Russian language related
    elif any(word in clean_request for word in ["русск", "литератур", "сочинени", "диктант", "грамматик"]):
        russian_responses = [
            "Русский язык - мой любимый предмет! С чем помочь?",
            "Литература или грамматика? Я готова разбирать любое произведение.",
            "Сочинение или изложение? Давай напишем вместе красивый текст.",
            "Русский язык - это искусство слов. Что нужно разобрать?",
        ]
        return random.choice(russian_responses)

    # Questions starting with что/как/почему/зачем
    elif any(clean_request.startswith(word) for word in ["что ", "как ", "почему ", "зачем "]):
        question_responses = [
            "Хороший вопрос! Давай разберемся вместе.",
            "Интересно узнать! Я помогу найти ответ.",
            "Вопросы - это всегда хорошо. Попробуем разобраться.",
            "Люблю отвечать на вопросы! Слушаю внимательно.",
        ]
        return random.choice(question_responses)

    # General help requests
    elif any(word in clean_request for word in ["помоги", "не могу", "не знаю", "объясни"]):
        help_responses = [
            "Конечно помогу! Расскажи подробнее, что именно нужно.",
            "Не переживай, вместе разберемся. Что случилось?",
            "Я здесь, чтобы помочь! Опиши проблему подробнее.",
            "Помощь нужна? Я готова выслушать и помочь найти решение.",
        ]
        return random.choice(help_responses)

    # Simple greetings or mentions
    elif clean_request in ["", "милана", "милану", "миланой", "милане"]:
        greeting_responses = [
            "Да, я здесь! Чем могу помочь?",
            "Слушаю тебя внимательно. Что нужно?",
            "Я готова помочь! Расскажи, что случилось.",
            "Привет! Чем могу быть полезна сегодня?",
        ]
        return random.choice(greeting_responses)

    else:
        # General response for other topics
        general_responses = [
            f"Интересная тема '{clean_request}'! Давай обсудим.",
            "Хм, звучит интересно. Расскажи подробнее!",
            "Я люблю узнавать новое. Что ты хочешь обсудить?",
            "Тема интересная! Поделись деталями, я постараюсь помочь.",
        ]
        return random.choice(general_responses)