#!/usr/bin/env python3
"""
Enhanced Proxy Manager - Gelişmiş proxy yönetimi
"""

import asyncio
import aiohttp
import random
import logging
from typing import List, Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class EnhancedProxyManager:
    def __init__(self):
        self.proxies: List[Dict[str, str]] = []
        self.working_proxies: List[Dict[str, str]] = []
        self.failed_proxies: List[Dict[str, str]] = []
        self.last_update = None
        self.update_interval = timedelta(hours=6)  # 6 saatte bir güncelle
        
    async def load_proxies(self) -> List[Dict[str, str]]:
        """Proxy listesini yükle (çeşitli kaynaklardan)"""
        proxies = []
        
        # Ücretsiz proxy kaynakları
        proxy_sources = [
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
            "https://raw.githubusercontent.com/mertguvencli/http-proxy-list/main/proxy-list/data.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
            "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt"
        ]
        
        for source in proxy_sources:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(source, timeout=15) as response:
                        if response.status == 200:
                            text = await response.text()
                            for line in text.strip().split('\n'):
                                line = line.strip()
                                if ':' in line and not line.startswith('#') and not line.startswith('//'):
                                    try:
                                        ip, port = line.split(':')
                                        # Port'un sayı olduğunu kontrol et
                                        int(port)
                                        proxies.append({
                                            'http': f'http://{ip}:{port}',
                                            'https': f'http://{ip}:{port}'
                                        })
                                    except ValueError:
                                        continue
            except Exception as e:
                logger.warning(f"Proxy kaynağı yüklenemedi {source}: {e}")
        
        logger.info(f"📡 {len(proxies)} proxy yüklendi")
        return proxies
    
    async def test_proxy(self, proxy: Dict[str, str]) -> bool:
        """Proxy'yi test et"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'http://httpbin.org/ip',
                    proxy=proxy['http'],
                    timeout=8
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'origin' in data:
                            logger.debug(f"✅ Proxy çalışıyor: {data['origin']}")
                            return True
        except Exception as e:
            logger.debug(f"❌ Proxy test hatası: {e}")
        return False
    
    async def update_proxy_list(self):
        """Proxy listesini güncelle"""
        if (self.last_update and 
            datetime.now() - self.last_update < self.update_interval):
            return
        
        logger.info("🔄 Proxy listesi güncelleniyor...")
        
        # Yeni proxy'leri yükle
        new_proxies = await self.load_proxies()
        
        # Çalışan proxy'leri test et
        working = []
        test_count = min(100, len(new_proxies))  # İlk 100'ü test et
        
        logger.info(f"🔍 {test_count} proxy test ediliyor...")
        
        for i, proxy in enumerate(new_proxies[:test_count]):
            if await self.test_proxy(proxy):
                working.append(proxy)
                logger.info(f"✅ Çalışan proxy {len(working)}: {proxy['http']}")
                if len(working) >= 20:  # 20 çalışan proxy yeter
                    break
            
            # Her 10 testte bir ilerleme göster
            if (i + 1) % 10 == 0:
                logger.info(f"📊 Test edilen: {i+1}/{test_count}, Çalışan: {len(working)}")
        
        self.working_proxies = working
        self.last_update = datetime.now()
        
        logger.info(f"✅ {len(working)} çalışan proxy bulundu")
    
    def get_random_proxy(self) -> Optional[Dict[str, str]]:
        """Rastgele çalışan proxy döndür"""
        if not self.working_proxies:
            return None
        return random.choice(self.working_proxies)
    
    async def get_proxy_for_request(self) -> Optional[Dict[str, str]]:
        """İstek için proxy al (güncelleme yapmadan)"""
        # Sadece mevcut çalışan proxy'lerden rastgele seç
        return self.get_random_proxy()
    
    async def start_background_update(self):
        """Arka plan proxy güncellemesini başlat"""
        import asyncio
        while True:
            try:
                await self.update_proxy_list()
                # 6 saat bekle
                await asyncio.sleep(6 * 60 * 60)  # 6 saat = 21600 saniye
            except Exception as e:
                logger.error(f"❌ Arka plan proxy güncelleme hatası: {e}")
                # Hata durumunda 1 saat bekle
                await asyncio.sleep(60 * 60)  # 1 saat

# Global proxy manager
proxy_manager = EnhancedProxyManager()
