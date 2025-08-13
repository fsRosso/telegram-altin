# 🚀 PythonAnywhere Kurulum Rehberi

## 📋 Gereksinimler
- ✅ PythonAnywhere Hacker Plan ($12/ay)
- ✅ Telegram Bot Token
- ✅ GitHub hesabı (kodları yüklemek için)

## 🔧 Adım Adım Kurulum

### 1️⃣ PythonAnywhere'e Giriş
- [pythonanywhere.com](https://www.pythonanywhere.com) adresine git
- Hacker plan ile giriş yap

### 2️⃣ Yeni Web App Oluştur
- **Web** sekmesine git
- **Add a new web app** tıkla
- **Manual configuration** seç
- **Python 3.11** seç
- **Next** tıkla

### 3️⃣ Kodları Yükle
```bash
# Consoles sekmesinde:
cd ~/telegram-fiyat-cekme
git clone https://github.com/kullaniciadi/telegram-fiyat-cekme.git
cd telegram-fiyat-cekme
```

### 4️⃣ Gerekli Paketleri Yükle
```bash
pip install --user -r requirements.txt
```

### 5️⃣ Playwright Kurulumu
```bash
playwright install
playwright install-deps
```

### 6️⃣ Web App Ayarları
- **Web** sekmesine geri dön
- **Code** bölümünde:
  - **Source code**: `/home/kullaniciadi/telegram-fiyat-cekme`
  - **Working directory**: `/home/kullaniciadi/telegram-fiyat-cekme`
- **WSGI configuration file** tıkla
- Tüm içeriği sil ve şunu yapıştır:

```python
import sys
import os

# Proje dizinini Python path'ine ekle
path = '/home/kullaniciadi/telegram-fiyat-cekme'
if path not in sys.path:
    sys.path.append(path)

# WSGI uygulamasını import et
from wsgi import application
```

### 7️⃣ Environment Variables
- **Web** sekmesinde **Environment variables** bölümünde:
  - **BOT_TOKEN**: `your_telegram_bot_token_here`

### 8️⃣ Reload Web App
- **Reload** butonuna tıkla

### 9️⃣ Webhook URL'ini Kopyala
- Web app URL'ini kopyala: `https://kullaniciadi.pythonanywhere.com`

### 🔗 Telegram Webhook Ayarı
```bash
# Consoles'da:
python
>>> from telegram_bot import TelegramBot
>>> from config import BOT_TOKEN
>>> bot = TelegramBot(BOT_TOKEN)
>>> bot.setup_webhook("https://kullaniciadi.pythonanywhere.com/webhook")
```

## ✅ Test Et
- Telegram'da botuna mesaj gönder
- PythonAnywhere **Web** sekmesinde **Log files** kontrol et

## 🚨 Sorun Giderme

### Bot Yanıt Vermiyor
- **Log files** kontrol et
- Webhook URL doğru mu?
- BOT_TOKEN doğru mu?

### Playwright Hatası
```bash
playwright install-deps
```

### Import Hatası
- **Working directory** doğru mu?
- **Source code** doğru mu?

## 📱 Bot Kullanımı
- **+0.01**: XAURUB + %0.01 + XAUUSD
- **-0.05**: XAURUB - %0.05 + XAUUSD  
- **25**: XAURUB ÷ 25 vs XAUUSD karşılaştırma

## 🔄 Güncelleme
```bash
cd ~/telegram-fiyat-cekme
git pull
# Web app'i reload et
```

## 💰 Maliyet
- **Hacker Plan**: $12/ay
- **Sürekli çalışır** (uyku modu yok)
- **1GB disk alanı**
- **Özel domain**

## 🎯 Avantajlar
- ✅ Sürekli çalışır
- ✅ Güvenilir
- ✅ Detaylı loglar
- ✅ SSH erişimi
- ✅ Kolay yönetim
