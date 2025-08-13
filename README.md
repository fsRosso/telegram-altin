# Telegram Altın Fiyat Botu

🤖 XAURUB ve XAUUSD fiyat takibi yapan Telegram botu

## 🚀 Özellikler

- **XAURUB Fiyat Takibi**: ProFinance.ru'dan güncel fiyatlar
- **XAUUSD Fiyat Takibi**: TradingView'den güncel fiyatlar
- **Yüzde Hesaplama**: +0.01, -0.05 gibi yüzde artış/azalış hesaplamaları
- **Bölme İşlemleri**: XAURUB fiyatını belirli sayılara bölme
- **Instance Kontrolü**: Aynı anda sadece bir bot instance'ı çalışır

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

1. **Railway CLI kurulumu:**
```bash
npm install -g @railway/cli
```

2. **Projeyi Railway'e yükle:**
```bash
railway login
railway init
railway up
```

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
