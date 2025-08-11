#!/usr/bin/env python3
"""
🚀 Telegram Altın Fiyat Botu - Ana Çalıştırma Dosyası
"""

import logging
from telegram_bot import TelegramBot
from config import BOT_TOKEN

# Logging ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Ana fonksiyon"""
    try:
        print("🚀 Telegram Altın Fiyat Botu başlatılıyor...")
        print(f"🔑 Bot Token: {BOT_TOKEN[:10]}...")
        
        # Bot instance'ını oluştur
        bot = TelegramBot(BOT_TOKEN)
        
        print("✅ Bot başarıyla oluşturuldu!")
        print("📱 Telegram'da botu bulabilirsiniz")
        print("🔄 Bot çalışıyor... Durdurmak için Ctrl+C\n")
        
        # Botu çalıştır (run() metodu async değil)
        bot.run()
        
    except Exception as e:
        logger.error(f"Bot başlatma hatası: {e}")
        print(f"❌ Bot başlatılamadı: {e}")
        return False
    
    return True

if __name__ == "__main__":
    try:
        # Ana fonksiyonu çalıştır
        main()
    except KeyboardInterrupt:
        print("\n🛑 Bot kullanıcı tarafından durduruldu.")
    except Exception as e:
        print(f"❌ Beklenmeyen hata: {e}")
        logger.error(f"Beklenmeyen hata: {e}")
