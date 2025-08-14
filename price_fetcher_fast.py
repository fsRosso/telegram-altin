import asyncio
from datetime import datetime
from playwright.async_api import async_playwright

from config import BROWSER_TYPE, PAGE_LOAD_WAIT


class FastPriceFetcher:
    def __init__(self) -> None:
        # Tablo tabanlı sayfa (Last sütunu burada)
        self.url = "https://www.profinance.ru/charts/goldgrrub/la07h"

        # Dinamik analiz için bellek
        self.last_known_price: float | None = None
        self.price_history: list[float] = []
        self.max_history_size: int = 10

        # Basit header
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }

    def analyze_price_change(self, new_price: float) -> dict:
        if self.last_known_price is None:
            self.last_known_price = new_price
            self.price_history.append(new_price)
            return {
                "is_first_price": True,
                "change_percent": 0.0,
                "change_amount": 0.0,
                "is_abnormal": False,
                "is_warning": False,
                "message": "📊 İlk fiyat alındı",
            }

        change_amount = new_price - self.last_known_price
        change_percent = (change_amount / self.last_known_price) * 100

        self.price_history.append(new_price)
        if len(self.price_history) > self.max_history_size:
            self.price_history.pop(0)

        is_abnormal = False
        is_warning = False
        message = f"📊 Normal değişim: {change_percent:.2f}%"

        # Uyarı eşiği: %0.5
        if abs(change_percent) > 0.5:
            is_warning = True
            if change_percent > 0:
                message = f"⚠️ UYARI: Fiyat %{change_percent:.2f} arttı! ({change_amount:.2f} RUB)"
            else:
                message = f"⚠️ UYARI: Fiyat %{abs(change_percent):.2f} düştü! ({abs(change_amount):.2f} RUB)"

        # Kritik eşikler
        if abs(change_percent) > 10:
            is_abnormal = True
            message = f"🚨 KRİTİK: BÜYÜK DEĞİŞİM %{change_percent:.2f}! ({change_amount:.2f} RUB)"
        elif change_percent < -5:
            is_abnormal = True
            message = f"📉 ANİ DÜŞÜŞ: %{abs(change_percent):.2f} ({abs(change_amount):.2f} RUB)"
        elif change_percent > 5:
            is_abnormal = True
            message = f"📈 ANİ YÜKSELİŞ: %{change_percent:.2f} ({change_amount:.2f} RUB)"

        self.last_known_price = new_price

        return {
            "is_first_price": False,
            "change_percent": change_percent,
            "change_amount": change_amount,
            "is_abnormal": is_abnormal,
            "is_warning": is_warning,
            "message": message,
            "price_history": self.price_history.copy(),
        }

    async def get_current_price(self, browser_type: str = None) -> float:
        # Varsayılan motor ayarı
        if browser_type is None:
            browser_type = BROWSER_TYPE

        print("🚀 TABLO TABANLI FİYAT alıyorum... (", browser_type, ")")
        print("🔗", self.url)

        async with async_playwright() as p:
            browser = None
            try:
                # Browser başlat
                if browser_type == "webkit":
                    browser = await p.webkit.launch(headless=True)
                elif browser_type == "firefox":
                    browser = await p.firefox.launch(headless=True)
                else:
                    browser = await p.chromium.launch(headless=True)

                page = await browser.new_page()
                await page.set_extra_http_headers(self.headers)

                # Ağ optimizasyonu: ağır kaynakları engelle
                async def _route_filter(route, request):
                    try:
                        if request.resource_type in ["image", "stylesheet", "font", "media", "other"]:
                            await route.abort()
                        else:
                            await route.continue_()
                    except Exception:
                        try:
                            await route.continue_()
                        except Exception:
                            pass
                await page.route("**/*", _route_filter)

                print("🔗 Sayfaya gidiyorum...")
                await page.goto(self.url, wait_until="domcontentloaded", timeout=8000)
                # Tablo görünene kadar bekle (daha stabil)
                try:
                    await page.wait_for_selector("table", timeout=4000)
                except Exception:
                    pass
                await asyncio.sleep(PAGE_LOAD_WAIT)

                # Tabloları bul
                tables = await page.query_selector_all("table")
                print(f"📊 Bulunan tablo sayısı: {len(tables)}")
                
                if len(tables) == 0:
                    raise Exception("Hiç tablo bulunamadı")
                
                # Tablo sayısına göre dinamik seçim
                if len(tables) >= 4:
                    main_table = tables[3]  # Eski mantık
                elif len(tables) >= 3:
                    main_table = tables[2]  # 3 tablo varsa
                elif len(tables) >= 2:
                    main_table = tables[1]  # 2 tablo varsa
                else:
                    main_table = tables[0]  # Tek tablo varsa
                
                print(f"🎯 Seçilen tablo indeksi: {tables.index(main_table)}")

                # Başlıklar
                headers = await main_table.query_selector_all("tr:first-child td")
                header_texts = [
                    (await h.inner_text()).strip() for h in headers
                ] if headers else []
                print("📋 Tablo başlıkları:", header_texts)

                # Veri satırları
                data_rows = await main_table.query_selector_all("tr:not(:first-child)")
                if not data_rows:
                    raise Exception("Veri satırları bulunamadı")

                # İlk satır
                first_data_row = data_rows[0]
                cells = await first_data_row.query_selector_all("td")
                if len(cells) < 3:
                    raise Exception("Yetersiz hücre")

                bid = await cells[0].inner_text()
                ask = await cells[1].inner_text()
                last = await cells[2].inner_text()
                time_txt = await cells[3].inner_text() if len(cells) > 3 else ""

                if not last or not last.strip():
                    print("⚠️ Last değeri boş, bir sonraki satırı kontrol ediyorum...")
                    if len(data_rows) > 1:
                        next_cells = await data_rows[1].query_selector_all("td")
                        if len(next_cells) >= 3:
                            last = await next_cells[2].inner_text()
                            time_txt = await next_cells[3].inner_text() if len(next_cells) > 3 else ""

                last_price = float(last.strip()) if last and last.strip() else None
                if not last_price or last_price <= 0:
                    raise Exception("Geçersiz fiyat")

                print("✅ Fiyat başarıyla çekildi!")
                print("   Bid:", bid)
                print("   Ask:", ask)
                print("   Last:", last_price)
                print("   Zaman:", time_txt.strip())

                # Analiz bilgisi (log)
                analysis = self.analyze_price_change(last_price)
                print("📊", analysis["message"])

                await browser.close()
                return last_price
            except Exception as e:
                print(f"❌ Browser API hatası: {e}")
                print(f"🔗 URL: {self.url}")
                print(f"📊 Tablo sayısı: {len(tables) if 'tables' in locals() else 'Bilinmiyor'}")
                if browser is not None:
                    await browser.close()
                raise Exception(f"Tablo bulunamadı: {e}")

    async def get_price_plus_increment_async(self, increment: float = 0.01) -> dict:
        try:
            current_price = await self.get_current_price(BROWSER_TYPE)
            if not current_price:
                raise Exception("Mevcut fiyat alınamadı")

            percentage_increase = increment / 100.0
            new_price = current_price * (1 + percentage_increase)
            
            return {
                "current_price": current_price,
                "increment": increment,
                "new_price": new_price,
                "increase_amount": new_price - current_price,
                "percentage_increase": new_price - current_price,
            }
        except Exception as e:
            print("❌ Fiyat hesaplama hatası:", e)
            raise


if __name__ == "__main__":
    fetcher = FastPriceFetcher()
    try:
        start = datetime.now()
        result = asyncio.run(fetcher.get_price_plus_increment_async(0.01))
        dur = (datetime.now() - start).total_seconds()
        print("\n✅ HIZLI SİSTEM SONUÇ:")
        print(f"⏱️ Süre: {dur:.2f} saniye")
        print(f"📊 Mevcut fiyat: {result['current_price']}")
        print(f"📈 Yeni fiyat (+{result['increment']}%): {result['new_price']}")
    except Exception as e:
        print("❌ Hata:", e)
