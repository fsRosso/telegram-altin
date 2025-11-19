"""
TradingView XAUUSD fiyatını tvDatafeed üzerinden hızlıca almak için yardımcı fonksiyonlar.

- Giriş kimlik bilgileri ortam değişkenlerinden okunur (`TV_USERNAME`, `TV_PASSWORD`).
- Bağlantı modül importunda kurulmaya çalışılır; başarılı olursa her çağrıda tekrar login olmaz.
- tvDatafeed requests+websocket kullandığı için Selenium/GUI açılmaz; Railway gibi headless
  ortamlarda ekstra konfig gerektirmez.
"""

from __future__ import annotations

import os
from typing import Final, Optional

from tvDatafeed import Interval, TvDatafeed

TV_USERNAME: Final[Optional[str]] = os.getenv("TV_USERNAME")
TV_PASSWORD: Final[Optional[str]] = os.getenv("TV_PASSWORD")


def _build_client() -> TvDatafeed:
    if not TV_USERNAME or not TV_PASSWORD:
        raise EnvironmentError(
            "TradingView kullanıcı adı/şifresi ortam değişkenlerinde bulunamadı."
        )
    return TvDatafeed(username=TV_USERNAME, password=TV_PASSWORD)


try:
    _TV_CLIENT: Final[Optional[TvDatafeed]] = _build_client()
    _TV_CLIENT_ERROR: Final[Optional[Exception]] = None
except Exception as exc:  # pragma: no cover - çevreye bağlı durum
    _TV_CLIENT = None
    _TV_CLIENT_ERROR = exc


def is_tv_client_ready() -> bool:
    """tvDatafeed istemcisi hazır mı?"""
    return _TV_CLIENT is not None


def get_xauusd_price() -> float:
    """
    OANDA:XAUUSD için son kapanış fiyatını döndür.

    Raises:
        RuntimeError: Veri alınamazsa veya istemci yoksa.
    """

    if _TV_CLIENT is None:
        msg = (
            "tvDatafeed istemcisi hazır değil."
            if _TV_CLIENT_ERROR is None
            else f"tvDatafeed istemcisi kurulamadı: {_TV_CLIENT_ERROR}"
        )
        raise RuntimeError(msg)

    data = _TV_CLIENT.get_hist(
        symbol="XAUUSD",
        exchange="OANDA",
        interval=Interval.in_1_minute,
        n_bars=1,
    )

    if data is None or data.empty:
        raise RuntimeError("XAUUSD fiyatı çekilemedi.")

    return float(data["close"].iloc[-1])


if __name__ == "__main__":  # Manuel test
    print(get_xauusd_price())

