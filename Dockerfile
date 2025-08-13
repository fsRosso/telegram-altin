FROM python:3.11-slim

# Sistem paketlerini kur
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Çalışma dizinini ayarla
WORKDIR /app

# Python paketlerini kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright browser'ları kur
RUN playwright install chromium

# Uygulama dosyalarını kopyala
COPY . .

# Bot'u çalıştır
CMD ["python", "main.py"]
