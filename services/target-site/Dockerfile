FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Устанавливаем системные зависимости (curl для healthcheck, tcpdump для Scapy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpcap-dev \
    tcpdump \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app
COPY seed.py ./seed.py
COPY make_admin.py ./make_admin.py

# ДОБАВЛЯЕМ ЭТИ ДВЕ СТРОЧКИ
COPY collector.py ./collector.py
COPY features.py ./features.py

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]