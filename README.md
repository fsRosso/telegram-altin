# Telegram Altın Fiyat Botu

🤖 XAURUB ve XAUUSD fiyat takibi yapan Telegram botu

## 🚀 Özellikler

- **XAURUB Fiyat Takibi**: ProFinance.ru'dan güncel fiyatlar
- **XAUUSD Fiyat Takibi**: TradingView'den güncel fiyatlar (tvDatafeed + Playwright fallback)
- **Yüzde Hesaplama**: +0.01, -0.05 gibi yüzde artış/azalış hesaplamaları
- **Bölme İşlemleri**: XAURUB fiyatını belirli sayılara bölme
- **Instance Kontrolü**: Aynı anda sadece bir bot instance'ı çalışır
- **Hızlı Fiyat Çekme**: tvDatafeed ile headless WebSocket bağlantısı (Playwright fallback)

## 🛠️ Kurulum

### Lokal Kurulum

1. **Dependencies kurulumu:**
```bash
pip install -r requirements.txt
```

2. **Config ayarları:**
```bash
# config.py dosyasında BOT_TOKEN'ı güncelleyin
```

3. **Bot'u çalıştır:**
```bash
python main.py
```

### Railway Deployment

1. **Railway'de GitHub Repo'yu Bağla:**
   - https://railway.app/ → "New Project" → "Deploy from GitHub repo"
   - `fsRosso/telegram-altin` repo'sunu seç

2. **Environment Variables Ekle:**
   ```
   BOT_TOKEN_DIFFERENT = YOUR_TELEGRAM_BOT_TOKEN
   TV_USERNAME = YOUR_TRADINGVIEW_USERNAME  (opsiyonel)
   TV_PASSWORD = YOUR_TRADINGVIEW_PASSWORD  (opsiyonel)
   ```
   
   **Not:** TV_USERNAME ve TV_PASSWORD eklenmezse otomatik olarak Playwright fallback kullanılır.

3. **Deploy:**
   - Railway otomatik olarak deploy edecek
   - Logs'tan durumu takip edin

## 🔧 Sorun Giderme

### "Conflict: terminated by other getUpdates request" Hatası

Bu hata genellikle birden fazla bot instance'ının çalışmasından kaynaklanır.

**Çözümler:**

1. **Railway Dashboard'da:**
   - Deployments sekmesine git
   - Eski deployment'ları durdur/sil
   - Yeni deployment yap

2. **Lokal bilgisayarda:**
   - Eski bot process'lerini durdur
   - PID dosyalarını temizle: `rm -f bot_*.pid`

3. **Instance kontrolü:**
   - `config.py`'de `ENABLE_INSTANCE_CONTROL = True` olduğundan emin ol

## 📱 Kullanım

- **Start**: `/start` - Bot'u başlat
- **Help**: `/help` - Yardım menüsü
- **Fiyat Sorgulama**: `+0.01`, `-0.05` gibi yüzde hesaplamaları
- **Bölme**: `25`, `50` gibi sayılar ile bölme işlemleri

## 🏗️ Proje Yapısı

```
telegram-fiyat-cekme/
├── main.py                 # Ana çalıştırma dosyası
├── telegram_bot.py         # Bot ana sınıfı
├── price_fetcher_fast.py   # XAURUB fiyat çekici
├── tradingview_*.py        # TradingView fiyat çekicileri
├── config.py               # Konfigürasyon
├── startup.sh              # Railway startup script
├── Dockerfile              # Docker container
└── requirements.txt        # Python dependencies
```

## 📝 Notlar

- Bot instance kontrolü sayesinde aynı anda sadece bir instance çalışır
- Railway'de deployment yaparken eski instance'ları durdurun
- PID dosyaları otomatik olarak temizlenir
