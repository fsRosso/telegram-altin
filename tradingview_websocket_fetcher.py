#!/usr/bin/env python3
"""
TradingView WebSocket Fetcher - tvdatafeed kütüphanesi ile
TradingView'in resmi WebSocket bağlantısını kullanarak XAUUSD fiyatlarını çeker
"""

import logging
import time
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from tvDatafeed import TvDatafeed, Interval

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingViewWebSocketFetcher:
    """
    TradingView WebSocket üzerinden XAUUSD fiyatlarını çeken sınıf
    tvdatafeed kütüphanesini kullanır
    """
    
    def __init__(self):
        # TradingView bağlantısı
        self.tv = TvDatafeed()
        
        # Fiyat verileri
        self.current_price: Optional[float] = None
        self.last_update: Optional[datetime] = None
        self.price_history: list[Dict[str, Any]] = []
        self.max_history_size = 100
        
        # Sembol bilgileri
        self.symbol = "XAUUSD"
        self.exchange = "OANDA"
        
        # Bağlantı durumu
        self.is_connected = True  # tvdatafeed her zaman bağlı
        
        logger.info("✅ TradingView WebSocket Fetcher başlatıldı")
    
    def get_current_price(self) -> Optional[float]:
        """
        Mevcut XAUUSD fiyatını döndür
        """
        try:
            # Son 1 mum verisi (en güncel)
            data = self.tv.get_hist(
                symbol=self.symbol,
                exchange=self.exchange,
                interval=Interval.in_1_minute,
                n_bars=1
            )
            
            if data is not None and not data.empty:
                price = data['close'].iloc[-1]
                self._update_price(price)
                return price
            else:
                logger.warning("⚠️ XAUUSD verisi alınamadı")
                return None
                
        except Exception as e:
            logger.error(f"❌ XAUUSD fiyat çekme hatası: {e}")
            return None
    
    def get_historical_data(self, n_bars: int = 5) -> Optional[Dict[str, Any]]:
        """
        Tarihsel veri çek
        """
        try:
            data = self.tv.get_hist(
                symbol=self.symbol,
                exchange=self.exchange,
                interval=Interval.in_1_minute,
                n_bars=n_bars
            )
            
            if data is not None and not data.empty:
                return {
                    "data": data,
                    "last_price": data['close'].iloc[-1],
                    "first_price": data['close'].iloc[0],
                    "timestamp": data.index[-1],
                    "bars_count": len(data)
                }
            else:
                logger.warning("⚠️ Tarihsel veri alınamadı")
                return None
                
        except Exception as e:
            logger.error(f"❌ Tarihsel veri çekme hatası: {e}")
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
            
            logger.info(f"💰 XAUUSD: ${price:.2f} (Güncelleme: {self.last_update.strftime('%H:%M:%S')})")
            
        except Exception as e:
            logger.error(f"❌ Fiyat güncelleme hatası: {e}")
    
    def get_price_info(self) -> Dict[str, Any]:
        """
        Detaylı fiyat bilgisi döndür
        """
        return {
            "current_price": self.current_price,
            "last_update": self.last_update,
            "is_connected": self.is_connected,
            "price_history_count": len(self.price_history),
            "symbol": f"{self.symbol}:{self.exchange}"
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
    
    def get_gram_price(self, usd_to_rub_rate: float = 100.0) -> Optional[float]:
        """
        XAUUSD fiyatını gram başına RUB cinsinden hesapla
        """
        try:
            if self.current_price is None:
                return None
            
            # 1 troy ounce = 31.1035 gram
            # XAUUSD fiyatını 31.1035'e böl ve USD'den RUB'e çevir
            gram_price_usd = self.current_price / 31.1035
            gram_price_rub = gram_price_usd * usd_to_rub_rate
            
            return gram_price_rub
            
        except Exception as e:
            logger.error(f"❌ Gram fiyat hesaplama hatası: {e}")
            return None
    
    def start_monitoring(self, interval_seconds: int = 30):
        """
        Fiyat izlemeyi başlat (opsiyonel)
        """
        try:
            logger.info(f"🔄 XAUUSD fiyat izleme başlatıldı ({interval_seconds}s aralık)")
            
            while True:
                price = self.get_current_price()
                if price:
                    analysis = self.analyze_price_change(price)
                    if analysis["is_warning"]:
                        logger.warning(f"⚠️ {analysis['message']}")
                
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("🛑 Fiyat izleme durduruldu")
        except Exception as e:
            logger.error(f"❌ Fiyat izleme hatası: {e}")

# Test fonksiyonu
def test_tradingview_websocket_fetcher():
    """
    TradingView WebSocket Fetcher'ı test et
    """
    try:
        logger.info("🧪 TradingView WebSocket Fetcher test ediliyor...")
        
        fetcher = TradingViewWebSocketFetcher()
        
        # Test 1: Mevcut fiyat
        logger.info("📊 Test 1: Mevcut fiyat")
        price = fetcher.get_current_price()
        if price:
            logger.info(f"✅ XAUUSD fiyatı: ${price:.2f}")
        else:
            logger.error("❌ Fiyat alınamadı")
            return False
        
        # Test 2: Tarihsel veri
        logger.info("📈 Test 2: Tarihsel veri")
        hist_data = fetcher.get_historical_data(5)
        if hist_data:
            logger.info(f"✅ Tarihsel veri: {hist_data['bars_count']} mum")
            logger.info(f"📊 Son fiyat: ${hist_data['last_price']:.2f}")
        else:
            logger.error("❌ Tarihsel veri alınamadı")
            return False
        
        # Test 3: Fiyat analizi
        logger.info("🔍 Test 3: Fiyat analizi")
        analysis = fetcher.analyze_price_change(price)
        logger.info(f"📊 Analiz: {analysis['message']}")
        
        # Test 4: Gram fiyatı
        logger.info("⚖️ Test 4: Gram fiyatı")
        gram_price = fetcher.get_gram_price(100.0)  # 1 USD = 100 RUB varsayımı
        if gram_price:
            logger.info(f"✅ Gram fiyatı: {gram_price:.4f} RUB/gram")
        
        logger.info("🎉 Tüm testler başarılı!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test hatası: {e}")
        return False

if __name__ == "__main__":
    # Test çalıştır
    test_tradingview_websocket_fetcher()
