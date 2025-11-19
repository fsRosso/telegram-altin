"""
XAUUSD son fiyatını TradingView'den çekmek için yardımcı fonksiyon.

- Kimlik bilgileri ortam değişkenlerinden okunur (TV_USERNAME / TV_PASSWORD).
- tvDatafeed bağlantısı yalnızca modül import edildiğinde kurulup tekrar
  kullanılacağı için Telegram botundaki her çağrıda ek oturum açma gecikmesi
  olmaz.
- Bu repo sürümü TradingView'e HTTP/WebSocket üzerinden bağlandığı için
  Selenium/GUI açılmaz; yani headless gereksinimi doğal olarak sağlanır.
"""

from __future__ import annotations

import os
from typing import Final

from tvDatafeed import Interval, TvDatafeed

TV_USERNAME: Final[str | None] = os.getenv("TV_USERNAME")
TV_PASSWORD: Final[str | None] = os.getenv("TV_PASSWORD")


def _build_client() -> TvDatafeed:
    """Tek seferlik TvDatafeed istemcisi kurulumunu yap."""
    if not TV_USERNAME or not TV_PASSWORD:
        raise EnvironmentError(
            "TradingView kullanıcı adı/şifresi ortam değişkenlerinde bulunamadı."
        )
    # Selenium yerine requests+websocket kullanıldığı için ekstra headless
    # ayarına gerek yok; bu çağrı tek oturumla kalır.
    return TvDatafeed(username=TV_USERNAME, password=TV_PASSWORD)


tv_client: Final[TvDatafeed] = _build_client()


def get_xauusd_price() -> float:
    """
    OANDA:XAUUSD için son kapanış fiyatını döndür.
    
    Returns:
        float: TradingView üzerinde görülen en güncel kapanış fiyatı.
    
    Raises:
        RuntimeError: Veri alınamazsa.
    """
    data = tv_client.get_hist(
        symbol="XAUUSD",
        exchange="OANDA",
        interval=Interval.in_1_minute,
        n_bars=1,
    )
    if data is None or data.empty:
        raise RuntimeError("XAUUSD fiyatı çekilemedi.")
    
    return float(data["close"].iloc[-1])


if __name__ == "__main__":
    print(get_xauusd_price())
