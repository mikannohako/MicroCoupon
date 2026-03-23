#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

log() {
  echo "[setup] $*"
}

fail() {
  echo "[setup] ERROR: $*" >&2
  exit 1
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "Required command not found: $1"
  fi
}

pick_compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose)
  elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
  else
    fail "docker compose or docker-compose is required"
  fi
}

generate_secret_key() {
  python3 - <<'PY'
import secrets
alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*(-_=+)"
print("".join(secrets.choice(alphabet) for _ in range(50)))
PY
}

setup_env_file() {
  local env_file="$PROJECT_ROOT/.env"
  local env_template="$PROJECT_ROOT/.env.template"

  if [[ -f "$env_file" ]]; then
    log ".env already exists. Skip creating .env"
    return
  fi

  [[ -f "$env_template" ]] || fail ".env.template not found"

  log "Creating .env from .env.template"
  cp "$env_template" "$env_file"

  local secret
  secret="$(generate_secret_key)"
  sed -i "s#^SECRET_KEY=.*#SECRET_KEY=$secret#" "$env_file"

  # Linux local default: keep basic auth file in project root
  local htpasswd_path
  htpasswd_path="$PROJECT_ROOT/.htpasswd"
  sed -i "s#^BASIC_AUTH_FILE_HOST=.*#BASIC_AUTH_FILE_HOST=$htpasswd_path#" "$env_file"
}

setup_basic_auth_file() {
  local env_file="$PROJECT_ROOT/.env"
  [[ -f "$env_file" ]] || fail ".env not found"

  local htpasswd_path
  htpasswd_path="$(grep '^BASIC_AUTH_FILE_HOST=' "$env_file" | cut -d'=' -f2-)"
  [[ -n "$htpasswd_path" ]] || fail "BASIC_AUTH_FILE_HOST is empty in .env"

  local basic_user="${BASIC_AUTH_USER:-admin}"
  local basic_pass="${BASIC_AUTH_PASS:-admin1234}"

  if [[ -f "$htpasswd_path" ]]; then
    log "Basic auth file already exists: $htpasswd_path"
    return
  fi

  log "Creating basic auth file: $htpasswd_path"
  mkdir -p "$(dirname "$htpasswd_path")"

  docker run --rm httpd:2.4-alpine htpasswd -nbB "$basic_user" "$basic_pass" > "$htpasswd_path"
  chmod 600 "$htpasswd_path"
}

wait_for_db() {
  log "Waiting for database to be ready"
  local retries=30
  local count=0

  until "${COMPOSE[@]}" exec -T db sh -lc 'pg_isready -U "$POSTGRES_USER"' >/dev/null 2>&1; do
    count=$((count + 1))
    if [[ "$count" -ge "$retries" ]]; then
      fail "Database did not become ready in time"
    fi
    sleep 2
  done

  log "Database is ready"
}

run_django_init() {
  log "Running migrations"
  "${COMPOSE[@]}" exec -T django python manage.py migrate --noinput

  log "Collecting static files"
  "${COMPOSE[@]}" exec -T django python manage.py collectstatic --noinput
}

create_or_update_admin_user() {
  local username="${DJANGO_ADMIN_USERNAME:-admin}"
  local password="${DJANGO_ADMIN_PASSWORD:-admin1234}"
  local email="${DJANGO_ADMIN_EMAIL:-admin@example.com}"

  log "Creating/updating Django admin user: $username"
  "${COMPOSE[@]}" exec -T \
    -e DJANGO_ADMIN_USERNAME="$username" \
    -e DJANGO_ADMIN_PASSWORD="$password" \
    -e DJANGO_ADMIN_EMAIL="$email" \
    django python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ["DJANGO_ADMIN_USERNAME"]
password = os.environ["DJANGO_ADMIN_PASSWORD"]
email = os.environ["DJANGO_ADMIN_EMAIL"]

user, created = User.objects.get_or_create(
    username=username,
    defaults={
        "email": email,
        "is_active": True,
        "is_staff": True,
        "is_superuser": True,
        "user_type": "admin",
    },
)

# Re-run safe: keep credentials/role up to date
user.email = email
user.is_active = True
user.is_staff = True
user.is_superuser = True
if hasattr(user, "user_type"):
    user.user_type = "admin"
user.set_password(password)
user.save()

print(f"admin user ready: {username} (created={created})")
PY
}

main() {
  require_cmd docker
  require_cmd python3
  pick_compose_cmd

  if ! docker info >/dev/null 2>&1; then
    fail "Docker daemon is not running"
  fi

  setup_env_file
  setup_basic_auth_file

  log "Starting containers"
  "${COMPOSE[@]}" up -d --build

  wait_for_db
  run_django_init
  create_or_update_admin_user

  cat <<EOF

[setup] Initial setup completed.
[setup] Open: http://localhost:8080
[setup] Login page: http://localhost:8080/account/login/
[setup] Admin username: ${DJANGO_ADMIN_USERNAME:-admin}
[setup] Admin password: ${DJANGO_ADMIN_PASSWORD:-admin1234}

Tips:
- Override credentials before running:
  DJANGO_ADMIN_USERNAME=owner DJANGO_ADMIN_PASSWORD='strong-password' ./setup.sh
- Override basic auth:
  BASIC_AUTH_USER=admin BASIC_AUTH_PASS='strong-basic-pass' ./setup.sh
EOF
}

main "$@"
