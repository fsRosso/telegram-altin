import asyncio
import aiohttp
import time
import random
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger(__name__)

class ProxyManager:
    """
    Otomatik proxy yönetim sistemi
    - GitHub'dan proxy listelerini otomatik günceller
    - Proxy'leri test eder ve çalışanları filtreler
    - Otomatik rotation yapar
    - Proxy performansını izler
    """
    
    def __init__(self):
        # Proxy listesi kaynakları (GitHub)
        self.proxy_sources = [
            'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
            'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt',
            'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
            'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies.txt',
            'https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt'
        ]
        
        # Proxy verileri
        self.proxies: List[Dict] = []
        self.working_proxies: List[Dict] = []
        self.current_proxy_index = 0
        
        # Cache ve güncelleme ayarları
        self.cache_file = "proxy_cache.json"
        self.last_update = None
        self.update_interval = timedelta(hours=6)  # 6 saatte bir güncelle
        
        # Test ayarları
        self.test_url = "http://httpbin.org/ip"  # IP test URL'i
        self.test_timeout = 10  # Test timeout süresi
        self.max_concurrent_tests = 50  # Maksimum eşzamanlı test
        
        # Performans izleme
        self.proxy_stats = {}
        
        # Logging
        logging.basicConfig(level=logging.INFO)
        
    async def update_proxy_list(self, force_update: bool = False) -> bool:
        """
        Proxy listesini günceller
        """
        try:
            # Cache kontrolü
            if not force_update and self._should_use_cache():
                if self._load_from_cache():
                    logger.info(f"✅ Cache'den {len(self.proxies)} proxy yüklendi")
                    return True
            
            logger.info("🔄 Proxy listesi güncelleniyor...")
            
            # Tüm kaynaklardan proxy'leri topla
            all_proxies = set()
            
            for source in self.proxy_sources:
                try:
                    proxies = await self._fetch_proxies_from_source(source)
                    all_proxies.update(proxies)
                    logger.info(f"📡 {source}: {len(proxies)} proxy bulundu")
                except Exception as e:
                    logger.warning(f"⚠️ {source} hatası: {e}")
            
            # Proxy'leri parse et
            self.proxies = []
            for proxy_str in all_proxies:
                proxy = self._parse_proxy(proxy_str)
                if proxy:
                    self.proxies.append(proxy)
            
            logger.info(f"📊 Toplam {len(self.proxies)} proxy bulundu")
            
            # Cache'e kaydet
            self._save_to_cache()
            self.last_update = datetime.now()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Proxy listesi güncelleme hatası: {e}")
            return False
    
    async def _fetch_proxies_from_source(self, url: str) -> set:
        """
        Tek bir kaynaktan proxy listesi çeker
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    content = await response.text()
                    # Satır satır parse et
                    proxies = set()
                    for line in content.strip().split('\n'):
                        line = line.strip()
                        if line and ':' in line and not line.startswith('#'):
                            proxies.add(line)
                    return proxies
                else:
                    raise Exception(f"HTTP {response.status}")
    
    def _parse_proxy(self, proxy_str: str) -> Optional[Dict]:
        """
        Proxy string'ini parse eder
        """
        try:
            if ':' not in proxy_str:
                return None
            
            parts = proxy_str.split(':')
            if len(parts) != 2:
                return None
            
            ip, port = parts[0], parts[1]
            
            # IP formatını kontrol et
            if not self._is_valid_ip(ip):
                return None
            
            # Port formatını kontrol et
            try:
                port_num = int(port)
                if port_num < 1 or port_num > 65535:
                    return None
            except ValueError:
                return None
            
            return {
                'ip': ip,
                'port': port_num,
                'proxy': f"http://{ip}:{port}",
                'working': False,
                'last_tested': None,
                'response_time': None,
                'success_count': 0,
                'fail_count': 0
            }
            
        except Exception:
            return None
    
    def _is_valid_ip(self, ip: str) -> bool:
        """
        IP adresinin geçerli olup olmadığını kontrol eder
        """
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            
            for part in parts:
                if not part.isdigit():
                    return False
                num = int(part)
                if num < 0 or num > 255:
                    return False
            
            return True
        except:
            return False
    
    async def test_proxies(self, max_proxies: int = 100) -> int:
        """
        Proxy'leri test eder ve çalışanları filtreler
        """
        if not self.proxies:
            logger.warning("⚠️ Test edilecek proxy yok!")
            return 0
        
        logger.info(f"🧪 {min(len(self.proxies), max_proxies)} proxy test ediliyor...")
        
        # Test edilecek proxy'leri seç
        test_proxies = self.proxies[:max_proxies]
        
        # Eşzamanlı test
        semaphore = asyncio.Semaphore(self.max_concurrent_tests)
        
        async def test_single_proxy(proxy):
            async with semaphore:
                return await self._test_single_proxy(proxy)
        
        # Tüm proxy'leri test et
        tasks = [test_single_proxy(proxy) for proxy in test_proxies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Sonuçları işle
        working_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.debug(f"❌ {test_proxies[i]['proxy']} test hatası: {result}")
                test_proxies[i]['working'] = False
                test_proxies[i]['fail_count'] += 1
            elif result:
                test_proxies[i]['working'] = True
                test_proxies[i]['success_count'] += 1
                working_count += 1
        
        # Çalışan proxy'leri filtrele
        self.working_proxies = [p for p in test_proxies if p['working']]
        
        logger.info(f"✅ {working_count}/{len(test_proxies)} proxy çalışıyor")
        
        # Cache'e kaydet
        self._save_to_cache()
        
        return working_count
    
    async def _test_single_proxy(self, proxy: Dict) -> bool:
        """
        Tek bir proxy'yi test eder
        """
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.test_url,
                    proxy=proxy['proxy'],
                    timeout=aiohttp.ClientTimeout(total=self.test_timeout)
                ) as response:
                    if response.status == 200:
                        elapsed = time.time() - start_time
                        proxy['response_time'] = elapsed
                        proxy['last_tested'] = datetime.now()
                        return True
                    else:
                        return False
                        
        except Exception:
            proxy['last_tested'] = datetime.now()
            return False
    
    def get_next_proxy(self) -> Optional[Dict]:
        """
        Sıradaki çalışan proxy'yi döner
        """
        if not self.working_proxies:
            return None
        
        # Round-robin rotation
        proxy = self.working_proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.working_proxies)
        
        return proxy
    
    def get_random_proxy(self) -> Optional[Dict]:
        """
        Rastgele çalışan proxy döner
        """
        if not self.working_proxies:
            return None
        
        return random.choice(self.working_proxies)
    
    def get_fastest_proxy(self) -> Optional[Dict]:
        """
        En hızlı proxy'yi döner
        """
        if not self.working_proxies:
            return None
        
        # Response time'a göre sırala
        sorted_proxies = sorted(
            [p for p in self.working_proxies if p['response_time'] is not None],
            key=lambda x: x['response_time']
        )
        
        return sorted_proxies[0] if sorted_proxies else None
    
    def _should_use_cache(self) -> bool:
        """
        Cache kullanılıp kullanılmayacağını kontrol eder
        """
        if not self.last_update:
            return False
        
        return datetime.now() - self.last_update < self.update_interval
    
    def _save_to_cache(self):
        """
        Proxy listesini cache'e kaydeder
        """
        try:
            # Proxy verilerini kopyala ve datetime'ları temizle
            proxies_copy = []
            for proxy in self.proxies:
                proxy_copy = proxy.copy()
                if proxy_copy.get('last_tested'):
                    proxy_copy['last_tested'] = proxy_copy['last_tested'].isoformat()
                proxies_copy.append(proxy_copy)
            
            working_proxies_copy = []
            for proxy in self.working_proxies:
                proxy_copy = proxy.copy()
                if proxy_copy.get('last_tested'):
                    proxy_copy['last_tested'] = proxy_copy['last_tested'].isoformat()
                working_proxies_copy.append(proxy_copy)
            
            cache_data = {
                'proxies': proxies_copy,
                'working_proxies': working_proxies_copy,
                'last_update': self.last_update.isoformat() if self.last_update else None
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
            logger.info("💾 Proxy listesi cache'e kaydedildi")
            
        except Exception as e:
            logger.error(f"❌ Cache kaydetme hatası: {e}")
    
    def _load_from_cache(self) -> bool:
        """
        Proxy listesini cache'den yükler
        """
        try:
            if not os.path.exists(self.cache_file):
                return False
            
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            self.proxies = cache_data.get('proxies', [])
            self.working_proxies = cache_data.get('working_proxies', [])
            
            if cache_data.get('last_update'):
                self.last_update = datetime.fromisoformat(cache_data['last_update'])
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Cache yükleme hatası: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """
        Proxy istatistiklerini döner
        """
        total_proxies = len(self.proxies)
        working_proxies = len(self.working_proxies)
        
        if total_proxies == 0:
            return {
                'total': 0,
                'working': 0,
                'working_percentage': 0,
                'last_update': self.last_update.isoformat() if self.last_update else None
            }
        
        working_percentage = (working_proxies / total_proxies) * 100
        
        # Ortalama response time
        avg_response_time = None
        if working_proxies > 0:
            response_times = [p['response_time'] for p in self.working_proxies if p['response_time'] is not None]
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
        
        return {
            'total': total_proxies,
            'working': working_proxies,
            'working_percentage': round(working_percentage, 2),
            'avg_response_time': round(avg_response_time, 3) if avg_response_time else None,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }
    
    def cleanup(self):
        """
        Temizlik işlemleri
        """
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
                logger.info("🗑️ Cache dosyası temizlendi")
        except Exception as e:
            logger.error(f"❌ Temizlik hatası: {e}")

# Test fonksiyonu
async def test_proxy_manager():
    """
    Proxy manager'ı test eder
    """
    manager = ProxyManager()
    
    try:
        print("🚀 Proxy Manager test ediliyor...")
        
        # Proxy listesini güncelle
        success = await manager.update_proxy_list()
        if not success:
            print("❌ Proxy listesi güncellenemedi!")
            return
        
        # Proxy'leri test et
        working_count = await manager.test_proxies(max_proxies=50)
        
        # İstatistikleri göster
        stats = manager.get_stats()
        print(f"\n📊 Proxy İstatistikleri:")
        print(f"   Toplam: {stats['total']}")
        print(f"   Çalışan: {stats['working']}")
        print(f"   Başarı Oranı: %{stats['working_percentage']}")
        print(f"   Ortalama Response Time: {stats['avg_response_time']}s")
        
        # Örnek proxy'ler
        if manager.working_proxies:
            print(f"\n✅ Çalışan Proxy Örnekleri:")
            for i, proxy in enumerate(manager.working_proxies[:5]):
                print(f"   {i+1}. {proxy['proxy']} (Response: {proxy['response_time']:.3f}s)")
        
        # En hızlı proxy
        fastest = manager.get_fastest_proxy()
        if fastest:
            print(f"\n🏃 En Hızlı Proxy: {fastest['proxy']} ({fastest['response_time']:.3f}s)")
        
    except Exception as e:
        print(f"❌ Test hatası: {e}")
    finally:
        manager.cleanup()

if __name__ == "__main__":
    asyncio.run(test_proxy_manager())
