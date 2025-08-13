FROM mcr.microsoft.com/playwright/python:v1.48.0-focal

# Python 3.11'i aktif et
ENV PYTHON_VERSION=3.11

# Çalışma dizinini ayarla
WORKDIR /app

# Python paketlerini kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# Bot'u çalıştır
CMD ["python3.11", "main.py"]
