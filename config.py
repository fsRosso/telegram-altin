# Telegram Bot Konfigürasyonu
# BotFather'dan aldığınız token'ı buraya yazın

BOT_TOKEN = "8305326180:AAFXBcHmz7ZOnr-hAT9Tn5cblhzOasYXWWg"

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
