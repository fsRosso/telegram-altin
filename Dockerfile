FROM mcr.microsoft.com/playwright/python:v1.48.0-focal

# Python path'ini ayarla
ENV PATH="/usr/local/bin:$PATH"
ENV PYTHONPATH="/usr/local/lib/python3.11/site-packages:$PYTHONPATH"

# Çalışma dizinini ayarla
WORKDIR /app

# Sistem paketlerini güncelle
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python paketlerini kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright browser'ları kur
RUN playwright install chromium
RUN playwright install-deps chromium

# Uygulama dosyalarını kopyala
COPY . .

# Çalıştırma izinlerini ver
RUN chmod +x main.py

# Bot'u çalıştır
CMD ["python", "main.py"]
