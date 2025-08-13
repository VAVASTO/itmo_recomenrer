#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram bot for ITMO curriculum Q&A using YandexGPT
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime

import requests
from yandex_cloud_ml_sdk import YCloudML

from pdf_processor import PDFProcessor
from bot_config import (
    TELEGRAM_CONFIG, YANDEX_CONFIG, BOT_CONFIG, SYSTEM_PROMPTS,
    validate_config, get_config_summary
)

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, BOT_CONFIG['log_level']),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(BOT_CONFIG['log_file'], encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ITMOCurriculumBot:
    """Telegram bot for ITMO curriculum questions"""
    
    def __init__(self):
        # Валидация конфигурации
        config_status = validate_config()
        if not config_status['valid']:
            logger.error("Configuration validation failed:")
            for issue in config_status['issues']:
                logger.error(f"  - {issue}")
            raise ValueError("Invalid configuration")
        
        # Загрузка конфигурации
        self.telegram_token = TELEGRAM_CONFIG['token']
        self.yandex_folder_id = YANDEX_CONFIG['folder_id']
        self.yandex_auth_token = YANDEX_CONFIG['auth_token']
        
        # Инициализация процессора PDF
        self.pdf_processor = PDFProcessor()
        
        # Инициализация YandexGPT SDK
        self.yandex_sdk = YCloudML(
            folder_id=self.yandex_folder_id,
            auth=self.yandex_auth_token,
        )
        
        # Offset для получения обновлений
        self.update_offset = 0
        
        # Кэш для хранения контекста разговоров
        self.conversation_cache = {}
        
        logger.info("ITMO Curriculum Bot initialized")
        logger.info(get_config_summary())
    
    def get_system_prompt(self) -> str:
        """Получить системный промпт с учебными планами"""
        curriculum_text = self.pdf_processor.get_curriculum_text()
        return SYSTEM_PROMPTS['main'].format(curriculum_text=curriculum_text)
    
    def create_messages_for_yandex(self, user_question: str) -> List[Dict]:
        """Создать сообщения для YandexGPT API"""
        system_prompt = self.get_system_prompt()
        
        messages = [
            {
                "role": "system",
                "text": system_prompt
            },
            {
                "role": "user", 
                "text": user_question
            }
        ]
        
        return messages
    
    async def get_yandex_response(self, user_question: str) -> str:
        """Получить ответ от YandexGPT"""
        try:
            messages = self.create_messages_for_yandex(user_question)
            
            logger.info(f"Sending request to YandexGPT for question: {user_question[:100]}...")
            
            # ОТЛАДОЧНЫЙ ВЫВОД: печатаем системный промпт
            system_message = messages[0] if messages and messages[0].get('role') == 'system' else None
            if system_message:
                print("\n" + "="*80)
                print("СИСТЕМНЫЙ ПРОМПТ, ОТПРАВЛЯЕМЫЙ В YANDEXGPT:")
                print("="*80)
                print(system_message['text'])
                print("="*80)
                print(f"Длина системного промпта: {len(system_message['text'])} символов")
                print("="*80 + "\n")
            
            # ОТЛАДОЧНЫЙ ВЫВОД: печатаем вопрос пользователя
            user_message = messages[1] if len(messages) > 1 and messages[1].get('role') == 'user' else None
            if user_message:
                print("ВОПРОС ПОЛЬЗОВАТЕЛЯ:")
                print("-" * 40)
                print(user_message['text'])
                print("-" * 40 + "\n")
            
            # Вызов YandexGPT
            result = (
                self.yandex_sdk.models.completions(YANDEX_CONFIG['model_name'])
                .configure(
                    temperature=YANDEX_CONFIG['temperature'],
                    max_tokens=YANDEX_CONFIG['max_tokens']
                )
                .run(messages)
            )
            
            if result and len(result) > 0:
                response_text = result[0].text if hasattr(result[0], 'text') else str(result[0])
                logger.info(f"Received response from YandexGPT: {response_text[:100]}...")
                # Исправляем форматирование для Telegram
                response_text = self.fix_telegram_formatting(response_text)
                return response_text
            else:
                logger.error("Empty response from YandexGPT")
                return SYSTEM_PROMPTS['no_response']
                
        except Exception as e:
            logger.error(f"Error calling YandexGPT: {e}")
            return SYSTEM_PROMPTS['error']
    
    def fix_telegram_formatting(self, text: str) -> str:
        """Исправить форматирование для Telegram"""
        import re
        
        # Заменяем markdown форматирование на HTML
        # **жирный** -> <b>жирный</b>
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        
        # *курсив* -> <i>курсив</i>
        text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<i>\1</i>', text)
        
        # ```код``` -> <code>код</code>
        text = re.sub(r'```(.*?)```', r'<code>\1</code>', text, flags=re.DOTALL)
        
        # `код` -> <code>код</code>
        text = re.sub(r'`([^`]+?)`', r'<code>\1</code>', text)
        
        return text
    
    def send_telegram_message(self, chat_id: int, text: str) -> bool:
        """Отправить сообщение в Telegram"""
        url = f'https://api.telegram.org/bot{self.telegram_token}/sendMessage'
        
        # Разбиваем длинные сообщения
        max_length = TELEGRAM_CONFIG['max_message_length']
        if len(text) > max_length:
            parts = [text[i:i+max_length] for i in range(0, len(text), max_length)]
            for i, part in enumerate(parts):
                if i > 0:
                    part = f"(продолжение {i+1}/{len(parts)})\n\n" + part
                payload = {
                    'chat_id': chat_id,
                    'text': part,
                    'parse_mode': 'HTML'
                }
                try:
                    response = requests.post(url, data=payload, timeout=10)
                    if not response.json().get('ok'):
                        logger.error(f"Failed to send message part {i+1}: {response.text}")
                        return False
                except Exception as e:
                    logger.error(f"Error sending message part {i+1}: {e}")
                    return False
            return True
        else:
            payload = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }
            try:
                response = requests.post(url, data=payload, timeout=10)
                result = response.json()
                if result.get('ok'):
                    return True
                else:
                    logger.error(f"Failed to send message: {result}")
                    return False
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                return False
    
    def get_telegram_updates(self) -> List[Dict]:
        """Получить обновления из Telegram"""
        url = f'https://api.telegram.org/bot{self.telegram_token}/getUpdates'
        params = {
            'offset': self.update_offset,
            'timeout': TELEGRAM_CONFIG['timeout'],
            'limit': 100
        }
        
        try:
            response = requests.get(url, params=params, timeout=TELEGRAM_CONFIG['timeout'] + 5)
            data = response.json()
            
            if data.get('ok') and data.get('result'):
                updates = data['result']
                if updates:
                    # Обновляем offset
                    self.update_offset = updates[-1]['update_id'] + 1
                return updates
            else:
                logger.error(f"Error getting updates: {data}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting Telegram updates: {e}")
            return []
    
    def process_message(self, message: Dict) -> Optional[str]:
        """Обработать входящее сообщение"""
        try:
            chat_id = message['chat']['id']
            user_id = message['from']['id']
            text = message.get('text', '').strip()
            
            if not text:
                return None
            
            logger.info(f"Processing message from user {user_id} in chat {chat_id}: {text}")
            
            # Команды бота
            if text.startswith('/start'):
                self.send_telegram_message(chat_id, SYSTEM_PROMPTS['welcome'])
                return "start_command_processed"
            
            elif text.startswith('/help'):
                self.send_telegram_message(chat_id, SYSTEM_PROMPTS['help'])
                return "help_command_processed"
            
            # Обычный вопрос - отправляем в YandexGPT
            return text
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return None
    
    async def show_thinking_animation(self, chat_id: int):
        """Показать анимацию обдумывания"""
        thinking_messages = [
            "🤔 Анализирую учебные планы...",
            "📚 Ищу информацию в базе данных...",
            "🔍 Проверяю детали программ...",
            "💭 Формулирую ответ..."
        ]
        
        message_id = None
        
        for i, msg in enumerate(thinking_messages):
            try:
                if message_id is None:
                    # Отправляем первое сообщение
                    url = f'https://api.telegram.org/bot{self.telegram_token}/sendMessage'
                    payload = {
                        'chat_id': chat_id,
                        'text': msg,
                        'parse_mode': 'HTML'
                    }
                    response = requests.post(url, data=payload, timeout=10)
                    result = response.json()
                    if result.get('ok'):
                        message_id = result['result']['message_id']
                else:
                    # Редактируем существующее сообщение
                    url = f'https://api.telegram.org/bot{self.telegram_token}/editMessageText'
                    payload = {
                        'chat_id': chat_id,
                        'message_id': message_id,
                        'text': msg,
                        'parse_mode': 'HTML'
                    }
                    requests.post(url, data=payload, timeout=10)
                
                # Пауза между сообщениями
                if i < len(thinking_messages) - 1:
                    await asyncio.sleep(1.5)
                    
            except Exception as e:
                logger.error(f"Error in thinking animation: {e}")
                break
        
        return message_id
    
    async def handle_question(self, chat_id: int, question: str):
        """Обработать вопрос пользователя"""
        thinking_message_id = None
        try:
            # Отправляем индикатор "печатает"
            typing_url = f'https://api.telegram.org/bot{self.telegram_token}/sendChatAction'
            requests.post(typing_url, data={'chat_id': chat_id, 'action': 'typing'})
            
            # Показываем анимацию обдумывания
            thinking_message_id = await self.show_thinking_animation(chat_id)
            
            # Получаем ответ от YandexGPT
            response = await self.get_yandex_response(question)
            
            # Удаляем сообщение с анимацией
            if thinking_message_id:
                try:
                    delete_url = f'https://api.telegram.org/bot{self.telegram_token}/deleteMessage'
                    requests.post(delete_url, data={
                        'chat_id': chat_id,
                        'message_id': thinking_message_id
                    }, timeout=5)
                except Exception as e:
                    logger.warning(f"Could not delete thinking message: {e}")
            
            # Отправляем ответ пользователю
            self.send_telegram_message(chat_id, response)
            
            logger.info(f"Successfully handled question for chat {chat_id}")
            
        except Exception as e:
            logger.error(f"Error handling question: {e}")
            
            # Удаляем сообщение с анимацией в случае ошибки
            if thinking_message_id:
                try:
                    delete_url = f'https://api.telegram.org/bot{self.telegram_token}/deleteMessage'
                    requests.post(delete_url, data={
                        'chat_id': chat_id,
                        'message_id': thinking_message_id
                    }, timeout=5)
                except:
                    pass
            
            error_message = "Извините, произошла ошибка при обработке вашего вопроса. Попробуйте позже."
            self.send_telegram_message(chat_id, error_message)
    
    async def run(self):
        """Запустить бота"""
        logger.info("Starting ITMO Curriculum Bot...")
        
        while True:
            try:
                # Получаем обновления
                updates = self.get_telegram_updates()
                
                for update in updates:
                    if 'message' in update:
                        message = update['message']
                        chat_id = message['chat']['id']
                        
                        # Обрабатываем сообщение
                        question = self.process_message(message)
                        
                        if question and question not in ['start_command_processed', 'help_command_processed']:
                            # Обрабатываем вопрос асинхронно
                            await self.handle_question(chat_id, question)
                
                # Небольшая пауза между запросами
                await asyncio.sleep(1)
                
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(5)  # Пауза при ошибке

def main():
    """Главная функция"""
    try:
        # Создаем и запускаем бота
        bot = ITMOCurriculumBot()
        
        # Запускаем бота
        asyncio.run(bot.run())
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    main()