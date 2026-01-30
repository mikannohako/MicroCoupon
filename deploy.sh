#!/bin/bash
set -e

echo "=== Update source ==="
git pull origin main

echo "=== Build & Run ==="
docker compose up -d --build

echo "=== Django migrate ==="
docker compose exec -T django python manage.py migrate --noinput

echo "=== Collectstatic ==="
docker compose exec -T django python manage.py collectstatic --noinput

echo "=== Done ==="
echo "Application deployed successfully!"