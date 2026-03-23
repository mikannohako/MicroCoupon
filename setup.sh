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

    # Display prompt with [setup] prefix and default in brackets
    printf "[setup] %s [%s]: " "$prompt" "$default" >&2

    # Read from stdin with timeout (non-blocking for pipe inputs)
    if read -r -t 60 input 2>/dev/null; then
        if [[ -z "$input" ]]; then
            echo "$default"
        else
            echo "$input"
        fi
    else
        # Timeout or non-interactive: use default
        echo "$default"
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
    
    # Check if environment variables are already set
    if [[ -z "${DJANGO_ADMIN_USERNAME:-}" ]]; then
        local django_user django_pass django_email
        django_user=$(prompt_user_input "Username" "admin")
        django_pass=$(prompt_user_input "Password" "admin1234")
        django_email=$(prompt_user_input "Email" "admin@example.com")
        
        export DJANGO_ADMIN_USERNAME="$django_user"
        export DJANGO_ADMIN_PASSWORD="$django_pass"
        export DJANGO_ADMIN_EMAIL="$django_email"
    else
        log "Using env vars: DJANGO_ADMIN_USERNAME=$DJANGO_ADMIN_USERNAME"
    fi

    log ""
    log "=== Basic Auth Setup ==="
    
    if [[ -z "${BASIC_AUTH_USER:-}" ]]; then
        local basic_user basic_pass
        basic_user=$(prompt_user_input "Username (/admin)" "admin")
        basic_pass=$(prompt_user_input "Password (/admin)" "admin1234")
        
        export BASIC_AUTH_USER="$basic_user"
        export BASIC_AUTH_PASS="$basic_pass"
    else
        log "Using env vars: BASIC_AUTH_USER=$BASIC_AUTH_USER"
    fi

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

    log ""
    log "========================================================"
    log "✓ Initial setup completed successfully!"
    log "========================================================"
    log ""
    log "Open: http://localhost:8080"
    log "Login page: http://localhost:8080/account/login/"
    log ""
    log "Django Admin:"
    log "  Username: ${DJANGO_ADMIN_USERNAME:-admin}"
    log "  Password: ${DJANGO_ADMIN_PASSWORD:-admin1234}"
    log "  Email: ${DJANGO_ADMIN_EMAIL:-admin@example.com}"
    log ""
    log "Basic Auth (/admin path):"
    log "  Username: ${BASIC_AUTH_USER:-admin}"
    log "  Password: ${BASIC_AUTH_PASS:-admin1234}"
    log ""
}

main "$@" < /dev/tty 2>/dev/null || main "$@"
