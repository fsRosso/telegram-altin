import yfinance as yf
import logging
from typing import Dict, Optional
from config import PRICE_VALIDATION_TOLERANCE

logger = logging.getLogger(__name__)

class YFinanceFetcher:
    """yfinance ile fiyat çekme ve doğrulama"""
    
    def __init__(self):
        # Ticker sembolleri
        self.gold_ticker = "GC=F"  # XAUUSD (Altın)
        self.usd_rub_ticker = "USDRUB=X"  # USD/RUB döviz kuru
        
    def get_xauusd_price(self) -> Optional[float]:
        """XAUUSD (Altın) fiyatını çeker"""
        try:
            gold = yf.Ticker(self.gold_ticker)
            price = gold.info.get('regularMarketPrice')
            
            if price:
                logger.info(f"✅ yfinance XAUUSD: ${price:.2f}")
                return float(price)
            else:
                logger.warning("⚠️ yfinance XAUUSD verisi bulunamadı")
                return None
                
        except Exception as e:
            logger.error(f"❌ yfinance XAUUSD hatası: {e}")
            return None
    
    def get_usd_rub_rate(self) -> Optional[float]:
        """USD/RUB döviz kurunu çeker"""
        try:
            usd_rub = yf.Ticker(self.usd_rub_ticker)
            rate = usd_rub.info.get('regularMarketPrice')
            
            if rate:
                logger.info(f"✅ yfinance USD/RUB: {rate:.4f}")
                return float(rate)
            else:
                logger.warning("⚠️ yfinance USD/RUB verisi bulunamadı")
                return None
                
        except Exception as e:
            logger.error(f"❌ yfinance USD/RUB hatası: {e}")
            return None
    
    def calculate_xaurub_from_components(self) -> Optional[float]:
        """XAUUSD ve USD/RUB'den XAURUB hesaplar"""
        try:
            xauusd = self.get_xauusd_price()
            usd_rub = self.get_usd_rub_rate()
            
            if xauusd and usd_rub:
                calculated_xaurub = xauusd * usd_rub
                logger.info(f"✅ Hesaplanan XAURUB: {calculated_xaurub:.2f} RUB")
                return calculated_xaurub
            else:
                logger.warning("⚠️ XAURUB hesaplanamadı - eksik veri")
                return None
                
        except Exception as e:
            logger.error(f"❌ XAURUB hesaplama hatası: {e}")
            return None
    
    def validate_xaurub_price(self, direct_xaurub: float, tolerance_percent: float = None) -> Dict:
        """Direkt XAURUB ile hesaplanan XAURUB'yi karşılaştırır"""
        try:
            if tolerance_percent is None:
                tolerance_percent = PRICE_VALIDATION_TOLERANCE
                
            calculated_xaurub = self.calculate_xaurub_from_components()
            
            if calculated_xaurub is None:
                return {
                    "valid": False,
                    "error": "Hesaplanan XAURUB bulunamadı",
                    "direct_price": direct_xaurub,
                    "calculated_price": None,
                    "difference_percent": None
                }
            
            # Fark yüzdesi hesapla
            difference = abs(direct_xaurub - calculated_xaurub)
            difference_percent = (difference / calculated_xaurub) * 100
            
            # Tolerans kontrolü
            is_valid = difference_percent <= tolerance_percent
            
            result = {
                "valid": is_valid,
                "direct_price": direct_xaurub,
                "calculated_price": calculated_xaurub,
                "difference": difference,
                "difference_percent": difference_percent,
                "tolerance_percent": tolerance_percent,
                "status": "✅ Normal" if is_valid else "⚠️ Anormal"
            }
            
            if is_valid:
                logger.info(f"✅ XAURUB doğrulama başarılı: Fark %{difference_percent:.2f}")
            else:
                logger.warning(f"⚠️ XAURUB anormallik tespit edildi: Fark %{difference_percent:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ XAURUB doğrulama hatası: {e}")
            return {
                "valid": False,
                "error": str(e),
                "direct_price": direct_xaurub,
                "calculated_price": None,
                "difference_percent": None
            }
    
    def get_market_status(self) -> Dict:
        """Piyasa durumu özeti"""
        try:
            xauusd = self.get_xauusd_price()
            usd_rub = self.get_usd_rub_rate()
            
            status = {
                "xauusd": xauusd,
                "usd_rub": usd_rub,
                "calculated_xaurub": None,
                "timestamp": "Şimdi"
            }
            
            if xauusd and usd_rub:
                status["calculated_xaurub"] = xauusd * usd_rub
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Piyasa durumu hatası: {e}")
            return {"error": str(e)}
    
    def get_detailed_info(self) -> Dict:
        """Detaylı piyasa bilgileri"""
        try:
            gold = yf.Ticker(self.gold_ticker)
            usd_rub = yf.Ticker(self.usd_rub_ticker)
            
            gold_info = gold.info
            usd_rub_info = usd_rub.info
            
            detailed_info = {
                "gold": {
                    "price": gold_info.get('regularMarketPrice'),
                    "change": gold_info.get('regularMarketChange'),
                    "change_percent": gold_info.get('regularMarketChangePercent'),
                    "volume": gold_info.get('volume'),
                    "market_cap": gold_info.get('marketCap'),
                    "previous_close": gold_info.get('previousClose'),
                    "open": gold_info.get('regularMarketOpen'),
                    "day_high": gold_info.get('dayHigh'),
                    "day_low": gold_info.get('dayLow')
                },
                "usd_rub": {
                    "rate": usd_rub_info.get('regularMarketPrice'),
                    "change": usd_rub_info.get('regularMarketChange'),
                    "change_percent": usd_rub_info.get('regularMarketChangePercent'),
                    "previous_close": usd_rub_info.get('previousClose')
                }
            }
            
            return detailed_info
            
        except Exception as e:
            logger.error(f"❌ Detaylı bilgi hatası: {e}")
            return {"error": str(e)}

# Test fonksiyonu
if __name__ == "__main__":
    fetcher = YFinanceFetcher()
    
    print("🧪 yfinance Test:")
    print(f"XAUUSD: ${fetcher.get_xauusd_price()}")
    print(f"USD/RUB: {fetcher.get_usd_rub_rate()}")
    print(f"Hesaplanan XAURUB: {fetcher.calculate_xaurub_from_components()}")
    
    # Detaylı bilgi testi
    detailed = fetcher.get_detailed_info()
    if "error" not in detailed:
        print(f"\n📊 Detaylı Bilgiler:")
        print(f"Altın: ${detailed['gold']['price']} (Değişim: {detailed['gold']['change_percent']}%)")
        print(f"USD/RUB: {detailed['usd_rub']['rate']} (Değişim: {detailed['usd_rub']['change_percent']}%)")
