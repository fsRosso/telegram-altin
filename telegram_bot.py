import logging
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from price_fetcher_fast import FastPriceFetcher
from tradingview_chart_fetcher import TradingViewChartFetcher
import asyncio

# Logging ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Railway healthcheck için minimal HTTP handler"""
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.price_fetcher = FastPriceFetcher()
        self.xauusd_fetcher = TradingViewChartFetcher()
        self.application = Application.builder().token(token).build()
        self.last_xaurub_price = None  # Son XAURUB fiyatı
        self.last_xauusd_price = None  # Son XAUUSD fiyatı (hafızada)
        self.healthcheck_server = None
        self.setup_handlers()
        self.start_healthcheck()
    
    def start_healthcheck(self):
        """Minimal healthcheck server'ı başlatır"""
        try:
            import os
            port = int(os.environ.get('PORT', 8000))
            self.healthcheck_server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
            print(f"🌐 Healthcheck server başlatıldı: port {port}")
            
            # Ayrı thread'de çalıştır
            thread = threading.Thread(target=self.healthcheck_server.serve_forever, daemon=True)
            thread.start()
            print("✅ Healthcheck server hazır!")
        except Exception as e:
            print(f"❌ Healthcheck server hatası: {e}")
    
    def setup_handlers(self):
        """Bot komutlarını ve mesaj işleyicilerini ayarlar"""
        # Komut işleyicileri
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Mesaj işleyicileri
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start komutu işleyicisi"""
        welcome_message = """
🤖 Gelişmiş Altın Fiyat Botuna Hoşgeldiniz!

Bu bot hem ProFinance.ru'dan XAURUB hem de TradingView'den XAUUSD fiyat verilerini çeker.

📈 Kullanım:
• "+0,01" yazarak GÜNCEL XAURUB fiyatı + %0.01 ve GÜNCEL XAUUSD fiyatı (gram başına RUB)
• "-0,05" yazarak GÜNCEL XAURUB fiyatı - %0.05 ve GÜNCEL XAUUSD fiyatı (gram başına RUB)
• "25" yazarak XAURUB ÷ 25 sonucu XAUUSD gram başına ile karşılaştırılır

🔄 Her + veya - işlemde yeni fiyatlar çekilir!
📏 XAUUSD fiyatı 31.1035'e bölünerek gram başına RUB değeri hesaplanır
⚠️ %0.5'ten fazla fiyat değişimlerinde uyarı verilir

❓ Yardım için /help yazın
        """
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help komutu işleyicisi"""
        help_message = """
🆘 Yardım

📝 Komutlar:
• /start - Botu başlat
• /help - Bu yardım mesajını göster

💰 Fiyat Sorgulama (Yüzde Artış/Azalış):
• "+0,01" - GÜNCEL XAURUB fiyatı + %0.01 + GÜNCEL XAUUSD fiyatı
• "+0,05" - GÜNCEL XAURUB fiyatı + %0.05 + GÜNCEL XAUUSD fiyatı
• "+1" - GÜNCEL XAURUB fiyatı + %1.00 + GÜNCEL XAUUSD fiyatı
• "-0,05" - GÜNCEL XAURUB fiyatı - %0.05 + GÜNCEL XAUUSD fiyatı
• "-1" - GÜNCEL XAURUB fiyatı - %1.00 + GÜNCEL XAUUSD fiyatı

🔄 Her + veya - işlemde yeni fiyatlar çekilir!

🔢 Bölme ve Karşılaştırma:
• "25" - Son XAURUB fiyatı 25'e bölünür ve XAUUSD ile karşılaştırılır
• "50" - Son XAURUB fiyatı 50'ye bölünür ve XAUUSD ile karşılaştırılır
• "2.5" - Son XAURUB fiyatı 2.5'e bölünür ve XAUUSD ile karşılaştırılır

⚡ Örnek kullanım:
Siz: +0,01
Bot: GÜNCEL XAURUB: 119.00 RUB → 119.0119 RUB (+%0.01)
      GÜNCEL XAUUSD: $3,348.45 → 107.65 RUB/gram (÷31.1035)

Siz: -0,05
Bot: GÜNCEL XAURUB: 119.50 RUB → 118.9403 RUB (-%0.05)
      GÜNCEL XAUUSD: $3,349.20 → 107.68 RUB/gram (÷31.1035)

Siz: 25
Bot: XAURUB ÷ 25 = 4.7605 RUB
      XAUUSD gram başına: 107.68 RUB
      Fark: 107.68 - 4.7605 = 102.92 RUB
        """
        await update.message.reply_text(help_message)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gelen mesajları işler"""
        message_text = update.message.text.strip()
        
        # "+0,01" veya "-0,05" formatındaki mesajları kontrol et (YÜZDE HESABI)
        if message_text.startswith('+') or message_text.startswith('-'):
            await self.handle_price_request(update, message_text)
        # Sadece sayı gönderildiyse son fiyatı böl (BÖLME İŞLEMİ)
        elif self.is_number(message_text):
            await self.handle_division_request(update, message_text)
        else:
            # Bilinmeyen mesaj
            await update.message.reply_text(
                "❓ Anlamadım!\n\n"
                "📈 Fiyat sorgulamak için: '+0,01' veya '-0,05'\n"
                "🔢 XAURUB ÷ sayı vs XAUUSD gram başına karşılaştırması için: '25'\n"
                "❓ Yardım için: /help"
            )
    
    async def handle_price_request(self, update: Update, increment_text: str):
        """Fiyat artırma/azaltma isteğini işler"""
        try:
            start_ts = time.perf_counter()
            # Bekleme mesajı gönder
            waiting_message = await update.message.reply_text("📊 Fiyat verileri çekiliyor...\n🔍 XAURUB ve XAUUSD fiyatları alınıyor...")
            
            # İşareti ve değeri ayır
            sign = increment_text[0]  # + veya -
            value_str = increment_text[1:]  # İşareti çıkar
            value_str = value_str.replace(',', '.')  # Virgülü noktaya çevir
            increment = float(value_str)
            
            # Eğer - işareti varsa, değeri negatif yap
            if sign == '-':
                increment = -increment
            
            # ✅ HER İŞLEMDE YENİ FİYATLAR ÇEK!
            # XAURUB ve XAUUSD fiyat verilerini paralel olarak çek (ASYNC)
            xaurub_task = self.price_fetcher.get_price_plus_increment_async(increment)
            
            # XAUUSD için browser başlatma ve fiyat çekme task'ı
            async def get_xauusd_price():
                try:
                    if await self.xauusd_fetcher.start_browser():
                        # Sadece JavaScript-only yöntemi kullan (çok hızlı!)
                        price = await self.xauusd_fetcher.get_price_javascript_only()
                        
                        if price:
                            await self.xauusd_fetcher.update_price(price)
                            # ✅ XAUUSD fiyatını hafızaya al
                            self.last_xauusd_price = price
                        await self.xauusd_fetcher.close_browser()
                        return price
                except Exception as e:
                    logger.error(f"XAUUSD fiyat çekme hatası: {e}")
                    return None
                return None
            
            xauusd_task = get_xauusd_price()
            
            # Paralel olarak çalıştır
            xaurub_result, xauusd_price = await asyncio.gather(xaurub_task, xauusd_task)
            
            # ✅ HER İŞLEMDE YENİ FİYATLAR GÜNCELLENİYOR!
            # XAUUSD fiyatını hafızaya al
            if xauusd_price:
                self.last_xauusd_price = xauusd_price
            
            # Son XAURUB fiyatını kaydet
            self.last_xaurub_price = xaurub_result['new_price']
            
            # Fiyat değişim analizi yap
            current_price = xaurub_result['current_price']
            change_analysis = self.price_fetcher.analyze_price_change(current_price)
            
            # Uyarı mesajı hazırla
            warning_message = ""
            if change_analysis['is_warning']:
                warning_message = f"\n⚠️ UYARI: XAURUB fiyatı %{abs(change_analysis['change_percent']):.2f} değişti!\n"
            if change_analysis['is_abnormal']:
                warning_message = f"\n🚨 KRİTİK: Anormal XAURUB fiyat değişimi %{abs(change_analysis['change_percent']):.2f}!\n"
            
            # XAUUSD durumu mesajı
            xauusd_status = ""
            if xauusd_price:
                # XAUUSD fiyatını 31.1035'e böl (1 troy ounce = 31.1035 gram)
                xauusd_rub_per_gram = xauusd_price / 31.1035
                
                # XAUUSD fiyat değişim analizi
                xauusd_analysis = self.xauusd_fetcher.analyze_xauusd_price_change(xauusd_price)
                xauusd_status = f"""
💎 XAUUSD: ${xauusd_price:.2f}
📏 Gram başına: {xauusd_rub_per_gram:.4f} RUB (÷31.1035)"""
                
                # XAUUSD uyarı mesajı
                if xauusd_analysis["is_warning"]:
                    xauusd_status += f"\n⚠️ {xauusd_analysis['message']}"
            else:
                xauusd_status = f"\n❌ XAUUSD fiyatı alınamadı"
            
            # Sonuç mesajını hazırla
            elapsed = time.perf_counter() - start_ts
            
            # İşaret ve değişim mesajını hazırla
            if increment >= 0:
                change_text = f"+%{increment}"
                change_desc = "Artış"
            else:
                change_text = f"%{increment}"
                change_desc = "Azalış"
            
            response_message = f"""
💰 Fiyat Bilgisi (GÜNCEL)

🇷🇺 XAURUB (Ruble):
📈 Mevcut fiyat: {xaurub_result['current_price']:.2f} RUB
📊 Yeni fiyat: {xaurub_result['new_price']:.4f} RUB ({change_text})
📈 {change_desc} miktarı: {xaurub_result['percentage_increase']:.4f} RUB{warning_message}

🇺🇸 XAUUSD (Dolar):{xauusd_status}

🕐 Güncelleme zamanı: {self.get_current_time()}
⏱️ İşlem süresi: {elapsed:.2f} sn
🔄 Her işlemde güncel fiyatlar çekiliyor!

💡 İpucu: Bir sayı göndererek XAURUB fiyatını o sayıya bölebilir ve XAUUSD ile karşılaştırabilirsiniz

⚠️ Not: %0.5'ten fazla fiyat değişimlerinde uyarı verilir
            """.strip()
            
            # Bekleme mesajını güncelle
            await waiting_message.edit_text(response_message)
            
        except ValueError:
            await update.message.reply_text(
                "❌ Geçersiz format!\n"
                "Örnek: +0,01 (yüzde 0.01 artış) veya -0,05 (yüzde 0.05 azalış)"
            )
        except Exception as e:
            error_message = f"❌ Hata oluştu: {str(e)}\n\n🔄 Lütfen tekrar deneyin."
            try:
                await waiting_message.edit_text(error_message)
            except:
                await update.message.reply_text(error_message)
            
            logger.error(f"Fiyat çekme hatası: {e}")
    
    async def handle_division_request(self, update: Update, number_text: str):
        """Sayı gönderildiğinde son XAURUB fiyatını böler ve XAUUSD ile karşılaştırır"""
        try:
            # Son XAURUB fiyatı var mı kontrol et
            if self.last_xaurub_price is None:
                await update.message.reply_text(
                    "❌ Henüz XAURUB fiyat sorgulaması yapmadınız!\n"
                    "Önce '+0,01' yazarak fiyat sorgulayın."
                )
                return
            
            # XAUUSD fiyatı hafızada var mı kontrol et
            if self.last_xauusd_price is None:
                await update.message.reply_text(
                    "❌ XAUUSD fiyatı hafızada yok!\n"
                    "Önce '+0,01' yazarak hem XAURUB hem XAUUSD fiyatlarını alın."
                )
                return
            
            # Sayıyı parse et
            divisor = float(number_text.replace(',', '.'))
            
            if divisor == 0:
                await update.message.reply_text("❌ Sıfıra bölme yapılamaz!")
                return
            
            # Bölme işlemi
            divided_xaurub = self.last_xaurub_price / divisor
            
            # XAUUSD ile karşılaştırma
            # XAUUSD fiyatını 31.1035'e böl (1 troy ounce = 31.1035 gram)
            xauusd_rub_per_gram = self.last_xauusd_price / 31.1035
            
            # Fark hesaplama (XAUUSD gram başına - XAURUB bölünmüş)
            difference = xauusd_rub_per_gram - divided_xaurub
            difference_percent = (difference / xauusd_rub_per_gram) * 100
            
            # Karşılaştırma sonucu
            comparison_result = ""
            if divided_xaurub > xauusd_rub_per_gram:
                comparison_result = f"📈 XAURUB ÷ {divisor} > XAUUSD gram başına"
            elif divided_xaurub < xauusd_rub_per_gram:
                comparison_result = f"📉 XAURUB ÷ {divisor} < XAUUSD gram başına"
            else:
                comparison_result = f"⚖️ XAURUB ÷ {divisor} = XAUUSD gram başına"
            
            # Sonuç mesajını hazırla
            response_message = f"""
🔢 Bölme ve Karşılaştırma İşlemi

🇷🇺 XAURUB (Ruble):
📊 Son fiyat: {self.last_xaurub_price:.4f} RUB
➗ Bölen: {divisor}
📉 Sonuç: {divided_xaurub:.4f} RUB

🇺🇸 XAUUSD (Dolar):
💎 Fiyat: ${self.last_xauusd_price:.2f}
📏 Gram başına: {xauusd_rub_per_gram:.4f} RUB (÷31.1035)

📊 Karşılaştırma:
{comparison_result}
📈 Fark: {difference:.4f} RUB
📊 Fark yüzdesi: %{difference_percent:.2f}

💡 Not: XAUUSD fiyatı 31.1035'e bölünerek gram başına RUB değeri hesaplanır
            """.strip()
            
            await update.message.reply_text(response_message)
            
        except ValueError:
            await update.message.reply_text(
                "❌ Geçersiz sayı formatı!\n"
                "Örnek: 25 veya 25.5"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Bölme işlemi hatası: {str(e)}")
    
    def is_number(self, text: str) -> bool:
        """Metnin sayı olup olmadığını kontrol eder (bölme işlemi için)"""
        try:
            float(text.replace(',', '.'))
            return True
        except ValueError:
            return False
    
    def get_current_time(self):
        """Mevcut zamanı formatlar"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Hata işleyicisi"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.message:
            await update.message.reply_text(
                "❌ Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin."
            )
    
    def run(self):
        """Botu çalıştırır"""
        print("🤖 Telegram botu başlatılıyor...")
        print("📱 Bot hazır! Telegram'da mesaj gönderebilirsiniz.")
        print("🛑 Durdurmak için Ctrl+C tuşlarına basın.\n")
        
        # Hata işleyicisini ekle
        self.application.add_error_handler(self.error_handler)
        
        # Botu çalıştır
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

# Test fonksiyonu
if __name__ == "__main__":
    # Test için token gerekli
    print("⚠️  Bu dosya doğrudan çalıştırılamaz.")
    print("🚀 main.py dosyasını kullanın.")
