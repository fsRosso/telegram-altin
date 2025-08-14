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

        # Rate limiting koruması
        self.last_request_time = 0
        self.min_request_interval = 10  # 10 saniye minimum bekleme
        self.request_count = 0
        self.max_requests_per_hour = 30  # Saatte maksimum 30 istek

        # Gelişmiş header (bot tespitini zorlaştır)
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
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
        
        # Proxy sistemi (şimdilik devre dışı)
        self.proxy_list = [None]  # Sadece direkt bağlantı
        self.current_proxy_index = 0
        self.use_proxy = False  # Proxy kullanımını kapat
        
        # User-Agent rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
        ]
        self.current_ua_index = 0

    def _rotate_proxy_and_ua(self):
        """User-Agent'ı değiştir (Proxy şimdilik devre dışı)"""
        # User-Agent rotation
        self.current_ua_index = (self.current_ua_index + 1) % len(self.user_agents)
        new_ua = self.user_agents[self.current_ua_index]
        self.headers["User-Agent"] = new_ua
        
        # Proxy rotation (şimdilik devre dışı)
        if self.use_proxy and self.request_count % 5 == 0:
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
            print(f"🔄 Proxy değiştirildi: {self.current_proxy_index}")
        else:
            print(f"🔄 User-Agent değiştirildi: {self.current_ua_index}")

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
        # Rate limiting kontrolü
        import time
        current_time = time.time()
        
        # Minimum bekleme süresi kontrolü
        if current_time - self.last_request_time < self.min_request_interval:
            wait_time = self.min_request_interval - (current_time - self.last_request_time)
            print(f"⏳ Rate limiting: {wait_time:.1f} saniye bekleniyor...")
            await asyncio.sleep(wait_time)
        
        # Saatlik istek limiti kontrolü
        if self.request_count >= self.max_requests_per_hour:
            print("🚨 Saatlik istek limiti aşıldı! 1 saat bekleniyor...")
            await asyncio.sleep(3600)  # 1 saat bekle
            self.request_count = 0
        
        # Varsayılan motor ayarı
        if browser_type is None:
            browser_type = BROWSER_TYPE

        print("🚀 TABLO TABANLI FİYAT alıyorum... (", browser_type, ")")
        print("🔗", self.url)
        
        # İstek sayacını güncelle
        self.last_request_time = time.time()
        self.request_count += 1
        
        # Proxy ve User-Agent rotation
        self._rotate_proxy_and_ua()
        
        async with async_playwright() as p:
            browser = None
            try:
                # Browser başlat (fingerprinting koruması ile)
                browser_args = [
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-images",
                    "--disable-javascript",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-ipc-flooding-protection"
                ]
                
                if browser_type == "webkit":
                    browser = await p.webkit.launch(headless=True)
                elif browser_type == "firefox":
                    browser = await p.firefox.launch(headless=True)
                else:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=browser_args
                    )

                page = await browser.new_page()
                await page.set_extra_http_headers(self.headers)
                
                # Page fingerprinting koruması
                await page.add_init_script("""
                    // WebDriver özelliğini gizle
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });
                    
                    // Chrome özelliklerini gizle
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5],
                    });
                    
                    // Permissions API'yi gizle
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                """)

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
                
                # Random delay ekle (bot tespitini zorlaştır)
                import random
                random_delay = random.uniform(1.0, 3.0)
                print(f"🎲 Random delay: {random_delay:.1f} saniye")
                await asyncio.sleep(random_delay)
                
                # Tablo görünene kadar bekle (daha stabil)
                try:
                    await page.wait_for_selector("table", timeout=4000)
                except Exception:
                    pass
                await asyncio.sleep(PAGE_LOAD_WAIT)

                # Tabloları bul
                tables = await page.query_selector_all("table")
                if len(tables) < 4:
                    raise Exception("Tablo bulunamadı")

                main_table = tables[3]

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
                print("❌ Browser API hatası:", e)
                if browser is not None:
                    await browser.close()
                raise

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
