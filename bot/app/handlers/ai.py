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
    "Я бы с радостью помог, но сейчас немного занята. Попробуй позже",
    "Хм, неплохой вопрос. Что ты уже знаешь об этом?",
    "Я не эксперт в этом, но могу попробовать помочь. Расскажи подробнее",
    "Отличный вопрос! Я посмотрю, что можно сделать",
    "Я бы хотела помочь, но мне нужно больше информации",
    "Это заставляет задуматься. Что ты хочешь узнать?",
]

# Pattern to detect when someone is asking Milana for help
MILANA_PATTERNS = [
    r".*милан[а|у|ой|е].*помоги.*",
    r".*милан[а|у|ой|е].*домашк[а|у|ой|е|и].*",
    r".*милан[а|у|ой|е].*задани[е|ю|я|ем|и|й].*",
    r".*милан[а|у|ой|е].*учеб[а|у|ой|е|ы|ников|ника].*",
    r".*помоги.*милан[а|у|ой|е].*",
    r".*милан[а|у|ой|е].*не могу.*",
    r".*милан[а|у|ой|е].*не знаю.*",
    r".*милан[а|у|ой|е].*объясни.*",
    r".*объясни.*милан[а|у|ой|е].*",
]

@router.message(lambda message: message.text and any(re.match(pattern, message.text.lower()) for pattern in MILANA_PATTERNS))
async def ai_milana(message: Message):
    try:
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
        
        # Send the response
        await message.answer(response)
        
    except Exception as e:
        logging.error(f"Error in AI Milana handler: {e}")
        # Fallback response
        await message.answer("Извини, у меня сейчас технические проблемы. Попробуй позже.")

def get_simulated_ai_response(request_text: str) -> str:
    """
    Simulate an AI response. In a real implementation, this would connect to an AI API.
    """
    # If we have a specific request, we can customize the response
    if "домашк" in request_text.lower() or "задани" in request_text.lower():
        homework_responses = [
            f"С домашкой по '{request_text}'? Давай разберемся вместе. Что именно тебе непонятно?",
            f"Домашнее задание по '{request_text}' звучит интересно. С чего хочешь начать?",
            f"Я могу помочь с '{request_text}'. Расскажи, какие темы вызывают трудности?",
            f"С радостью помогу с '{request_text}'. Покажи, где застрял?",
        ]
        return random.choice(homework_responses)
    elif "матем" in request_text.lower():
        math_responses = [
            "Математика - это мое любимое! Давай посмотрим на задачу.",
            "С математикой я точно смогу помочь. Что за пример?",
            "Математика? Интересно! Покажи условие задачи.",
        ]
        return random.choice(math_responses)
    elif "русск" in request_text.lower():
        russian_responses = [
            "С русским языком помогу! Что нужно - сочинение, диктант или разбор предложения?",
            "Русский язык - моя страсть! С чем нужна помощь?",
            "Давай разберем грамматику вместе. Что именно не понятно?",
        ]
        return random.choice(russian_responses)
    else:
        # General response
        return random.choice(EXAMPLE_RESPONSES)