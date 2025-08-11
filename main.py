#!/usr/bin/env python3
"""
🚀 Telegram Altın Fiyat Botu - Ana Çalıştırma Dosyası
"""

import logging
import asyncio
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram_bot import TelegramBot
from config import BOT_TOKEN
import os

# Logging ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Railway healthcheck için basit HTTP handler"""
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            response = """
            <html>
            <head><title>Telegram Altın Fiyat Botu</title></head>
            <body>
                <h1>🤖 Telegram Altın Fiyat Botu</h1>
                <p>✅ Bot çalışıyor ve sağlıklı!</p>
                <p>🚀 Railway deployment başarılı</p>
            </body>
            </html>
            """
            self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # HTTP log'larını sustur
        pass

def run_healthcheck_server():
    """Healthcheck HTTP server'ı çalıştırır"""
    try:
        port = int(os.environ.get('PORT', 8000))
        server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        print(f"🌐 Healthcheck server başlatıldı: http://0.0.0.0:{port}")
        print("✅ Railway healthcheck için hazır!")
        server.serve_forever()
    except Exception as e:
        print(f"❌ Healthcheck server hatası: {e}")

def main():
    """Ana fonksiyon"""
    try:
        print("🚀 Telegram Altın Fiyat Botu başlatılıyor...")
        print(f"🔑 Bot Token: {BOT_TOKEN[:10]}...")
        
        # Healthcheck server'ı ÖNCE başlat
        print("🌐 Healthcheck server başlatılıyor...")
        healthcheck_thread = threading.Thread(target=run_healthcheck_server, daemon=True)
        healthcheck_thread.start()
        
        # Server'ın başlaması için kısa bir bekleme
        time.sleep(2)
        print("✅ Healthcheck server hazır!")
        
        # Bot instance'ını oluştur
        print("🤖 Bot instance oluşturuluyor...")
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
