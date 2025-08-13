#!/usr/bin/env python3
"""
🚀 PythonAnywhere WSGI Dosyası
Telegram Bot Webhook için
"""

import os
import sys
import logging
from telegram_bot import TelegramBot
from config import BOT_TOKEN

# Logging ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot instance'ını oluştur
bot = TelegramBot(BOT_TOKEN)

# Webhook URL'ini ayarla (PythonAnywhere'de otomatik)
webhook_url = f"https://{os.environ.get('USERNAME', 'yourusername')}.pythonanywhere.com/webhook"

# Webhook'u ayarla
bot.setup_webhook(webhook_url)

# WSGI uygulaması
application = bot.application

if __name__ == "__main__":
    print("🚀 PythonAnywhere Bot başlatıldı!")
    print(f"🔗 Webhook URL: {webhook_url}")
