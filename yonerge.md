# 🚀 Telegram Altın Fiyat Botu

## 📋 Proje Açıklaması
Bu bot ProFinance.ru sitesinden anlık altın (XAU/RUB) fiyatlarını çeker ve Telegram üzerinden kullanıcılara sunar.

## ✨ Özellikler
- **Anlık Fiyat Çekme**: Tablo tabanlı güvenilir fiyat çekme
- **Akıllı Fiyat Analizi**: Fiyat değişimlerini takip ve anormal değişimleri tespit
- **Telegram Bot**: Kolay kullanım için Telegram arayüzü
- **Yüzde Hesaplama**: Fiyat + belirtilen yüzde artışı
- **Bölme İşlemi**: Son fiyatı belirtilen sayıya bölme

## 🛠️ Kurulum
1. Gerekli kütüphaneleri yükleyin:
   ```bash
   pip install -r requirements.txt
   ```

2. `config.py` dosyasında bot token'ınızı ayarlayın

3. Botu çalıştırın:
   ```bash
   python telegram_bot.py
   ```

## 📱 Kullanım
- **Fiyat Sorgulama**: `+0.01`, `+0.05`, `+1` gibi
- **Bölme İşlemi**: `25`, `50`, `2.5` gibi
- **Yardım**: `/help` komutu

## 🔧 Test
Sistemi test etmek için:
```bash
python test_connection.py
```

## 📁 Proje Yapısı
- `price_fetcher_fast.py` - Ana fiyat çekme sistemi
- `telegram_bot.py` - Telegram bot ana dosyası
- `config.py` - Bot konfigürasyonu
- `requirements.txt` - Gerekli kütüphaneler
- `test_connection.py` - Test sistemi

## 🚀 Sistem Özellikleri
- **Akıllı Fiyat Doğrulama**: Sadece mantıksız değerleri uyarır
- **Fiyat Değişim Takibi**: Son 10 fiyatı saklar
- **Anormal Değişim Tespiti**: %5+ değişimleri otomatik tespit eder
- **Fallback Sistemi**: Boş fiyat durumunda alternatif satırları kontrol eder

## 📊 Test Sonuçları
✅ Tablo başlıkları doğru tanınıyor  
✅ Anlık fiyat çekiliyor: **8700.23 RUB**  
✅ Yüzde hesaplamaları çalışıyor  
✅ Fiyat değişim analizi aktif  
✅ Bot başarıyla çalışıyor  

---
**Son Güncelleme**: 11.08.2025  
**Versiyon**: 2.0 - Tablo Tabanlı Sistem
