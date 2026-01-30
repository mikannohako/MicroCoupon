#!/bin/sh
set -e

echo "=== Apply migrations ==="
python manage.py migrate --noinput

echo "=== Collect static files ==="
python manage.py collectstatic --noinput

echo "=== Deployment completed ==="
echo "=== Git Pull ==="
git pull

echo "=== Docker Compose Build & Pull ==="
docker compose pull
docker compose build

echo "=== Docker Compose Up (Recreate) ==="
docker compose up -d

echo "=== Django Migrate ==="
docker compose exec microcoupon-django python manage.py migrate --noinput

echo "=== Django Collectstatic ==="
docker compose exec microcoupon-django python manage.py collectstatic --noinput

echo "=== Health Check (nginx) ==="
curl -f http://localhost/ || (echo 'Health check failed' && exit 1)

echo "=== Deployment completed ==="
