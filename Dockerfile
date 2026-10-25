# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Системные утилиты: для unshare (изоляция) и прибивания процессов
RUN apt-get update \
 && apt-get install -y --no-install-recommends util-linux procps \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY static ./static

# Папка данных (в Amvera монтируется как volume)
RUN mkdir -p /data

EXPOSE 80

# Один процесс uvicorn — на бесплатном тарифе этого достаточно.
# Очередь проверок работает через asyncio.Semaphore внутри процесса.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
