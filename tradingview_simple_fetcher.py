import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
import logging
import re

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingViewSimpleFetcher:
    """
    TradingView'dan XAUUSD OANDA fiyatını en basit yöntemle çeken sınıf
    """
    
    def __init__(self):
        # TradingView endpoint'leri
        self.symbol_page_url = "https://www.tradingview.com/symbols/XAUUSD/"
        self.api_urls = [
            "https://www.tradingview.com/markets/currencies/pairs-all/",
            "https://www.tradingview.com/symbols/FOREX-XAUUSD/",
            "https://www.tradingview.com/symbols/OANDA-XAUUSD/"
        ]
        
        # Fiyat verileri
        self.current_price: Optional[float] = None
        self.last_update: Optional[datetime] = None
        self.price_history: list[Dict[str, Any]] = []
        self.max_history_size = 100
        
        # HTTP session
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Origin": "https://www.tradingview.com",
            "Referer": "https://www.tradingview.com/",
        }
        
    async def start_session(self):
        """
        HTTP session başlat
        """
        try:
            self.session = aiohttp.ClientSession(headers=self.base_headers)
            logger.info("🌐 HTTP session başlatıldı")
            return True
            
        except Exception as e:
            logger.error(f"❌ Session başlatma hatası: {e}")
            return False
    
    async def get_price_from_symbol_page(self) -> Optional[float]:
        """
        TradingView sembol sayfasından (XAUUSD) fiyat çek
        """
        if not self.session:
            return None
        
        try:
            async with self.session.get(self.symbol_page_url, timeout=12) as response:
                if response.status != 200:
                    logger.warning(f"⚠️ Symbol page HTTP {response.status}")
                    return None
                
                html_content = await response.text()
                price = self._extract_price_from_html(html_content)
                if price:
                    logger.info(f"✅ Symbol sayfasından fiyat bulundu: ${price:.2f}")
                    return price
        except asyncio.TimeoutError:
            logger.warning("⏰ Symbol sayfası timeout")
        except Exception as e:
            logger.error(f"❌ Symbol sayfası hata: {e}")
        
        return None

    async def get_price_from_api(self) -> Optional[float]:
        """
        TradingView API'larından fiyat çek
        """
        if not self.session:
            logger.error("❌ HTTP session hazır değil")
            return None
        
        for url in self.api_urls:
            try:
                logger.info(f"📊 {url} adresinden fiyat çekiliyor...")
                
                async with self.session.get(url, timeout=10) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        
                        # Fiyat pattern'lerini ara
                        price = self._extract_price_from_html(html_content)
                        if price:
                            logger.info(f"✅ {url} adresinden fiyat bulundu: ${price:.2f}")
                            return price
                    else:
                        logger.warning(f"⚠️ {url} - HTTP {response.status}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"⏰ {url} - Timeout")
            except Exception as e:
                logger.warning(f"❌ {url} - Hata: {e}")
                continue
        
        return None
    
    def _extract_price_from_html(self, html_content: str) -> Optional[float]:
        """
        HTML içinden fiyat çıkar
        """
        try:
            json_price = self._extract_price_from_json_blob(html_content)
            if json_price:
                return json_price
            
            # Fiyat pattern'lerini ara (daha kapsamlı)
            price_patterns = [
                r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $1,234.56
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*USD',  # 1,234.56 USD
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*\$',  # 1,234.56 $
                r'price["\']?\s*:\s*["\']?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # price: "1,234.56"
                r'value["\']?\s*:\s*["\']?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # value: "1,234.56"
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*</span>',  # 1,234.56</span>
                r'<span[^>]*>(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)</span>',  # <span>1,234.56</span>
                r'data-last-price\s*=\s*"(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"',
                r'"lp"\s*:\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2,3})?)',
            ]
            
            for pattern in price_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    try:
                        # Virgülü kaldır ve float'a çevir
                        price_str = match.replace(',', '')
                        price = float(price_str)
                        
                        # Mantıklı fiyat aralığı kontrolü (altın için 1000-3000 arası)
                        if 1000 <= price <= 3000:
                            logger.info(f"✅ HTML'den fiyat bulundu: ${price:.2f}")
                            return price
                    except ValueError:
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"❌ HTML fiyat çıkarma hatası: {e}")
            return None

    def _extract_price_from_json_blob(self, html_content: str) -> Optional[float]:
        try:
            json_patterns = [
                r'window\.__data\s*=\s*(\{.*?\})\s*;</script>',
                r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});',
                r'window\.__NEXT_DATA__\s*=\s*(\{.*?\});',
            ]
            for pattern in json_patterns:
                match = re.search(pattern, html_content, re.DOTALL)
                if match:
                    blob = match.group(1)
                    price = self._search_price_in_dict(blob)
                    if price:
                        return price
        except Exception as e:
            logger.debug(f"JSON blob parse hatası: {e}")
        return None

    def _search_price_in_dict(self, blob: str) -> Optional[float]:
        try:
            data = json.loads(blob)
        except Exception:
            try:
                cleaned = blob.replace("\\'", "'")
                data = json.loads(cleaned)
            except Exception:
                return None
        
        target_symbols = {"XAUUSD", "OANDA:XAUUSD", "FOREXCOM:XAUUSD"}
        price_keys = ["price", "lastPrice", "lp", "close", "regular_session_close"]
        
        def search(obj):
            if isinstance(obj, dict):
                symbol = obj.get("symbol") or obj.get("symbolName") or obj.get("ticker")
                if symbol and symbol.upper() in target_symbols:
                    for key in price_keys:
                        if key in obj:
                            try:
                                value = float(str(obj[key]).replace(',', ''))
                                if 1000 <= value <= 4000:
                                    return value
                            except Exception:
                                continue
                for v in obj.values():
                    price = search(v)
                    if price:
                        return price
            elif isinstance(obj, list):
                for item in obj:
                    price = search(item)
                    if price:
                        return price
            return None
        
        return search(data)
    
    async def get_price_from_search(self) -> Optional[float]:
        """
        TradingView search API'sından fiyat çek
        """
        if not self.session:
            return None
        
        try:
            # TradingView search endpoint
            search_url = "https://www.tradingview.com/api/v1/search/overview/"
            search_params = {
                "query": "XAUUSD",
                "type": "symbols",
                "exchange": "OANDA"
            }
            
            logger.info("🔍 TradingView search API'sından fiyat çekiliyor...")
            
            async with self.session.get(search_url, params=search_params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # JSON'dan fiyat çıkar
                    if 'data' in data and 'symbols' in data['data']:
                        for symbol in data['data']['symbols']:
                            if 'XAUUSD' in symbol.get('symbol', ''):
                                price = symbol.get('price')
                                if price:
                                    try:
                                        price_float = float(price)
                                        if 1000 <= price_float <= 3000:
                                            logger.info(f"✅ Search API'dan fiyat bulundu: ${price_float:.2f}")
                                            return price_float
                                    except ValueError:
                                        continue
                
                return None
                
        except Exception as e:
            logger.warning(f"❌ Search API hatası: {e}")
            return None
    
    async def get_price_from_market_data(self) -> Optional[float]:
        """
        TradingView market data API'sından fiyat çek
        """
        if not self.session:
            return None
        
        try:
            # Market data endpoint (tahmini)
            market_url = "https://www.tradingview.com/api/v1/symbols/OANDA:XAUUSD/quote/"
            
            logger.info("📊 Market data API'sından fiyat çekiliyor...")
            
            async with self.session.get(market_url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # JSON'dan fiyat çıkar
                    price = data.get('price') or data.get('last_price') or data.get('close')
                    if price:
                        try:
                            price_float = float(price)
                            if 1000 <= price_float <= 3000:
                                logger.info(f"✅ Market data API'dan fiyat bulundu: ${price_float:.2f}")
                                return price_float
                        except ValueError:
                            pass
                
                return None
                
        except Exception as e:
            logger.warning(f"❌ Market data API hatası: {e}")
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
                "source": "TradingView Simple Fetcher"
            }
            
            self.price_history.append(price_data)
            if len(self.price_history) > self.max_history_size:
                self.price_history.pop(0)
            
            logger.info(f"💰 XAUUSD OANDA: ${price:.2f} (Güncelleme: {self.last_update.strftime('%H:%M:%S')})")
            
        except Exception as e:
            logger.error(f"❌ Fiyat güncelleme hatası: {e}")
    
    async def get_best_price(self) -> Optional[float]:
        """
        En iyi fiyatı bul (birden fazla yöntem dene)
        """
        logger.info("🔍 En iyi fiyat aranıyor...")
        
        if not self.session or self.session.closed:
            started = await self.start_session()
            if not started:
                logger.error("❌ HTTP session başlatılamadı, fallback fiyat alınamadı")
                return None
        
        # 0. Direkt sembol sayfasını dene
        price = await self.get_price_from_symbol_page()
        if price:
            return price
        
        # 1. Önce search API'dan dene
        price = await self.get_price_from_search()
        if price:
            return price
        
        # 2. Market data API'dan dene
        price = await self.get_price_from_market_data()
        if price:
            return price
        
        # 3. HTML parsing ile dene
        price = await self.get_price_from_api()
        if price:
            return price
        
        logger.warning("⚠️ Hiçbir yöntemle fiyat bulunamadı")
        return None
    
    async def continuous_price_monitoring(self, interval: int = 30):
        """
        Sürekli fiyat izleme
        """
        try:
            logger.info(f"🔄 Sürekli fiyat izleme başlatıldı (her {interval} saniyede)")
            
            while True:
                # En iyi fiyatı bul
                price = await self.get_best_price()
                
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
            "method": "Simple Fetcher"
        }
    
    async def close_session(self):
        """
        HTTP session'ı kapat
        """
        try:
            if self.session:
                await self.session.close()
                logger.info("🌐 HTTP session kapatıldı")
        except Exception as e:
            logger.error(f"❌ Session kapatma hatası: {e}")

# Test fonksiyonu
async def test_simple_fetcher():
    """
    Simple fetcher'ı test et
    """
    fetcher = TradingViewSimpleFetcher()
    
    try:
        logger.info("🧪 TradingView Simple Fetcher test ediliyor...")
        
        # Session'ı başlat
        if await fetcher.start_session():
            # Tek seferlik fiyat çek
            price = await fetcher.get_best_price()
            if price:
                await fetcher.update_price(price)
                logger.info(f"✅ Test başarılı! Fiyat: ${price:.2f}")
            else:
                logger.error("❌ Test başarısız - fiyat bulunamadı")
            
            # 15 saniye boyunca sürekli izleme
            logger.info("🔄 15 saniye boyunca sürekli izleme...")
            await asyncio.wait_for(
                fetcher.continuous_price_monitoring(interval=3),
                timeout=15.0
            )
            
    except asyncio.TimeoutError:
        logger.info("⏰ Test süresi doldu")
    except Exception as e:
        logger.error(f"❌ Test hatası: {e}")
    finally:
        await fetcher.close_session()

if __name__ == "__main__":
    # Test çalıştır
    asyncio.run(test_simple_fetcher())



