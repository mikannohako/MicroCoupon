FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt update && apt install -y build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 静的ファイルの収集と生成
RUN mkdir -p /app/staticfiles && \
    python manage.py collectstatic --noinput --clear 2>/dev/null || true

# エラーテンプレートを staticfiles にコピー
RUN cp /app/templates/404.html /app/staticfiles/404.html && \
    cp /app/templates/500.html /app/staticfiles/500.html
