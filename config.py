# Telegram Bot Konfigürasyonu
# BotFather'dan aldığınız token'ı buraya yazın

import os

# Environment variable'dan token al, yoksa default kullan
BOT_TOKEN = os.getenv("BOT_TOKEN_DIFFERENT", "YENİ_TOKEN_BURAYA")

# Örnek token formatı:
# BOT_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"

# Diğer ayarlar
PRICE_UPDATE_TIMEOUT = 8  # Saniye cinsinden timeout süresi (15s → 8s)
DEFAULT_INCREMENT = 0.01   # Varsayılan artış miktarı

# Browser ve Hız Optimizasyon Ayarları
BROWSER_TYPE = "chromium"  # "chromium", "firefox", "webkit" - chromium daha stabil
PAGE_LOAD_WAIT = 1.5       # Sayfa yükleme bekleme süresi (3s → 1.5s)
ENABLE_BROWSER_OPTIMIZATION = True  # Browser optimizasyonlarını etkinleştir

# Instance Kontrol Ayarları
ENABLE_INSTANCE_CONTROL = False  # Railway'de geçici olarak kapatıldı
INSTANCE_CHECK_INTERVAL = 30   # Instance kontrol aralığı (saniye)

# Timezone Ayarları
TIMEZONE = "Europe/Istanbul"  # Türkiye saati

# Fiyat Doğrulama Ayarları
PRICE_VALIDATION_TOLERANCE = 5.0  # %5 tolerans (anormallik tespiti için)

# Cache Ayarları
CACHE_DURATION = 3.0  # Cache süresi (saniye) - 3 saniye içinde tekrar istek varsa cache'den ver
