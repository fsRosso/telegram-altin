FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

# Python path'ini ayarla
ENV PATH="/usr/local/bin:$PATH"

# Mevcut Python ve pip sürümlerini kontrol et
RUN python3 --version
RUN which python3
RUN ls -la /usr/bin/python*

# pip'in gerçek konumunu bul
RUN which pip || echo "pip bulunamadı"
RUN which pip3 || echo "pip3 bulunamadı"
RUN find /usr -name "pip*" 2>/dev/null || echo "pip dosyaları bulunamadı"
RUN find /usr/local -name "pip*" 2>/dev/null || echo "pip dosyaları bulunamadı"

# Python 3.10'u aktif et (Ubuntu 22.04'te varsayılan)
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1

# pip alternatiflerini kontrol et ve kur
RUN pip --version || echo "pip bulunamadı"
RUN pip3 --version || echo "pip3 bulunamadı"
RUN python3 -m pip --version || echo "python3 -m pip bulunamadı"

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
