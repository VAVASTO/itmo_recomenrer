#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to run ITMO Curriculum Telegram Bot
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Добавляем текущую директорию в путь для импорта модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram_bot import main

if __name__ == "__main__":
    try:
        print("🤖 Запуск ITMO Curriculum Bot...")
        print("Для остановки нажмите Ctrl+C")
        print("-" * 50)
        
        main()
        
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        logging.error(f"Bot startup error: {e}")
        sys.exit(1)