#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration file for ITMO Telegram Bot
"""

import os
from typing import Dict, Any

# Попытка импорта секретов (если файл существует)
try:
    from secrets import TELEGRAM_BOT_TOKEN, YANDEX_FOLDER_ID, YANDEX_AUTH_TOKEN
except ImportError:
    # Если файл secrets.py не найден, используем переменные окружения или заглушки
    TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
    YANDEX_FOLDER_ID = "YOUR_YANDEX_FOLDER_ID"
    YANDEX_AUTH_TOKEN = "YOUR_YANDEX_AUTH_TOKEN"

# Telegram Bot Configuration
TELEGRAM_CONFIG = {
    'token': os.getenv('TELEGRAM_BOT_TOKEN', TELEGRAM_BOT_TOKEN),
    'webhook_url': os.getenv('WEBHOOK_URL', ''),
    'use_webhook': os.getenv('USE_WEBHOOK', 'false').lower() == 'true',
    'max_message_length': 4000,
    'timeout': 30
}

# YandexGPT Configuration
YANDEX_CONFIG = {
    'folder_id': os.getenv('YANDEX_FOLDER_ID', YANDEX_FOLDER_ID),
    'auth_token': os.getenv('YANDEX_AUTH_TOKEN', YANDEX_AUTH_TOKEN),
    'model_name': 'yandexgpt',
    'temperature': 0.3,
    'max_tokens': 2000
}

# Bot Behavior Configuration
BOT_CONFIG = {
    'response_timeout': 30,
    'max_retries': 3,
    'retry_delay': 2,
    'log_level': 'INFO',
    'log_file': 'telegram_bot.log',
    'conversation_cache_size': 1000,
    'conversation_timeout': 3600  # 1 hour
}

# System Prompts
SYSTEM_PROMPTS = {
    'main': """Ты - помощник по учебным планам ИТМО для магистерских программ "Искусственный интеллект" и "Управление ИИ-продуктами".

ВАЖНЫЕ ПРАВИЛА:
1. Отвечай СТРОГО по предоставленным учебным планам
2. Если информации нет в учебных планах - честно скажи об этом
3. Не придумывай информацию, которой нет в планах
4. Всегда указывай конкретные названия дисциплин, количество зачетных единиц и часов
5. Если спрашивают про конкретную дисциплину - найди её в планах и дай точную информацию
6. Отвечай на русском языке
7. Будь конкретным и информативным
8. Если вопрос не касается учебных планов ИТМО, вежливо перенаправь к теме учебных планов

КРИТИЧЕСКИ ВАЖНО - ФОРМАТИРОВАНИЕ ДЛЯ TELEGRAM:
- ОБЯЗАТЕЛЬНО используй <b>жирный текст</b> (НЕ **текст**) для выделения названий программ и важных терминов
- ОБЯЗАТЕЛЬНО используй <i>курсив</i> (НЕ *текст*) для выделения названий дисциплин
- ОБЯЗАТЕЛЬНО используй <code>код</code> для выделения цифр (зачетные единицы, часы)
- Используй • для списков дисциплин
- Используй 📚 📊 🎓 и другие эмодзи для улучшения читаемости
- Структурируй ответ с абзацами и переносами строк
- Для больших списков группируй информацию по семестрам или блокам

ЗАПРЕЩЕНО использовать:
- **жирный** (двойные звездочки) - НЕ РАБОТАЕТ в Telegram
- *курсив* (одинарные звездочки) - НЕ РАБОТАЕТ в Telegram
- ```код``` (тройные обратные кавычки) - используй <code>код</code>

УЧЕБНЫЕ ПЛАНЫ:

{curriculum_text}

Отвечай только на основе этой информации с правильным форматированием для Telegram.""",
    
    'welcome': """🎓 Добро пожаловать в бот по учебным планам ИТМО!

Я помогу вам найти информацию о магистерских программах:
• <b>Искусственный интеллект</b>
• <b>Управление ИИ-продуктами</b>

Вы можете спросить:
• Какие дисциплины есть в программе?
• Сколько зачетных единиц у дисциплины?
• В каком семестре изучается предмет?
• Какие практики предусмотрены?
• И многое другое!

Просто задайте свой вопрос! 💬""",
    
    'help': """📚 <b>Помощь по боту</b>

<b>Доступные программы:</b>
• Искусственный интеллект
• Управление ИИ-продуктами/AI Product

<b>Примеры вопросов:</b>
• "Какие дисциплины по машинному обучению есть в программе ИИ?"
• "Сколько зачетных единиц у дисциплины 'Глубокое обучение'?"
• "Какие практики в 3 семестре?"
• "Расскажи про программу Управление ИИ-продуктами"

<b>Команды:</b>
/start - начать работу
/help - эта справка

Задавайте вопросы на русском языке! 🇷🇺""",
    
    'error': "Извините, произошла ошибка при обработке вашего вопроса. Попробуйте позже.",
    'no_response': "Извините, не удалось получить ответ от модели. Попробуйте позже."
}

# Validation functions
def validate_config() -> Dict[str, Any]:
    """Validate configuration and return status"""
    issues = []
    
    # Check Telegram token
    if not TELEGRAM_CONFIG['token'] or TELEGRAM_CONFIG['token'] == 'YOUR_TELEGRAM_TOKEN':
        issues.append("Telegram bot token not configured")
    
    # Check YandexGPT credentials
    if not YANDEX_CONFIG['folder_id'] or YANDEX_CONFIG['folder_id'] == 'YOUR_FOLDER_ID':
        issues.append("YandexGPT folder_id not configured")
    
    if not YANDEX_CONFIG['auth_token'] or YANDEX_CONFIG['auth_token'] == 'YOUR_AUTH_TOKEN':
        issues.append("YandexGPT auth_token not configured")
    
    return {
        'valid': len(issues) == 0,
        'issues': issues
    }

def get_config_summary() -> str:
    """Get configuration summary for logging"""
    return f"""
Bot Configuration:
- Telegram Token: {'✓ Set' if TELEGRAM_CONFIG['token'] else '✗ Missing'}
- YandexGPT Folder ID: {'✓ Set' if YANDEX_CONFIG['folder_id'] else '✗ Missing'}
- YandexGPT Auth Token: {'✓ Set' if YANDEX_CONFIG['auth_token'] else '✗ Missing'}
- Log Level: {BOT_CONFIG['log_level']}
- Max Message Length: {TELEGRAM_CONFIG['max_message_length']}
- Model Temperature: {YANDEX_CONFIG['temperature']}
"""