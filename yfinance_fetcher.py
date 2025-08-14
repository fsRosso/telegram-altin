import yfinance as yf
import logging
import os
from typing import Dict, Optional
from config import PRICE_VALIDATION_TOLERANCE

# Railway'de cache sorunu için cache dizinini /tmp'ye yönlendir
try:
    import appdirs
    # Cache dizinini geçici klasöre yönlendir
    appdirs.user_cache_dir = lambda *args: "/tmp"
    logging.info("✅ Cache dizini /tmp'ye yönlendirildi")
except ImportError:
    logging.warning("⚠️ appdirs bulunamadı, cache yönlendirmesi yapılamadı")

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
            # Rate limiting için kısa bekleme
            import time
            time.sleep(0.5)  # 500ms bekle
            
            gold = yf.Ticker(self.gold_ticker)
            
            # Önce info metodunu dene
            try:
                info = gold.info
                if info and 'regularMarketPrice' in info:
                    price = info['regularMarketPrice']
                    if price:
                        logger.info(f"✅ yfinance XAUUSD (info): ${price:.2f}")
                        return float(price)
            except Exception as e:
                logger.warning(f"⚠️ yfinance info hatası: {e}")
            
            # info çalışmazsa history metodunu dene
            try:
                hist = gold.history(period="1d")
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
                    logger.info(f"✅ yfinance XAUUSD (history): ${price:.2f}")
                    return float(price)
            except Exception as e:
                logger.warning(f"⚠️ yfinance history hatası: {e}")
            
            logger.warning("⚠️ yfinance XAUUSD verisi bulunamadı")
            return None
                
        except Exception as e:
            logger.error(f"❌ yfinance XAUUSD hatası: {e}")
            return None
    
    def get_usd_rub_rate(self) -> Optional[float]:
        """USD/RUB döviz kurunu çeker"""
        try:
            # Rate limiting için kısa bekleme
            import time
            time.sleep(0.5)  # 500ms bekle
            
            usd_rub = yf.Ticker(self.usd_rub_ticker)
            
            # Önce info metodunu dene
            try:
                info = usd_rub.info
                if info and 'regularMarketPrice' in info:
                    rate = info['regularMarketPrice']
                    if rate:
                        logger.info(f"✅ yfinance USD/RUB (info): {rate:.4f}")
                        return float(rate)
            except Exception as e:
                logger.warning(f"⚠️ yfinance USD/RUB info hatası: {e}")
            
            # info çalışmazsa history metodunu dene
            try:
                hist = usd_rub.history(period="1d")
                if not hist.empty:
                    rate = hist['Close'].iloc[-1]
                    logger.info(f"✅ yfinance USD/RUB (history): {rate:.4f}")
                    return float(rate)
            except Exception as e:
                logger.warning(f"⚠️ yfinance USD/RUB history hatası: {e}")
            
            logger.warning("⚠️ yfinance USD/RUB verisi bulunamadı")
            return None
                
        except Exception as e:
            logger.error(f"❌ yfinance USD/RUB hatası: {e}")
            return None
    
    def calculate_xaurub_gram_price(self) -> Optional[float]:
        """XAUUSD ve USD/RUB'den XAURUB gram fiyatını hesaplar (÷31.1034768)"""
        try:
            xauusd = self.get_xauusd_price()
            usd_rub = self.get_usd_rub_rate()
            
            if xauusd and usd_rub:
                # XAUUSD × USD/RUB ÷ 31.1034768 = Gram fiyatı
                calculated_xaurub = xauusd * usd_rub
                gram_price = calculated_xaurub / 31.1034768
                logger.info(f"✅ Hesaplanan XAURUB gram fiyatı: {gram_price:.4f} RUB/gram")
                return gram_price
            else:
                logger.warning("⚠️ XAURUB gram fiyatı hesaplanamadı - eksik veri")
                return None
                
        except Exception as e:
            logger.error(f"❌ XAURUB gram fiyatı hesaplama hatası: {e}")
            return None
    
    def calculate_xaurub_from_components(self) -> Optional[float]:
        """XAUUSD ve USD/RUB'den XAURUB hesaplar (eski metod - geriye uyumluluk için)"""
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
            
            # Güvenli info alma
            try:
                gold_info = gold.info
            except:
                gold_info = {}
                
            try:
                usd_rub_info = usd_rub.info
            except:
                usd_rub_info = {}
            
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
        gold_price = detailed['gold'].get('price', 'N/A')
        gold_change = detailed['gold'].get('change_percent', 'N/A')
        usd_rub_rate = detailed['usd_rub'].get('rate', 'N/A')
        usd_rub_change = detailed['usd_rub'].get('change_percent', 'N/A')
        
        print(f"Altın: ${gold_price} (Değişim: {gold_change}%)")
        print(f"USD/RUB: {usd_rub_rate} (Değişim: {usd_rub_change}%)")
    else:
        print(f"❌ Detaylı bilgi hatası: {detailed['error']}")
