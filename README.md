# 🚀 Telegram Altın Fiyat Botu

Bu bot hem ProFinance.ru'dan XAURUB hem de TradingView'den XAUUSD fiyat verilerini çeker.

## 🌐 Railway Deployment

### 📋 Gereksinimler
- Python 3.11+
- Telegram Bot Token
- Railway hesabı

### 🚀 Kurulum Adımları

1. **GitHub'a yükle:**
```bash
git add .
git commit -m "Railway deployment için hazır"
git push origin main
```

2. **Railway'e bağla:**
   - [Railway.app](https://railway.app) hesabı aç
   - "New Project" → "Deploy from GitHub repo"
   - Repo'yu seç

3. **Environment Variables ekle:**
   - `BOT_TOKEN`: Telegram bot token'ı
   - `BROWSER_TYPE`: webkit

4. **Deploy et!**

### 📱 Kullanım
- `+0.01`: XAURUB + %0.01 + XAUUSD
- `-0.05`: XAURUB - %0.05 + XAUUSD  
- `25`: XAURUB ÷ 25 vs XAUUSD

### ⚠️ Not
- Bot uyku modunda bekler
- Telegram mesajı geldiğinde otomatik uyanır
- %0.5 fark uyarısı verir
