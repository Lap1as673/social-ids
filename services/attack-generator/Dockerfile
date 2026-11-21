FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# По умолчанию ничего не запускаем, ждём команду
CMD ["python", "cli.py", "--help"]