#!/bin/bash
set -e

echo "=== Git Pull ==="
git fetch origin
git reset --hard origin/main

echo "=== Docker Compose Pull ==="
docker compose pull

echo "=== Docker Compose Up ==="
docker compose up -d

echo "=== Django Migrate ==="
docker compose exec -T django python manage.py migrate --noinput

echo "=== Django Collectstatic ==="
docker compose exec -T django python manage.py collectstatic --noinput

echo "=== Health Check ==="
curl -f http://localhost:8080/ || (echo 'Health check failed' && exit 1)

echo "=== Deployment completed ==="
