"""
Модуль для интеграции улучшенной Mini-App "Правда или Действие 2.0" с ботом
"""
from aiogram import Router

# Инициализация роутера для Mini-App
router = Router(name="truth_or_dare_mini_app")

__all__ = ["router"]