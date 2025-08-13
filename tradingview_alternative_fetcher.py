import asyncio
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
import logging
from playwright.async_api import async_playwright
import re

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingViewAlternativeFetcher:
    """
    TradingView'dan XAUUSD OANDA fiyatını alternatif yöntemlerle çeken sınıf
    """
    
    def __init__(self):
        # TradingView URL'leri
        self.chart_url = "https://www.tradingview.com/chart/?symbol=OANDA%3AXAUUSD"
        self.symbol_url = "https://www.tradingview.com/symbols/OANDA-XAUUSD/"
        
        # Fiyat verileri
        self.current_price: Optional[float] = None
        self.last_update: Optional[datetime] = None
        self.price_history: list[Dict[str, Any]] = []
        self.max_history_size = 100
        
        # Browser ayarları
        self.browser = None
        self.page = None
        
    async def start_browser(self):
        """
        Browser'ı başlat
        """
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--no-first-run",
                    "--no-zygote",
                    "--disable-gpu"
                ]
            )
            
            self.page = await self.browser.new_page()
            
            # User agent ayarla
            await self.page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            
            logger.info("🌐 Browser başlatıldı")
            return True
            
        except Exception as e:
            logger.error(f"❌ Browser başlatma hatası: {e}")
            return False
    
    async def get_price_from_chart(self) -> Optional[float]:
        """
        TradingView chart sayfasından fiyat çek
        """
        try:
            if not self.page:
                logger.error("❌ Browser sayfası hazır değil")
                return None
            
            logger.info("📊 TradingView chart sayfasından fiyat çekiliyor...")
            
            # Chart sayfasına git
            await self.page.goto(self.chart_url, wait_until="networkidle")
            await asyncio.sleep(3)  # Sayfa yüklenmesi için bekle
            
            # Fiyat elementini bul (birkaç farklı selector dene)
            price_selectors = [
                '[data-role="price"]',
                '.chart-markup-table__price',
                '.tv-symbol-price-quote__value',
                '.tv-symbol-price-quote__price',
                '[class*="price"]',
                '[class*="Price"]'
            ]
            
            price = None
            for selector in price_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        price_text = await element.text_content()
                        if price_text:
                            # Fiyat metnini temizle
                            price = self._extract_price_from_text(price_text)
                            if price:
                                logger.info(f"✅ Fiyat bulundu: ${price:.2f}")
                                break
                except Exception as e:
                    continue
            
            if not price:
                # Alternatif yöntem: JavaScript ile fiyat çek
                price = await self._get_price_via_javascript()
            
            return price
            
        except Exception as e:
            logger.error(f"❌ Chart'tan fiyat çekme hatası: {e}")
            return None
    
    async def _get_price_via_javascript(self) -> Optional[float]:
        """
        JavaScript ile fiyat çek
        """
        try:
            # Sayfadaki tüm metinleri tara
            page_text = await self.page.evaluate("() => document.body.innerText")
            
            # Fiyat pattern'lerini ara
            price_patterns = [
                r'\$(\d+\.\d+)',  # $1234.56
                r'(\d+\.\d+)',    # 1234.56
                r'(\d+,\d+\.\d+)' # 1,234.56
            ]
            
            for pattern in price_patterns:
                matches = re.findall(pattern, page_text)
                for match in matches:
                    try:
                        # Virgülü kaldır ve float'a çevir
                        price_str = match.replace(',', '')
                        price = float(price_str)
                        
                        # Mantıklı fiyat aralığı kontrolü (altın için 1000-3000 arası)
                        if 1000 <= price <= 3000:
                            logger.info(f"✅ JavaScript ile fiyat bulundu: ${price:.2f}")
                            return price
                    except ValueError:
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"❌ JavaScript fiyat çekme hatası: {e}")
            return None
    
    def _extract_price_from_text(self, text: str) -> Optional[float]:
        """
        Metin içinden fiyat çıkar
        """
        try:
            # Metni temizle
            text = text.strip()
            
            # Fiyat pattern'lerini ara
            price_patterns = [
                r'\$(\d+\.\d+)',  # $1234.56
                r'(\d+\.\d+)',    # 1234.56
                r'(\d+,\d+\.\d+)' # 1,234.56
            ]
            
            for pattern in price_patterns:
                match = re.search(pattern, text)
                if match:
                    price_str = match.group(1) if match.groups() else match.group(0)
                    # Virgülü kaldır
                    price_str = price_str.replace(',', '')
                    price = float(price_str)
                    
                    # Mantıklı fiyat aralığı kontrolü
                    if 1000 <= price <= 3000:
                        return price
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Metin fiyat çıkarma hatası: {e}")
            return None
    
    async def get_price_from_symbol_page(self) -> Optional[float]:
        """
        Symbol sayfasından fiyat çek
        """
        try:
            if not self.page:
                logger.error("❌ Browser sayfası hazır değil")
                return None
            
            logger.info("📊 TradingView symbol sayfasından fiyat çekiliyor...")
            
            # Symbol sayfasına git
            await self.page.goto(self.symbol_url, wait_until="networkidle")
            await asyncio.sleep(3)
            
            # Fiyat elementini bul
            price_selectors = [
                '.tv-symbol-price-quote__value',
                '.tv-symbol-price-quote__price',
                '[data-role="price"]',
                '.chart-markup-table__price'
            ]
            
            for selector in price_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        price_text = await element.text_content()
                        if price_text:
                            price = self._extract_price_from_text(price_text)
                            if price:
                                logger.info(f"✅ Symbol sayfasından fiyat bulundu: ${price:.2f}")
                                return price
                except Exception as e:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Symbol sayfasından fiyat çekme hatası: {e}")
            return None
    
    async def update_price(self, price: float):
        """
        Yeni fiyatı güncelle
        """
        try:
            old_price = self.current_price
            self.current_price = price
            self.last_update = datetime.now()
            
            # Fiyat geçmişine ekle
            price_data = {
                "price": price,
                "timestamp": self.last_update,
                "change": old_price - price if old_price else 0,
                "source": "TradingView Alternative"
            }
            
            self.price_history.append(price_data)
            if len(self.price_history) > self.max_history_size:
                self.price_history.pop(0)
            
            logger.info(f"💰 XAUUSD OANDA: ${price:.2f} (Güncelleme: {self.last_update.strftime('%H:%M:%S')})")
            
        except Exception as e:
            logger.error(f"❌ Fiyat güncelleme hatası: {e}")
    
    async def continuous_price_monitoring(self, interval: int = 30):
        """
        Sürekli fiyat izleme
        """
        try:
            logger.info(f"🔄 Sürekli fiyat izleme başlatıldı (her {interval} saniyede)")
            
            while True:
                # Chart'tan fiyat çek
                price = await self.get_price_from_chart()
                
                if price:
                    await self.update_price(price)
                else:
                    # Chart'tan bulamazsa symbol sayfasından dene
                    price = await self.get_price_from_symbol_page()
                    if price:
                        await self.update_price(price)
                    else:
                        logger.warning("⚠️ Fiyat bulunamadı")
                
                # Belirtilen süre kadar bekle
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Fiyat izleme durduruldu")
        except Exception as e:
            logger.error(f"❌ Sürekli izleme hatası: {e}")
    
    def get_current_price(self) -> Optional[float]:
        """
        Mevcut fiyatı döndür
        """
        return self.current_price
    
    def get_price_info(self) -> Dict[str, Any]:
        """
        Detaylı fiyat bilgisi döndür
        """
        return {
            "current_price": self.current_price,
            "last_update": self.last_update,
            "price_history_count": len(self.price_history),
            "symbol": "OANDA:XAUUSD",
            "method": "Alternative Fetcher"
        }
    
    async def close_browser(self):
        """
        Browser'ı kapat
        """
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            
            logger.info("🌐 Browser kapatıldı")
            
        except Exception as e:
            logger.error(f"❌ Browser kapatma hatası: {e}")

# Test fonksiyonu
async def test_alternative_fetcher():
    """
    Alternative fetcher'ı test et
    """
    fetcher = TradingViewAlternativeFetcher()
    
    try:
        logger.info("🧪 TradingView Alternative Fetcher test ediliyor...")
        
        # Browser'ı başlat
        if await fetcher.start_browser():
            # Tek seferlik fiyat çek
            price = await fetcher.get_price_from_chart()
            if price:
                await fetcher.update_price(price)
                logger.info(f"✅ Test başarılı! Fiyat: ${price:.2f}")
            else:
                logger.warning("⚠️ Chart'tan fiyat bulunamadı, symbol sayfası deneniyor...")
                price = await fetcher.get_price_from_symbol_page()
                if price:
                    await fetcher.update_price(price)
                    logger.info(f"✅ Test başarılı! Fiyat: ${price:.2f}")
                else:
                    logger.error("❌ Hiçbir yöntemle fiyat bulunamadı")
            
            # 10 saniye boyunca sürekli izleme
            logger.info("🔄 10 saniye boyunca sürekli izleme...")
            await asyncio.wait_for(
                fetcher.continuous_price_monitoring(interval=2),
                timeout=10.0
            )
            
    except asyncio.TimeoutError:
        logger.info("⏰ Test süresi doldu")
    except Exception as e:
        logger.error(f"❌ Test hatası: {e}")
    finally:
        await fetcher.close_browser()

if __name__ == "__main__":
    # Test çalıştır
    asyncio.run(test_alternative_fetcher())

