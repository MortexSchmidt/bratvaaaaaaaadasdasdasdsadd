from __future__ import annotations
from aiogram import Router
from aiogram.types import Message
import re
import random
import logging
import requests
import json
from openai import OpenAI
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
    Get real AI response from OpenAI API
    """
    try:
        # Check if API key exists
        if not config.openai_api_key:
            logging.error("OpenAI API key not found in config")
            return "Извини, у меня не настроен ИИ. Добавь OPENAI_API_KEY в .env файл."

        logging.info(f"OpenAI API key found, length: {len(config.openai_api_key)}")

        # Initialize OpenAI client
        client = OpenAI(api_key=config.openai_api_key)

        # Create system message for Milana's personality
        system_message = """Ты - Милана, дружелюбная и умная девушка-помощник в Telegram боте.
        Ты всегда вежливая, позитивная и готова помочь. Ты общаешься на русском языке.
        Ты можешь помогать с домашними заданиями, объяснять сложные темы, отвечать на вопросы.
        Будь естественной в общении, как настоящая подруга."""

        # Create user message
        user_message = f"Меня зовут {user_name}. Мой вопрос: {request_text}"

        logging.info(f"Sending request to OpenAI for user {user_name}: {request_text[:50]}...")

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=500,
                temperature=0.7
            )
        except Exception as api_error:
            logging.error(f"OpenAI API error: {type(api_error).__name__}: {api_error}")
            # Try with a different model if gpt-3.5-turbo fails
            if "gpt-3.5-turbo" in str(api_error):
                logging.info("Trying with gpt-4 model...")
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message}
                    ],
                    max_tokens=500,
                    temperature=0.7
                )
            else:
                raise api_error

        ai_response = response.choices[0].message.content.strip()
        logging.info(f"Received response from OpenAI: {ai_response[:50]}...")
        return ai_response

    except Exception as e:
        logging.error(f"Error calling OpenAI API: {type(e).__name__}: {e}")
        # Try Hugging Face as fallback
        logging.info("Trying Hugging Face API as fallback...")
        hf_response = get_huggingface_response(request_text, user_name)
        if hf_response:
            return hf_response
        return "Извини, у меня проблемы с ИИ. Попробуй позже или спроси что-то попроще."


def get_huggingface_response(request_text: str, user_name: str) -> str:
    """
    Get response from Hugging Face Inference API (free alternative)
    """
    if not config.huggingface_token:
        logging.error("Hugging Face token not found")
        return None

    try:
        # Use a free model from Hugging Face (try distilgpt2 - smaller and available)
        model_name = "distilgpt2"

        headers = {
            "Authorization": f"Bearer {config.huggingface_token}",
            "Content-Type": "application/json"
        }

        # Simple prompt for GPT-2
        prompt = f"Ты - Милана, дружелюбная помощница. Пользователь {user_name} спрашивает: {request_text}\nМилана отвечает:"

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 500,
                "temperature": 0.7,
                "do_sample": True,
                "return_full_text": False
            }
        }

        logging.info(f"Sending request to Hugging Face for user {user_name}")

        response = requests.post(
            f"https://api-inference.huggingface.co/models/{model_name}",
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                generated_text = result[0].get("generated_text", "")
                # Clean up the response
                clean_response = generated_text.replace(prompt, "").strip()
                logging.info(f"Received response from Hugging Face: {clean_response[:50]}...")
                return clean_response
            else:
                logging.error(f"Unexpected response format from Hugging Face: {result}")
                return None
        elif response.status_code == 429:
            logging.warning("Hugging Face rate limit exceeded")
            return None
        else:
            logging.error(f"Hugging Face API error: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logging.error(f"Error calling Hugging Face API: {type(e).__name__}: {e}")
        return None