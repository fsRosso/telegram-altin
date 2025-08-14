import requests
import logging
from typing import Dict, Optional, Tuple
from config import ALPHA_VANTAGE_API_KEY

logger = logging.getLogger(__name__)

class AlphaVantageFetcher:
    """Alpha Vantage API ile fiyat çekme ve doğrulama"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or ALPHA_VANTAGE_API_KEY
        self.base_url = "https://www.alphavantage.co/query"
        
    def get_xauusd_price(self) -> Optional[float]:
        """XAUUSD (Altın) fiyatını çeker"""
        try:
            params = {
                "function": "CURRENCY_EXCHANGE_RATE",
                "from_currency": "XAU",
                "to_currency": "USD",
                "apikey": self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if "Realtime Currency Exchange Rate" in data:
                rate_info = data["Realtime Currency Exchange Rate"]
                price = float(rate_info["5. Exchange Rate"])
                logger.info(f"✅ Alpha Vantage XAUUSD: ${price:.2f}")
                return price
            else:
                logger.warning("⚠️ Alpha Vantage XAUUSD verisi bulunamadı")
                return None
                
        except Exception as e:
            logger.error(f"❌ Alpha Vantage XAUUSD hatası: {e}")
            return None
    
    def get_usd_rub_rate(self) -> Optional[float]:
        """USD/RUB döviz kurunu çeker"""
        try:
            params = {
                "function": "CURRENCY_EXCHANGE_RATE",
                "from_currency": "USD",
                "to_currency": "RUB",
                "apikey": self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if "Realtime Currency Exchange Rate" in data:
                rate_info = data["Realtime Currency Exchange Rate"]
                rate = float(rate_info["5. Exchange Rate"])
                logger.info(f"✅ Alpha Vantage USD/RUB: {rate:.4f}")
                return rate
            else:
                logger.warning("⚠️ Alpha Vantage USD/RUB verisi bulunamadı")
                return None
                
        except Exception as e:
            logger.error(f"❌ Alpha Vantage USD/RUB hatası: {e}")
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
    
    def validate_xaurub_price(self, direct_xaurub: float, tolerance_percent: float = 5.0) -> Dict:
        """Direkt XAURUB ile hesaplanan XAURUB'yi karşılaştırır"""
        try:
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
                "timestamp": None
            }
            
            if xauusd and usd_rub:
                status["calculated_xaurub"] = xauusd * usd_rub
                status["timestamp"] = "Şimdi"
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Piyasa durumu hatası: {e}")
            return {"error": str(e)}

# Test fonksiyonu
if __name__ == "__main__":
    fetcher = AlphaVantageFetcher()
    
    print("🧪 Alpha Vantage Test:")
    print(f"XAUUSD: ${fetcher.get_xauusd_price()}")
    print(f"USD/RUB: {fetcher.get_usd_rub_rate()}")
    print(f"Hesaplanan XAURUB: {fetcher.calculate_xaurub_from_components()}")
