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

prompt_user_input() {
    local prompt="$1"
    local default="$2"
    local input

    if [[ -n "$default" ]]; then
        printf "%s [%s]: " "$prompt" "$default"
    else
        printf "%s: " "$prompt"
    fi

    read -r input
    
    # Return default if empty input
    if [[ -z "$input" ]]; then
        echo "$default"
    else
        echo "$input"
    fi
}

setup_env_file() {
    local env_file="$PROJECT_ROOT/.env"
    local env_template="$PROJECT_ROOT/.env.template"

    if [[ -f "$env_file" ]]; then
        log ".env already exists. Skip creating .env"
        return
    fi

    [[ -f "$env_template" ]] || fail ".env.template not found"

    log ""
    log "=== Django Admin User Setup ==="
    local django_user django_pass django_email
    django_user=$(prompt_user_input "Django admin username" "admin")
    django_pass=$(prompt_user_input "Django admin password" "admin1234")
    django_email=$(prompt_user_input "Django admin email" "admin@example.com")

    log ""
    log "=== Basic Auth Setup ==="
    local basic_user basic_pass
    basic_user=$(prompt_user_input "Basic auth username (for /admin)" "admin")
    basic_pass=$(prompt_user_input "Basic auth password" "admin1234")

    log ""
    log "Creating .env from .env.template"

    local secret
    secret="$(generate_secret_key)"
    local htpasswd_path="$PROJECT_ROOT/.htpasswd"

    # Use Python to read template, process values, and write with proper line endings (LF only)
    python3 - <<PYEOF
import sys

template_file = "$env_template"
output_file = "$env_file"
secret = "$secret"
htpasswd_path = "$htpasswd_path"

try:
    with open(template_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove any CRLF and normalize to LF
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    
    # Replace placeholders
    content = content.replace('SECRET_KEY=', f'SECRET_KEY={secret}')
    content = content.replace('BASIC_AUTH_FILE_HOST=', f'BASIC_AUTH_FILE_HOST={htpasswd_path}')
    
    # Write with LF only (no CRLF)
    with open(output_file, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    
    print(f"[setup] Created {output_file} with proper line endings")
except Exception as e:
    print(f"[setup] ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
    
    # Export for later use
    export DJANGO_ADMIN_USERNAME="$django_user"
    export DJANGO_ADMIN_PASSWORD="$django_pass"
    export DJANGO_ADMIN_EMAIL="$django_email"
    export BASIC_AUTH_USER="$basic_user"
    export BASIC_AUTH_PASS="$basic_pass"
}

setup_basic_auth_file() {
    local env_file="$PROJECT_ROOT/.env"
    [[ -f "$env_file" ]] || fail ".env not found"

    local htpasswd_path
    htpasswd_path="$(grep '^BASIC_AUTH_FILE_HOST=' "$env_file" | cut -d'=' -f2-)"
    [[ -n "$htpasswd_path" ]] || fail "BASIC_AUTH_FILE_HOST is empty in .env"

    # Use environment variables set by setup_env_file, fallback to defaults
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

remove_conflicting_named_containers() {
    local auto_remove="${AUTO_REMOVE_CONFLICTING_CONTAINERS:-1}"
    local names=(
        "microcoupon-django"
        "microcoupon-postgres"
        "microcoupon-nginx"
    )

    for name in "${names[@]}"; do
        if docker ps -a --format '{{.Names}}' | grep -Fxq "$name"; then
        if [[ "$auto_remove" == "1" ]]; then
            log "Removing conflicting container: $name"
            docker rm -f "$name" >/dev/null
        else
            fail "Container name conflict detected: $name (set AUTO_REMOVE_CONFLICTING_CONTAINERS=1 to auto-fix)"
        fi
        fi
    done
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

    log "Creating/updating Django admin user: $username (email: $email)"
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

    log ""
    log "========================================================"
    log "MicroCoupon Setup"
    log "========================================================"

    setup_env_file
    setup_basic_auth_file
    remove_conflicting_named_containers

    log ""
    log "Starting containers..."
    "${COMPOSE[@]}" up -d --build

    wait_for_db
    run_django_init
    create_or_update_admin_user

    cat <<EOF

========================================================
[setup] ✓ Initial setup completed successfully!
========================================================

Open: http://localhost:8080
Login page: http://localhost:8080/account/login/

Django Admin:
  Username: ${DJANGO_ADMIN_USERNAME:-admin}
  Password: ${DJANGO_ADMIN_PASSWORD:-admin1234}
  Email: ${DJANGO_ADMIN_EMAIL:-admin@example.com}

Basic Auth (/admin path):
  Username: ${BASIC_AUTH_USER:-admin}
  Password: ${BASIC_AUTH_PASS:-admin1234}

========================================================
EOF
}

main "$@"
