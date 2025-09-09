#!/usr/bin/env python3
"""
ProFinance.ru History Fetcher - Gerçek Fiyat Verisi ile
ProFinance.ru'nun history endpoint'ini kullanarak XAURUB fiyatlarını çeker
"""

import asyncio
import aiohttp
import logging
import time
import re
import random
from datetime import datetime
from typing import Optional, Dict, Any
from user_agent_rotator import user_agent_rotator
from proxy_manager_enhanced import proxy_manager

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProFinanceHistoryFetcher:
    """
    ProFinance.ru History API üzerinden XAURUB fiyatlarını çeken sınıf
    Gerçek fiyat verisini history endpoint'inden alır
    """
    
    def __init__(self):
        # ProFinance.ru API endpoint'leri
        self.base_url = "https://charts.profinance.ru/html/charts"
        self.refresh_url = f"{self.base_url}/refresh"
        self.history_url = f"{self.base_url}/history"
        
        # Sembol bilgileri
        self.symbol = "GOLDGRRUB"
        self.session_id = None
        
        # Fiyat verileri
        self.current_price: Optional[float] = None
        self.last_update: Optional[datetime] = None
        self.price_history: list[Dict[str, Any]] = []
        self.max_history_size = 100
        
        # HTTP session
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Headers - User-Agent rotasyonu ile
        self.headers = {
            "User-Agent": user_agent_rotator.get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0"
        }
        
        logger.info("✅ ProFinance History Fetcher başlatıldı")
    
    async def __aenter__(self):
        """Async context manager girişi"""
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager çıkışı"""
        if self.session:
            await self.session.close()
    
    async def get_session_id(self) -> Optional[str]:
        """
        Session ID al
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(headers=self.headers)
            
            # User-Agent rotasyonu
            self.headers["User-Agent"] = user_agent_rotator.get_next_user_agent()
            
            # Proxy al (sadece mevcut çalışan proxy'lerden, test yapmadan)
            proxy = proxy_manager.get_random_proxy()
            proxy_url = proxy['http'] if proxy else None
            
            # Refresh endpoint'ini çağır
            params = {"s": self.symbol}
            async with self.session.get(self.refresh_url, params=params, proxy=proxy_url) as response:
                if response.status == 200:
                    text = await response.text()
                    
                    # Session ID'yi bul (format: "1;y6w7YQyO")
                    sid_match = re.search(r'1;([a-zA-Z0-9]+)', text)
                    if sid_match:
                        self.session_id = sid_match.group(1)
                        logger.info(f"✅ Session ID alındı: {self.session_id}")
                        return self.session_id
                    else:
                        logger.warning("⚠️ Session ID bulunamadı")
                        return None
                else:
                    logger.error(f"❌ Session ID alınamadı: HTTP {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Session ID alma hatası: {e}")
            return None
    
    async def get_current_price(self) -> Optional[float]:
        """
        Mevcut XAURUB fiyatını döndür
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(headers=self.headers)
            
            # Session ID yoksa al
            if not self.session_id:
                await self.get_session_id()
            
            if not self.session_id:
                logger.error("❌ Session ID alınamadı")
                return None
            
            # User-Agent rotasyonu
            self.headers["User-Agent"] = user_agent_rotator.get_next_user_agent()
            
            # Proxy al (sadece mevcut çalışan proxy'lerden, test yapmadan)
            proxy = proxy_manager.get_random_proxy()
            proxy_url = proxy['http'] if proxy else None
            
            # History endpoint'ini çağır
            params = {
                "SID": self.session_id,
                "s": "goldgrrub",
                "h": "400",
                "w": "728",
                "pt": "4",
                "tt": "0",
                "z": "7",
                "ba": "2",
                "left": "0",
                "T": str(int(time.time() * 1000))
            }
            
            async with self.session.get(self.history_url, params=params, proxy=proxy_url) as response:
                if response.status == 200:
                    text = await response.text()
                    
                    # Fiyatı parse et
                    price = self._parse_price_from_history(text)
                    if price:
                        self._update_price(price)
                        return price
                    else:
                        logger.warning("⚠️ Fiyat parse edilemedi")
                        return None
                else:
                    logger.error(f"❌ Fiyat alınamadı: HTTP {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Fiyat çekme hatası: {e}")
            return None
    
    def _parse_price_from_history(self, text: str) -> Optional[float]:
        """
        History response'dan fiyatı parse et
        Format: ";Bid;Ask;Last;Время\n;9817.16;9821.23;;20:29:25.000\n;9817.47;9821.52;9819.26;20:29:25.000"
        """
        try:
            # CSV formatını parse et
            lines = text.strip().split('\n')
            
            if len(lines) < 2:
                logger.warning("⚠️ Yetersiz veri satırı")
                return None
            
            # İlk satır header: ";Bid;Ask;Last;Время"
            # İkinci satır veri: ";9817.16;9821.23;;20:29:25.000"
            
            for line in lines[1:]:  # Header'ı atla
                if not line.strip():
                    continue
                
                # Satırı parse et
                parts = line.split(';')
                if len(parts) >= 4:
                    try:
                        bid = float(parts[1]) if parts[1] else None
                        ask = float(parts[2]) if parts[2] else None
                        last = float(parts[3]) if parts[3] else None
                        time_str = parts[4] if len(parts) > 4 else ""
                        
                        # Last fiyatı varsa onu kullan
                        if last and 50 < last < 10000:  # Makul fiyat aralığı
                            logger.info(f"✅ ProFinance Last fiyatı: {last} RUB (Zaman: {time_str})")
                            return last
                        
                        # Last yoksa Bid ve Ask'in ortalamasını al
                        if bid and ask and 50 < bid < 10000 and 50 < ask < 10000:
                            avg_price = (bid + ask) / 2
                            logger.info(f"✅ ProFinance ortalama fiyat: {avg_price} RUB (Bid: {bid}, Ask: {ask})")
                            return avg_price
                        
                        # Sadece Bid varsa onu kullan
                        if bid and 50 < bid < 10000:
                            logger.info(f"✅ ProFinance Bid fiyatı: {bid} RUB")
                            return bid
                        
                        # Sadece Ask varsa onu kullan
                        if ask and 50 < ask < 10000:
                            logger.info(f"✅ ProFinance Ask fiyatı: {ask} RUB")
                            return ask
                            
                    except (ValueError, IndexError) as e:
                        logger.warning(f"⚠️ Satır parse hatası: {line} - {e}")
                        continue
            
            logger.warning("⚠️ Geçerli fiyat bulunamadı")
            return None
            
        except Exception as e:
            logger.error(f"❌ History parse hatası: {e}")
            return None
    
    def _update_price(self, price: float):
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
                "change": price - old_price if old_price else 0,
                "change_percent": ((price - old_price) / old_price * 100) if old_price else 0
            }
            
            self.price_history.append(price_data)
            if len(self.price_history) > self.max_history_size:
                self.price_history.pop(0)
            
            logger.info(f"💰 XAURUB: {price:.2f} RUB (Güncelleme: {self.last_update.strftime('%H:%M:%S')})")
            
        except Exception as e:
            logger.error(f"❌ Fiyat güncelleme hatası: {e}")
    
    def get_price_info(self) -> Dict[str, Any]:
        """
        Detaylı fiyat bilgisi döndür
        """
        return {
            "current_price": self.current_price,
            "last_update": self.last_update,
            "session_id": self.session_id,
            "price_history_count": len(self.price_history),
            "symbol": self.symbol
        }
    
    def analyze_price_change(self, price: float) -> Dict[str, Any]:
        """
        Fiyat değişimini analiz et
        """
        try:
            if not self.price_history:
                return {
                    "is_warning": False,
                    "message": "Yeterli veri yok",
                    "change_percent": 0
                }
            
            # Son 5 fiyatın ortalamasını al
            recent_prices = [p["price"] for p in self.price_history[-5:]]
            avg_price = sum(recent_prices) / len(recent_prices)
            
            # Fiyat değişim yüzdesi
            change_percent = ((price - avg_price) / avg_price) * 100
            
            # Uyarı eşiği %0.5
            is_warning = abs(change_percent) > 0.5
            
            if is_warning:
                direction = "yükseliş" if change_percent > 0 else "düşüş"
                message = f"⚠️ Hızlı {direction}: %{abs(change_percent):.2f}"
            else:
                message = f"📊 Normal değişim: %{change_percent:.2f}"
            
            return {
                "is_warning": is_warning,
                "message": message,
                "change_percent": change_percent,
                "avg_price": avg_price
            }
            
        except Exception as e:
            logger.error(f"❌ Fiyat analizi hatası: {e}")
            return {
                "is_warning": False,
                "message": "Analiz hatası",
                "change_percent": 0
            }

# Test fonksiyonu
async def test_profinance_history_fetcher():
    """
    ProFinance History Fetcher'ı test et
    """
    try:
        logger.info("🧪 ProFinance History Fetcher test ediliyor...")
        
        async with ProFinanceHistoryFetcher() as fetcher:
            # Test 1: Mevcut fiyat
            logger.info("📊 Test 1: Mevcut fiyat")
            price = await fetcher.get_current_price()
            if price:
                logger.info(f"✅ XAURUB fiyatı: {price:.2f} RUB")
            else:
                logger.error("❌ Fiyat alınamadı")
                return False
            
            # Test 2: Fiyat analizi
            logger.info("🔍 Test 2: Fiyat analizi")
            analysis = fetcher.analyze_price_change(price)
            logger.info(f"📊 Analiz: {analysis['message']}")
            
            # Test 3: Birkaç kez daha fiyat çek
            logger.info("🔄 Test 3: Çoklu fiyat çekme")
            for i in range(3):
                price = await fetcher.get_current_price()
                if price:
                    logger.info(f"✅ Fiyat {i+1}: {price:.2f} RUB")
                await asyncio.sleep(2)
            
            logger.info("🎉 Tüm testler başarılı!")
            return True
        
    except Exception as e:
        logger.error(f"❌ Test hatası: {e}")
        return False

if __name__ == "__main__":
    # Test çalıştır
    asyncio.run(test_profinance_history_fetcher())
