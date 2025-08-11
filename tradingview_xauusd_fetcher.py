import asyncio
import json
import websockets
import time
from datetime import datetime
from typing import Optional, Dict, Any
import logging

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingViewXAUUSDFetcher:
    """
    TradingView'dan XAUUSD OANDA fiyatını WebSocket ile çeken sınıf
    """
    
    def __init__(self):
        # TradingView WebSocket endpoint'leri
        self.ws_url = "wss://data.tradingview.com/socket.io/websocket"
        self.ws_public_url = "wss://prodata.tradingview.com/socket.io/websocket"
        
        # XAUUSD OANDA sembol bilgileri
        self.symbol = "OANDA:XAUUSD"
        self.symbol_id = None
        
        # WebSocket bağlantı durumu
        self.websocket = None
        self.is_connected = False
        self.is_authenticated = False
        
        # Fiyat verileri
        self.current_price: Optional[float] = None
        self.last_update: Optional[datetime] = None
        self.price_history: list[Dict[str, Any]] = []
        self.max_history_size = 100
        
        # Bağlantı parametreleri
        self.session_id = None
        self.auth_token = None
        
    async def connect(self) -> bool:
        """
        TradingView WebSocket'e bağlan
        """
        try:
            logger.info("🔌 TradingView WebSocket'e bağlanılıyor...")
            
            # WebSocket bağlantısı
            self.websocket = await websockets.connect(
                self.ws_url,
                extra_headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            
            self.is_connected = True
            logger.info("✅ WebSocket bağlantısı başarılı")
            
            # Handshake ve authentication
            await self._perform_handshake()
            await self._authenticate()
            await self._subscribe_to_symbol()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ WebSocket bağlantı hatası: {e}")
            self.is_connected = False
            return False
    
    async def _perform_handshake(self):
        """
        TradingView ile handshake yap
        """
        try:
            # Handshake mesajı
            handshake_msg = {
                "method": "set_auth_token",
                "params": [""],
                "id": 1
            }
            
            await self.websocket.send(json.dumps(handshake_msg))
            logger.info("🤝 Handshake gönderildi")
            
        except Exception as e:
            logger.error(f"❌ Handshake hatası: {e}")
    
    async def _authenticate(self):
        """
        Anonim authentication
        """
        try:
            # Anonim auth mesajı
            auth_msg = {
                "method": "set_auth_token",
                "params": [""],
                "id": 2
            }
            
            await self.websocket.send(json.dumps(auth_msg))
            logger.info("🔐 Anonim authentication gönderildi")
            
        except Exception as e:
            logger.error(f"❌ Authentication hatası: {e}")
    
    async def _subscribe_to_symbol(self):
        """
        XAUUSD OANDA sembolüne abone ol
        """
        try:
            # Sembol aboneliği
            subscribe_msg = {
                "method": "resolve_symbol",
                "params": [
                    "sds_sym_1",
                    "={\"symbol\":\"" + self.symbol + "\",\"adjustment\":\"splits\",\"session\":\"extended\"}"
                ],
                "id": 3
            }
            
            await self.websocket.send(json.dumps(subscribe_msg))
            logger.info(f"📊 {self.symbol} sembolüne abone olundu")
            
            # Fiyat stream aboneliği
            price_subscribe_msg = {
                "method": "quote_create_session",
                "params": ["qs_1"],
                "id": 4
            }
            
            await self.websocket.send(json.dumps(price_subscribe_msg))
            logger.info("💰 Fiyat stream aboneliği oluşturuldu")
            
        except Exception as e:
            logger.error(f"❌ Sembol abonelik hatası: {e}")
    
    async def listen_for_prices(self):
        """
        WebSocket'ten gelen fiyat verilerini dinle
        """
        if not self.is_connected or not self.websocket:
            logger.error("❌ WebSocket bağlı değil")
            return
        
        try:
            logger.info("👂 Fiyat verileri dinleniyor...")
            
            async for message in self.websocket:
                try:
                    # Mesajı parse et
                    data = json.loads(message)
                    await self._process_message(data)
                    
                except json.JSONDecodeError:
                    # Binary mesaj olabilir, atla
                    continue
                except Exception as e:
                    logger.error(f"❌ Mesaj işleme hatası: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("⚠️ WebSocket bağlantısı kapandı")
            self.is_connected = False
        except Exception as e:
            logger.error(f"❌ Dinleme hatası: {e}")
            self.is_connected = False
    
    async def _process_message(self, data: Dict[str, Any]):
        """
        Gelen mesajı işle ve fiyatı çıkar
        """
        try:
            # Fiyat verisi kontrolü
            if "p" in data and "s" in data:
                symbol = data.get("s", "")
                price = data.get("p", 0)
                
                if symbol == self.symbol or "XAUUSD" in str(symbol):
                    await self._update_price(price)
                    
        except Exception as e:
            logger.error(f"❌ Mesaj işleme hatası: {e}")
    
    async def _update_price(self, price: float):
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
                "change": old_price - price if old_price else 0
            }
            
            self.price_history.append(price_data)
            if len(self.price_history) > self.max_history_size:
                self.price_history.pop(0)
            
            logger.info(f"💰 XAUUSD OANDA: ${price:.2f} (Güncelleme: {self.last_update.strftime('%H:%M:%S')})")
            
        except Exception as e:
            logger.error(f"❌ Fiyat güncelleme hatası: {e}")
    
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
            "is_connected": self.is_connected,
            "price_history_count": len(self.price_history),
            "symbol": self.symbol
        }
    
    async def disconnect(self):
        """
        WebSocket bağlantısını kapat
        """
        try:
            if self.websocket:
                await self.websocket.close()
                self.is_connected = False
                logger.info("🔌 WebSocket bağlantısı kapatıldı")
        except Exception as e:
            logger.error(f"❌ Bağlantı kapatma hatası: {e}")
    
    async def start_price_monitoring(self):
        """
        Fiyat izlemeyi başlat
        """
        try:
            # Bağlan
            if await self.connect():
                # Fiyat dinlemeyi başlat
                await self.listen_for_prices()
            else:
                logger.error("❌ Bağlantı kurulamadı")
                
        except Exception as e:
            logger.error(f"❌ Fiyat izleme hatası: {e}")
        finally:
            await self.disconnect()

# Test fonksiyonu
async def test_tradingview_fetcher():
    """
    TradingView fetcher'ı test et
    """
    fetcher = TradingViewXAUUSDFetcher()
    
    try:
        logger.info("🧪 TradingView XAUUSD Fetcher test ediliyor...")
        
        # 30 saniye boyunca fiyat izle
        await asyncio.wait_for(
            fetcher.start_price_monitoring(),
            timeout=30.0
        )
        
    except asyncio.TimeoutError:
        logger.info("⏰ Test süresi doldu")
    except Exception as e:
        logger.error(f"❌ Test hatası: {e}")
    finally:
        await fetcher.disconnect()

if __name__ == "__main__":
    # Test çalıştır
    asyncio.run(test_tradingview_fetcher())
