import asyncio
from datetime import datetime
from playwright.async_api import async_playwright

from config import BROWSER_TYPE, PAGE_LOAD_WAIT, CACHE_DURATION, ENABLE_PROXY
from proxy_manager import ProxyManager


class FastPriceFetcher:
    def __init__(self) -> None:
        # Tablo tabanlı sayfa (Last sütunu burada)
        self.url = "https://www.profinance.ru/charts/goldgrrub/la07h"

        # Dinamik analiz için bellek
        self.last_known_price: float | None = None
        self.price_history: list[float] = []
        self.max_history_size: int = 10

        # ✅ Rate limiting tamamen kaldırıldı - bot sadece kullanıcı istediğinde çalışıyor
        
        # Proxy sistemi
        self.proxy_manager = ProxyManager() if ENABLE_PROXY else None
        self.current_proxy = None
        
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
        
        # User-Agent rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
        ]
        self.current_ua_index = 0
        
        # 30 saniyelik akıllı cache sistemi (3 saniye çok kısa)
        self.cache = {
            "price": None,
            "timestamp": 0,
            "cache_duration": CACHE_DURATION  # Config'den al
        }

    def _rotate_proxy_and_ua(self):
        """User-Agent ve Proxy rotation"""
        # User-Agent rotation
        self.current_ua_index = (self.current_ua_index + 1) % len(self.user_agents)
        new_ua = self.user_agents[self.current_ua_index]
        self.headers["User-Agent"] = new_ua
        
        # Proxy rotation (eğer proxy sistemi aktifse)
        if self.proxy_manager and self.proxy_manager.working_proxies:
            self.current_proxy = self.proxy_manager.get_next_proxy()
            print(f"🔄 Proxy değiştirildi: {self.current_proxy['proxy']}")
        else:
            print(f"🔄 User-Agent değiştirildi: {self.current_ua_index}")
    
    def _is_cache_valid(self) -> bool:
        """Cache'in geçerli olup olmadığını kontrol et"""
        import time
        current_time = time.time()
        
        if self.cache["price"] is None:
            return False
            
        time_diff = current_time - self.cache["timestamp"]
        return time_diff < self.cache["cache_duration"]
    
    def _update_cache(self, price: float):
        """Cache'i güncelle"""
        import time
        self.cache["price"] = price
        self.cache["timestamp"] = time.time()
        print(f"💾 Cache güncellendi: {price:.4f} RUB ({CACHE_DURATION}s TTL)")

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
        # ✅ RATE LIMITING TAMAMEN KALDIRILDI!
        
        # Cache kontrolü - 3 saniye içinde tekrar istek varsa cache'den ver
        if self._is_cache_valid():
            print(f"💾 Cache'den veri alınıyor: {self.cache['price']:.4f} RUB")
            print(f"⏱️ Cache yaşı: {time.time() - self.cache['timestamp']:.1f} saniye")
            return self.cache["price"]
        
        # Varsayılan motor ayarı
        if browser_type is None:
            browser_type = BROWSER_TYPE

        print("🚀 TABLO TABANLI FİYAT alıyorum... (", browser_type, ")")
        print("🔗", self.url)
        
        # Proxy ve User-Agent rotation (her istekte)
        self._rotate_proxy_and_ua()
        
        # Proxy durumunu göster
        if self.current_proxy:
            print(f"🌐 Aktif Proxy: {self.current_proxy['proxy']}")
        else:
            print("ℹ️ Proxy kullanılmıyor")
        
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
                    # Chromium için proxy ayarları
                    browser_args = browser_args.copy()
                    if self.current_proxy:
                        proxy_server = f"{self.current_proxy['ip']}:{self.current_proxy['port']}"
                        browser_args.extend([f"--proxy-server={proxy_server}"])
                        print(f"🌐 ProFinance için Proxy kullanılıyor: {proxy_server}")
                    else:
                        print("ℹ️ ProFinance için proxy kullanılmıyor")
                    
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

                # Tabloları bul - sayfa yapısı değişse de çalışacak şekilde tüm tabloları tara
                tables = await page.query_selector_all("table")
                print(f"📊 Sayfada {len(tables)} tablo bulundu")
                if not tables:
                    raise Exception("Tablo bulunamadı")

                # Tüm tabloları tara, sayısal fiyat içeren hücreyi ara (XAURUB ~50-10000 arası)
                main_table = None
                bid = ask = last = time_txt = ""
                cells = []

                for i, tbl in enumerate(tables):
                    rows = await tbl.query_selector_all("tr")
                    for row in rows:
                        tds = await row.query_selector_all("td")
                        if len(tds) < 3:
                            continue
                        texts = [(await td.inner_text()).strip() for td in tds]
                        for j, txt in enumerate(texts[:4]):
                            try:
                                val = float(txt.replace(",", ".").replace(" ", ""))
                                if 50 < val < 10000:
                                    main_table = tbl
                                    bid = texts[0] if len(texts) > 0 else ""
                                    ask = texts[1] if len(texts) > 1 else ""
                                    last = texts[j]
                                    time_txt = texts[j + 1] if len(texts) > j + 1 else ""
                                    cells = tds
                                    print(f"✅ Fiyat tablosu bulundu: tablo #{i}, hücre #{j}, değer={val}")
                                    break
                            except ValueError:
                                continue
                        if main_table:
                            break
                    if main_table:
                        break

                if not main_table or not last:
                    raise Exception("Tablo bulunamadı")

                # Başlıklar (log için)
                headers = await main_table.query_selector_all("tr:first-child td")
                header_texts = [
                    (await h.inner_text()).strip() for h in headers
                ] if headers else []
                print("📋 Tablo başlıkları:", header_texts)

                last_price = float(last.strip().replace(",", ".").replace(" ", "")) if last and last.strip() else None
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

                # Cache'i güncelle
                self._update_cache(last_price)

                await browser.close()
                return last_price
            except Exception as e:
                print("❌ Browser API hatası:", e)
                if browser is not None:
                    await browser.close()
                raise

    async def get_price_plus_increment_async(self, increment: float = 0.01) -> dict:
        try:
            # ✅ CACHE KONTROLÜ BURADA YAPILIYOR!
            # 3 saniye içinde tekrar istek varsa cache'den ver
            if self._is_cache_valid():
                print(f"💾 Cache'den veri alınıyor: {self.cache['price']:.4f} RUB")
                print(f"⏱️ Cache yaşı: {time.time() - self.cache['timestamp']:.1f} saniye")
                current_price = self.cache["price"]
            else:
                # Cache geçersizse yeni veri çek
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

    async def initialize_proxy_manager(self):
        """
        Proxy manager'ı başlatır ve proxy listesini günceller
        """
        if not self.proxy_manager:
            return
        
        try:
            print("🔄 Proxy sistemi başlatılıyor...")
            
            # Proxy listesini güncelle
            success = await self.proxy_manager.update_proxy_list()
            if not success:
                print("⚠️ Proxy listesi güncellenemedi, proxy olmadan devam ediliyor")
                return
            
            # Proxy'leri test et
            working_count = await self.proxy_manager.test_proxies(max_proxies=50)
            
            if working_count > 0:
                print(f"✅ {working_count} çalışan proxy bulundu")
                # İlk proxy'yi seç
                self.current_proxy = self.proxy_manager.get_next_proxy()
                print(f"🌐 Aktif proxy: {self.current_proxy['proxy']}")
            else:
                print("⚠️ Çalışan proxy bulunamadı, proxy olmadan devam ediliyor")
                
        except Exception as e:
            print(f"❌ Proxy manager başlatma hatası: {e}")
            print("⚠️ Proxy olmadan devam ediliyor")


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
