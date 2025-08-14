import logging
import time
import os
import signal
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from price_fetcher_fast import FastPriceFetcher
from tradingview_chart_fetcher import TradingViewChartFetcher
from yfinance_fetcher import YFinanceFetcher
from config import ENABLE_INSTANCE_CONTROL, INSTANCE_CHECK_INTERVAL, PRICE_VALIDATION_TOLERANCE
import asyncio

# Logging ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.price_fetcher = FastPriceFetcher()
        self.xauusd_fetcher = TradingViewChartFetcher()
        self.yfinance_fetcher = YFinanceFetcher()  # Fiyat doğrulama için
        self.application = Application.builder().token(token).build()
        self.last_xaurub_price = None  # Son XAURUB fiyatı
        self.last_xauusd_price = None  # Son XAUUSD fiyatı (hafızada)
        self.setup_handlers()
        
        # Instance kontrolü için PID dosyası
        self.pid_file = f"bot_{token[:10]}.pid"
        if ENABLE_INSTANCE_CONTROL:
            self.check_instance()
        else:
            logger.info("Instance kontrolü devre dışı")
    
    def check_instance(self):
        """Aynı anda sadece bir bot instance'ının çalışmasını sağlar"""
        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, 'r') as f:
                    old_pid = int(f.read().strip())
                
                # PID'nin hala çalışıp çalışmadığını kontrol et
                try:
                    os.kill(old_pid, 0)  # Signal 0 ile process kontrolü
                    logger.warning(f"Bot zaten çalışıyor (PID: {old_pid})")
                    raise RuntimeError(f"Bot zaten çalışıyor (PID: {old_pid})")
                except OSError:
                    # Process ölmüş, PID dosyasını sil
                    logger.info(f"Eski PID dosyası temizlendi (PID: {old_pid})")
                    os.remove(self.pid_file)
            except (ValueError, IOError):
                # Geçersiz PID dosyası, sil
                os.remove(self.pid_file)
        
        # Yeni PID dosyası oluştur
        with open(self.pid_file, 'w') as f:
            f.write(str(os.getpid()))
        
        logger.info(f"Bot instance başlatıldı (PID: {os.getpid()})")
    
    def cleanup(self):
        """Temizlik işlemleri"""
        if os.path.exists(self.pid_file):
            os.remove(self.pid_file)
            logger.info("PID dosyası temizlendi")
    
    def __del__(self):
        """Destructor - PID dosyasını temizle"""
        self.cleanup()
    
    def setup_handlers(self):
        """Bot komutlarını ve mesaj işleyicilerini ayarlar"""
        # Komut işleyicileri
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("validate", self.validate_command))
        
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
• /validate - Fiyat doğrulama raporu

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
    
    async def validate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Validate komutu - fiyat doğrulama yapar"""
        try:
            await update.message.reply_text("🔍 Fiyat doğrulama başlatılıyor...")
            
            # Mevcut fiyatları al
            if not self.last_xaurub_price or not self.last_xauusd_price:
                await update.message.reply_text(
                    "❌ Henüz fiyat verisi yok!\n"
                    "Önce bir fiyat sorgusu yapın (örn: +0.01)"
                )
                return
            
            # Fiyat doğrulama yap
            validation_result = self.validate_prices(
                self.last_xaurub_price, 
                self.last_xauusd_price
            )
            
            if "error" in validation_result:
                await update.message.reply_text(f"❌ Doğrulama hatası: {validation_result['error']}")
                return
            
            # Sonuç mesajını hazırla
            xaurub_info = validation_result["xaurub"]
            xauusd_info = validation_result["xauusd"]
            
            validation_message = f"""
🔍 **Fiyat Doğrulama Raporu**

🇷🇺 **XAURUB Doğrulama:**
📊 Direkt Fiyat: {xaurub_info['direct_price']:.2f} RUB
🧮 Hesaplanan: {xaurub_info.get('calculated_price', 'N/A')} RUB
📈 Fark: %{xaurub_info.get('difference_percent', 'N/A'):.2f}
✅ Durum: {xaurub_info['status']}

🇺🇸 **XAUUSD Doğrulama:**
📊 TradingView: ${xauusd_info['tradingview_price']:.2f}
🧮 yfinance: ${xauusd_info['yfinance_price']:.2f}
📈 Fark: %{xauusd_info.get('difference_percent', 'N/A'):.2f}
✅ Durum: {xauusd_info['status']}

🎯 **Genel Durum:**
{validation_result['overall_status']}

💡 **Not:** %{PRICE_VALIDATION_TOLERANCE} tolerans ile kontrol edildi
            """.strip()
            
            await update.message.reply_text(validation_message)
            
        except Exception as e:
            logger.error(f"Validate komut hatası: {e}")
            await update.message.reply_text(f"❌ Doğrulama hatası: {str(e)}")
    
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
    
    def validate_prices(self, xaurub_price: float, xauusd_price: float) -> dict:
        """Fiyatları yfinance ile doğrular"""
        try:
            # XAURUB doğrulama
            xaurub_validation = self.yfinance_fetcher.validate_xaurub_price(
                xaurub_price, 
                PRICE_VALIDATION_TOLERANCE
            )
            
            # XAUUSD doğrulama (yfinance vs TradingView)
            yf_xauusd = self.yfinance_fetcher.get_xauusd_price()
            if yf_xauusd:
                xauusd_difference = abs(xauusd_price - yf_xauusd)
                xauusd_difference_percent = (xauusd_difference / yf_xauusd) * 100
                xauusd_valid = xauusd_difference_percent <= PRICE_VALIDATION_TOLERANCE
            else:
                xauusd_difference_percent = None
                xauusd_valid = None
            
            validation_result = {
                "xaurub": xaurub_validation,
                "xauusd": {
                    "valid": xauusd_valid,
                    "tradingview_price": xauusd_price,
                    "yfinance_price": yf_xauusd,
                    "difference_percent": xauusd_difference_percent,
                    "status": "✅ Normal" if xauusd_valid else "⚠️ Anormal" if xauusd_valid is False else "❓ Kontrol edilemedi"
                },
                "overall_status": "✅ Tüm fiyatlar normal" if (
                    xaurub_validation.get("valid", False) and 
                    (xauusd_valid is None or xauusd_valid)
                ) else "⚠️ Bazı fiyatlarda anormallik tespit edildi"
            }
            
            return validation_result
            
        except Exception as e:
            logger.error(f"❌ Fiyat doğrulama hatası: {e}")
            return {"error": str(e)}
    
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
        
        # Signal handler ekle (graceful shutdown için)
        def signal_handler(signum, frame):
            print(f"\n🛑 Signal {signum} alındı, bot kapatılıyor...")
            self.cleanup()
            exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Botu çalıştır
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,  # Eski mesajları yoksay
                close_loop=False
            )
        except Exception as e:
            logger.error(f"Bot çalışma hatası: {e}")
            self.cleanup()
            raise
        finally:
            self.cleanup()

# Test fonksiyonu
if __name__ == "__main__":
    # Test için token gerekli
    print("⚠️  Bu dosya doğrudan çalıştırılamaz.")
    print("🚀 main.py dosyasını kullanın.")
