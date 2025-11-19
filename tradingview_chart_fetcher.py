import asyncio
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
import logging
from playwright.async_api import async_playwright
import re
from config import BROWSER_TYPE
from playwright_stealth import Stealth

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingViewChartFetcher:
    """
    TradingView XAUUSD sayfasından fiyat çeken optimize edilmiş sınıf
    """
    
    def __init__(self):
        # TradingView XAUUSD sayfası
        self.xauusd_url = "https://www.tradingview.com/symbols/XAUUSD/"
        
        # Fiyat verileri
        self.current_price: Optional[float] = None
        self.last_update: Optional[datetime] = None
        self.price_history: list[Dict[str, Any]] = []
        self.max_history_size = 100
        
        # Akıllı fiyat değişim kontrolü için
        self.last_known_price: Optional[float] = None
        self.price_change_threshold = 0.5  # %0.5 eşik
        
        # Browser ayarları
        self.browser = None
        self.page = None
        self.playwright = None
        self.playwright_manager = None
        self.stealth = Stealth()
        
    async def start_browser(self):
        """
        Browser'ı başlat (optimize edilmiş)
        """
        try:
            self.playwright_manager = self.stealth.use_async(async_playwright())
            self.playwright = await self.playwright_manager.__aenter__()
            
            # Browser type'ı config'den al
            if BROWSER_TYPE == "webkit":
                self.browser = await self.playwright.webkit.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                        "--disable-extensions",
                        "--disable-plugins",
                        "--disable-images",
                        "--disable-javascript-harmony-shipping",
                        "--disable-background-timer-throttling",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-renderer-backgrounding",
                        "--disable-features=TranslateUI",
                        "--disable-ipc-flooding-protection",
                        "--no-default-browser-check",
                        "--disable-default-apps",
                        "--disable-sync",
                        "--metrics-recording-only",
                        "--disable-background-networking",
                        "--disable-component-extensions-with-background-pages",
                        "--disable-background-mode",
                        "--disable-client-side-phishing-detection",
                        "--disable-hang-monitor",
                        "--disable-prompt-on-repost",
                        "--disable-domain-reliability",
                        "--disable-component-update",
                        "--disable-features=InterestBasedFeatureSuggestions",
                        "--disable-features=AutofillServerCommunication",
                        "--disable-features=OptimizationHints"
                    ]
                )
            elif BROWSER_TYPE == "firefox":
                self.browser = await self.playwright.firefox.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                        "--disable-extensions",
                        "--disable-plugins",
                        "--disable-images",
                        "--disable-javascript-harmony-shipping",
                        "--disable-background-timer-throttling",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-renderer-backgrounding",
                        "--disable-features=TranslateUI",
                        "--disable-ipc-flooding-protection",
                        "--no-default-browser-check",
                        "--disable-default-apps",
                        "--disable-sync",
                        "--metrics-recording-only",
                        "--disable-background-networking",
                        "--disable-component-extensions-with-background-pages",
                        "--disable-background-mode",
                        "--disable-client-side-phishing-detection",
                        "--disable-hang-monitor",
                        "--disable-prompt-on-repost",
                        "--disable-domain-reliability",
                        "--disable-component-update",
                        "--disable-features=InterestBasedFeatureSuggestions",
                        "--disable-features=AutofillServerCommunication",
                        "--disable-features=OptimizationHints"
                    ]
                )
            else:
                # Default: chromium
                chromium_args = [
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-images",
                    "--disable-javascript-harmony-shipping",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-features=TranslateUI",
                    "--disable-ipc-flooding-protection",
                    "--no-default-browser-check",
                    "--disable-default-apps",
                    "--disable-sync",
                    "--metrics-recording-only",
                    "--disable-background-networking",
                    "--disable-component-extensions-with-background-pages",
                    "--disable-background-mode",
                    "--disable-client-side-phishing-detection",
                    "--disable-hang-monitor",
                    "--disable-prompt-on-repost",
                    "--disable-domain-reliability",
                    "--disable-component-update",
                    "--disable-features=InterestBasedFeatureSuggestions",
                    "--disable-features=AutofillServerCommunication",
                    "--disable-features=OptimizationHints",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-blink-features=AutomationControlled",
                    "--lang=en-US,en",
                    "--window-size=1280,720",
                    "--ignore-certificate-errors"
                ]
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=chromium_args
                )
            
            self.page = await self.browser.new_page()
            await self.stealth.apply_stealth_async(self.page)
            
            # User agent ve viewport ayarla
            await self.page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            
            await self.page.set_viewport_size({"width": 1280, "height": 720})
            
            logger.info(f"🌐 Browser başlatıldı ({BROWSER_TYPE} - optimize edilmiş)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Browser başlatma hatası: {e}")
            return False
    
    async def _debug_page(self):
        """
        Sayfa debug bilgilerini al
        """
        try:
            # Sayfa title'ını al
            title = await self.page.title()
            logger.info(f"🔍 Sayfa title: {title}")
            
            # URL'i kontrol et
            current_url = self.page.url
            logger.info(f"🔗 Mevcut URL: {current_url}")
            
            # Sayfa içeriğini kontrol et
            page_content = await self.page.content()
            if "XAUUSD" in page_content:
                logger.info("✅ Sayfada XAUUSD bulundu")
            else:
                logger.warning("⚠️ Sayfada XAUUSD bulunamadı")
            
            # Fiyat ile ilgili elementleri listele
            price_elements = await self.page.query_selector_all('[class*="price"], [class*="Price"], [data-role="price"]')
            logger.info(f"🔍 {len(price_elements)} fiyat elementi bulundu")
            
            # Tüm metinleri tara
            page_text = await self.page.evaluate("() => document.body.innerText")
            logger.info(f"📄 Sayfa metni (ilk 500 karakter): {page_text[:500]}")
            
            # Fiyat pattern'lerini ara
            price_patterns = [
                r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2,3})?)',  # $1,234.56 veya $1,234.567
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2,3})?)\s*USD',  # 1,234.56 USD veya 1,234.567 USD
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2,3})?)',  # 1,234.56 veya 1,234.567
            ]
            
            for pattern in price_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    logger.info(f"🔍 Pattern '{pattern}' ile bulunanlar: {matches[:5]}")
            
        except Exception as e:
            logger.error(f"❌ Debug hatası: {e}")
    
    async def get_price_from_xauusd_page(self) -> Optional[float]:
        """
        TradingView XAUUSD sayfasından fiyat çek
        """
        try:
            if not self.page:
                logger.error("❌ Browser sayfası hazır değil")
                return None
            
            logger.info(f"📊 {self.xauusd_url} adresinden fiyat çekiliyor...")
            
            # XAUUSD sayfasına git (optimize edilmiş)
            await self.page.goto(self.xauusd_url, wait_until="domcontentloaded", timeout=8000)
            # domcontentloaded daha hızlı, networkidle çok yavaş
            
            # Fiyat elementini bul (XAUUSD sayfasına özel selector'lar)
            price_selectors = [
                '.tv-symbol-price-quote__value',
                '.tv-symbol-price-quote__price',
                '[data-role="price"]',
                '.chart-markup-table__price',
                '[class*="price"]',
                '[class*="Price"]',
                '.tv-symbol-price-quote__value--last',
                '.tv-symbol-price-quote__value--bid',
                '.tv-symbol-price-quote__value--ask'
            ]
            
            price = None
            for selector in price_selectors:
                try:
                    # Element'i bekle
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    if element:
                        price_text = await element.text_content()
                        if price_text:
                            # Fiyat metnini temizle
                            price = self._extract_price_from_text(price_text)
                            if price:
                                logger.info(f"✅ Selector '{selector}' ile fiyat bulundu: ${price:.2f}")
                                return price
                except Exception as e:
                    continue
            
            if not price:
                # Alternatif yöntem: JavaScript ile fiyat çek
                price = await self._get_price_via_javascript()
            
            # Her durumda debug bilgilerini al
            await self._debug_page()
            
            return price
            
        except Exception as e:
            logger.error(f"❌ XAUUSD sayfasından fiyat çekme hatası: {e}")
            return None
    
    async def _get_price_via_javascript(self) -> Optional[float]:
        """
        JavaScript ile fiyat çek
        """
        try:
            # Sayfadaki tüm metinleri tara
            page_text = await self.page.evaluate("() => document.body.innerText")
            
            # Fiyat pattern'lerini ara (XAUUSD için optimize edilmiş)
            price_patterns = [
                r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2,3})?)',  # $1,234.56 veya $1,234.567
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2,3})?)\s*USD',  # 1,234.56 USD veya 1,234.567 USD
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2,3})?)',  # 1,234.56 veya 1,234.567
            ]
            
            logger.info(f"🔍 JavaScript ile sayfa metni taranıyor...")
            
            # Tüm bulunan fiyatları topla
            all_prices = []
            
            for pattern in price_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                logger.info(f"🔍 Pattern '{pattern}' ile bulunanlar: {matches[:5]}")
                
                for match in matches:
                    try:
                        # Virgülü kaldır ve float'a çevir
                        price_str = match.replace(',', '')
                        price = float(price_str)
                        
                        # Sadece mantıklı fiyat kontrolü (0'dan büyük)
                        if price > 0:
                            all_prices.append(price)
                    except ValueError:
                        continue
            
            # En güncel fiyatı bul (en mantıklı fiyat)
            if all_prices:
                # En mantıklı fiyatı bul (en büyük olan genelde en güncel)
                best_price = max(all_prices)
                logger.info(f"✅ JavaScript ile en mantıklı fiyat bulundu: ${best_price:.2f}")
                logger.info(f"🔍 Bulunan tüm fiyatlar: {all_prices}")
                return best_price
            
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
            logger.info(f"🔍 Fiyat metni: '{text}'")
            
            # Fiyat pattern'lerini ara
            price_patterns = [
                r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2,3})?)',  # $1,234.56 veya $1,234.567
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2,3})?)\s*USD',  # 1,234.56 USD veya 1,234.567 USD
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2,3})?)',  # 1,234.56 veya 1,234.567
            ]
            
            for pattern in price_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    price_str = match.group(1) if match.groups() else match.group(0)
                    # Virgülü kaldır
                    price_str = price_str.replace(',', '')
                    price = float(price_str)
                    
                    # Sadece mantıklı fiyat kontrolü (0'dan büyük)
                    if price > 0:
                        logger.info(f"✅ Metin'den fiyat çıkarıldı: ${price:.2f}")
                        return price
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Metin fiyat çıkarma hatası: {e}")
            return None
    
    async def update_price(self, price: float):
        """
        Yeni fiyatı güncelle ve değişim analizi yap
        """
        try:
            old_price = self.current_price
            self.current_price = price
            self.last_update = datetime.now()
            
            # Akıllı fiyat değişim analizi
            change_analysis = self.analyze_xauusd_price_change(price)
            
            # Fiyat geçmişine ekle
            price_data = {
                "price": price,
                "timestamp": self.last_update,
                "change": old_price - price if old_price else 0,
                "change_analysis": change_analysis,
                "source": "TradingView XAUUSD Page"
            }
            
            self.price_history.append(price_data)
            if len(self.price_history) > self.max_history_size:
                self.price_history.pop(0)
            
            # Log mesajı
            log_message = f"💰 XAUUSD OANDA: ${price:.2f} (Güncelleme: {self.last_update.strftime('%H:%M:%S')})"
            if change_analysis["is_warning"]:
                log_message += f" - {change_analysis['message']}"
            
            logger.info(log_message)
            
        except Exception as e:
            logger.error(f"❌ Fiyat güncelleme hatası: {e}")
    
    async def get_current_xauusd_price(self) -> Optional[float]:
        """
        Mevcut XAUUSD fiyatını al
        """
        return await self.get_price_from_xauusd_page()
    
    def get_current_price(self) -> Optional[float]:
        """
        Hafızadaki mevcut fiyatı döndür
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
            "symbol": "XAUUSD",
            "method": "TradingView XAUUSD Page",
            "url": self.xauusd_url
        }
    
    async def close_browser(self):
        """
        Browser'ı kapat
        """
        try:
            if self.page:
                await self.page.close()
                self.page = None
            if self.browser:
                await self.browser.close()
                self.browser = None
            if self.playwright_manager:
                await self.playwright_manager.__aexit__(None, None, None)
                self.playwright_manager = None
                self.playwright = None
            elif self.playwright:
                await self.playwright.stop()
                self.playwright = None
            
            logger.info("🌐 Browser kapatıldı")
            
        except Exception as e:
            logger.error(f"❌ Browser kapatma hatası: {e}")

    async def get_price_javascript_only(self) -> Optional[float]:
        """
        Sadece JavaScript ile fiyat çek (çok hızlı)
        """
        try:
            if not self.page:
                logger.error("❌ Browser sayfası hazır değil")
                return None
            
            logger.info("⚡ TradingView fiyatı için tarayıcı tabı hazırlanıyor...")
            await self.page.goto(self.xauusd_url, wait_until="networkidle", timeout=15000)
            await asyncio.sleep(2.5)
            
            if await self._is_captcha_displayed():
                logger.warning("🚧 TradingView CAPTCHA ekranı görüldü")
                return None
            
            price = await self._extract_price_from_next_data()
            if price:
                logger.info(f"✅ XAUUSD fiyatı __NEXT_DATA__ üzerinden bulundu: ${price:.2f}")
                return price
            
            price = await self._extract_price_from_dom_selectors()
            if price:
                logger.info(f"✅ XAUUSD fiyatı DOM selector ile bulundu: ${price:.2f}")
                return price
            
            price = await self._extract_price_from_text()
            if price:
                logger.info(f"✅ XAUUSD fiyatı metin analizi ile bulundu: ${price:.2f}")
                return price
            
            logger.warning("⚠️ TradingView tabında fiyat bulunamadı")
            return None
            
        except Exception as e:
            logger.error(f"❌ TradingView tabından fiyat çekme hatası: {e}")
            return None

    async def _is_captcha_displayed(self) -> bool:
        try:
            page_text = await self.page.evaluate("() => document.body.innerText.toLowerCase()")
            captcha_keywords = ["i am not a robot", "robot değil", "verify you are human", "captcha"]
            return any(keyword in page_text for keyword in captcha_keywords)
        except Exception:
            return False

    async def _extract_price_from_next_data(self) -> Optional[float]:
        try:
            script = await self.page.query_selector('script[id="__NEXT_DATA__"], script[type="application/json"][data-state]')
            if not script:
                return None
            
            content = await script.inner_text()
            json_data = json.loads(content)
            price = self._search_price_in_json(json_data)
            return price
        except Exception as e:
            logger.debug(f"__NEXT_DATA__ parse hatası: {e}")
            return None

    async def _extract_price_from_dom_selectors(self) -> Optional[float]:
        selectors = [
            '[data-symbol-name="OANDA:XAUUSD"] [data-role="price"]',
            '[data-symbol-name="XAUUSD"] [data-role="price"]',
            '.tv-symbol-price-quote__value',
            '[class*="last"] span',
            '[data-name="price"]',
        ]
        
        try:
            text_value = await self.page.evaluate(
                """(selectors) => {
                    const sanitize = (text) => {
                        if (!text) return null;
                        const match = text.replace(/\\s+/g, '').match(/\\d{3,5}(?:[.,]\\d{1,3})?/);
                        return match ? match[0] : null;
                    };
                    for (const selector of selectors) {
                        const el = document.querySelector(selector);
                        if (el) {
                            const value = sanitize(el.textContent);
                            if (value) {
                                return value;
                            }
                        }
                    }
                    return null;
                }""",
                selectors,
            )
            
            if text_value:
                return self._sanitize_price_string(text_value)
            return None
        except Exception as e:
            logger.debug(f"DOM selector fiyat çıkartma hatası: {e}")
            return None

    async def _extract_price_from_text(self) -> Optional[float]:
        try:
            page_text = await self.page.evaluate("() => document.body.innerText")
            logger.info(f"📄 Sayfa metni uzunluğu: {len(page_text)}")
            
            patterns = [
                r'XAUUSD[^\\d]*(\\d{3,5}(?:[.,]\\d{1,3})?)',
                r'(\\d{3,5}(?:[.,]\\d{1,3})?)\\s*USD',
                r'price[^\\d]*(\\d{3,5}(?:[.,]\\d{1,3})?)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    price = self._sanitize_price_string(match.group(1))
                    if price:
                        return price
            
            return None
        except Exception as e:
            logger.debug(f"Metin analizi hatası: {e}")
            return None

    def _search_price_in_json(self, data: Any) -> Optional[float]:
        price_keys = ["price", "lastPrice", "last", "lp", "close", "value"]
        target_symbols = {"XAUUSD", "OANDA:XAUUSD", "FOREXCOM:XAUUSD"}
        
        try:
            if isinstance(data, dict):
                symbol = data.get("symbol") or data.get("symbolName") or data.get("ticker")
                if symbol and symbol.upper() in target_symbols:
                    for key in price_keys:
                        if key in data:
                            price = self._sanitize_price_string(data[key])
                            if price:
                                return price
                
                for value in data.values():
                    price = self._search_price_in_json(value)
                    if price:
                        return price
            
            elif isinstance(data, list):
                for item in data:
                    price = self._search_price_in_json(item)
                    if price:
                        return price
        except Exception as e:
            logger.debug(f"JSON'dan fiyat arama hatası: {e}")
        
        return None

    def _sanitize_price_string(self, value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            if isinstance(value, (int, float)):
                return float(value)
            text = str(value)
            match = re.search(r'(\\d{3,5}(?:[.,]\\d{1,3})?)', text)
            if not match:
                return None
            price_str = match.group(1).replace(',', '')
            price = float(price_str)
            if 1000 <= price <= 4000:
                return price
            return None
        except Exception:
            return None

    def analyze_xauusd_price_change(self, new_price: float) -> dict:
        """
        XAUUSD fiyat değişimini analiz et (XAURUB gibi)
        """
        if self.last_known_price is None:
            self.last_known_price = new_price
            return {
                "is_first_price": True,
                "change_percent": 0.0,
                "change_amount": 0.0,
                "is_warning": False,
                "message": "💎 İlk XAUUSD fiyatı alındı",
            }

        change_amount = new_price - self.last_known_price
        change_percent = (change_amount / self.last_known_price) * 100

        is_warning = False
        message = f"💎 Normal XAUUSD değişim: {change_percent:.2f}%"

        # Uyarı eşiği: %0.5
        if abs(change_percent) > self.price_change_threshold:
            is_warning = True
            if change_percent > 0:
                message = f"⚠️ UYARI: XAUUSD %{change_percent:.2f} arttı! (${change_amount:.2f})"
            else:
                message = f"⚠️ UYARI: XAUUSD %{abs(change_percent):.2f} düştü! (${abs(change_amount):.2f})"

        self.last_known_price = new_price

        return {
            "is_first_price": False,
            "change_percent": change_percent,
            "change_amount": change_amount,
            "is_warning": is_warning,
            "message": message,
        }

# Test fonksiyonu
async def test_xauusd_fetcher():
    """
    XAUUSD fetcher'ı test et
    """
    fetcher = TradingViewChartFetcher()
    
    try:
        logger.info("🧪 TradingView XAUUSD Fetcher test ediliyor...")
        
        # Browser'ı başlat
        if await fetcher.start_browser():
            # Sadece JavaScript-only yöntem test et (çok hızlı!)
            logger.info("🧪 JavaScript-only yöntem test ediliyor...")
            js_price = await fetcher.get_price_javascript_only()
            if js_price:
                await fetcher.update_price(js_price)
                logger.info(f"✅ JavaScript-only yöntem başarılı! Fiyat: ${js_price:.2f}")
            
            # Fiyat bilgilerini göster
            info = fetcher.get_price_info()
            logger.info(f"📊 Fiyat bilgileri: {info}")
            
    except Exception as e:
        logger.error(f"❌ Test hatası: {e}")
    finally:
        await fetcher.close_browser()

if __name__ == "__main__":
    # Test çalıştır
    asyncio.run(test_xauusd_fetcher())
