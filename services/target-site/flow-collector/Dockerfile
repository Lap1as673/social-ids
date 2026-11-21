FROM python:3.11-slim

WORKDIR /app

# Устанавливаем libpcap для Scapy
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpcap-dev \
    tcpdump \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Запуск от root (нужно для sniffing)
CMD ["python", "collector.py"]