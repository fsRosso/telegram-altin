"""
TradingView Technical Analysis (tradingview-ta) ile XAUUSD fiyat çekici
Playwright yerine daha hafif ve hızlı bir kütüphane
"""

import logging
from tradingview_ta import TA_Handler, Interval
import asyncio

logger = logging.getLogger(__name__)

class TradingViewTAFetcher:
    """
    TradingView Technical Analysis kütüphanesi ile XAUUSD fiyat çekici
    """
    
    def __init__(self):
        self.last_price = None
        self.handler = None
        self._initialize_handler()
    
    def _initialize_handler(self):
        """TradingView handler'ı başlatır"""
        try:
            # XAUUSD için TradingView handler
            # Önemli: OANDA XAUUSD için screener='cfd' olmalı!
            self.handler = TA_Handler(
                symbol="XAUUSD",
                screener="cfd",  # OANDA XAUUSD için 'cfd' screener gerekli
                exchange="OANDA",  # OANDA forex broker
                interval=Interval.INTERVAL_1_MINUTE  # 1 dakikalık veri
            )
            logger.info("✅ TradingView TA Handler başlatıldı (OANDA:XAUUSD)")
        except Exception as e:
            logger.error(f"❌ Handler başlatma hatası: {e}")
            self.handler = None
    
    def get_price(self):
        """
        XAUUSD fiyatını çeker (senkron)
        
        Returns:
            float: XAUUSD fiyatı veya None
        """
        try:
            if not self.handler:
                self._initialize_handler()
                if not self.handler:
                    logger.error("Handler başlatılamadı")
                    return None
            
            # TradingView'den analiz verisini al
            analysis = self.handler.get_analysis()
            
            # Kapanış fiyatı (o anki fiyat)
            price = analysis.indicators.get("close")
            
            if price:
                self.last_price = price
                logger.info(f"✅ XAUUSD fiyatı çekildi: ${price:.2f}")
                return price
            else:
                logger.warning("⚠️ Fiyat verisi bulunamadı")
                return None
                
        except Exception as e:
            logger.error(f"❌ Fiyat çekme hatası: {e}")
            return None
    
    async def get_price_async(self):
        """
        XAUUSD fiyatını asenkron olarak çeker
        
        Returns:
            float: XAUUSD fiyatı veya None
        """
        # Senkron fonksiyonu async ortamda çalıştır
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_price)
    
    def get_full_analysis(self):
        """
        Tam teknik analiz verisini çeker
        
        Returns:
            dict: Analiz verisi veya None
        """
        try:
            if not self.handler:
                self._initialize_handler()
                if not self.handler:
                    return None
            
            analysis = self.handler.get_analysis()
            
            result = {
                "price": analysis.indicators.get("close"),
                "open": analysis.indicators.get("open"),
                "high": analysis.indicators.get("high"),
                "low": analysis.indicators.get("low"),
                "volume": analysis.indicators.get("volume"),
                "recommendation": analysis.summary.get("RECOMMENDATION"),
                "buy_signals": analysis.summary.get("BUY"),
                "sell_signals": analysis.summary.get("SELL"),
                "neutral_signals": analysis.summary.get("NEUTRAL"),
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Analiz çekme hatası: {e}")
            return None


# Test fonksiyonu
if __name__ == "__main__":
    import time
    
    print("🚀 TradingView TA Fetcher Test")
    print("-" * 50)
    
    fetcher = TradingViewTAFetcher()
    
    print("\n1️⃣ Basit Fiyat Çekme Testi:")
    price = fetcher.get_price()
    if price:
        print(f"✅ XAUUSD Fiyat: ${price:.2f}")
    else:
        print("❌ Fiyat çekilemedi")
    
    print("\n2️⃣ Detaylı Analiz Testi:")
    analysis = fetcher.get_full_analysis()
    if analysis:
        print(f"💎 Fiyat: ${analysis['price']:.2f}")
        print(f"📊 Açılış: ${analysis['open']:.2f}")
        print(f"📈 Yüksek: ${analysis['high']:.2f}")
        print(f"📉 Düşük: ${analysis['low']:.2f}")
        print(f"🔔 Öneri: {analysis['recommendation']}")
        print(f"📊 Al/Sat/Nötr: {analysis['buy_signals']}/{analysis['sell_signals']}/{analysis['neutral_signals']}")
    else:
        print("❌ Analiz çekilemedi")
    
    print("\n3️⃣ Async Test:")
    async def async_test():
        price = await fetcher.get_price_async()
        if price:
            print(f"✅ Async XAUUSD Fiyat: ${price:.2f}")
        else:
            print("❌ Async fiyat çekilemedi")
    
    asyncio.run(async_test())
    
    print("\n✅ Test tamamlandı!")

