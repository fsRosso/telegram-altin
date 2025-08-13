FROM mcr.microsoft.com/playwright/python:v1.40.0-focal

# Çalışma dizinini ayarla
WORKDIR /app

# Python paketlerini kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# Bot'u çalıştır
CMD ["python", "main.py"]
