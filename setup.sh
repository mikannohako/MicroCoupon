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
# Docker Composeの変数展開警告を避けるため、'$' は除外する
alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#%^&*(-_=+)"
print("".join(secrets.choice(alphabet) for _ in range(50)))
PY
}

prompt_user_input() {
    local prompt="$1"
    local default="$2"
    local input

    # Display prompt with [setup] prefix and default in brackets
    printf "[setup] %s [%s]: " "$prompt" "$default" >&2

    # Check if this is a password field (contains "Password" or "password")
    local is_password=0
    if [[ "$prompt" =~ [Pp]assword ]]; then
        is_password=1
    fi

    # Read from stdin with timeout (non-blocking for pipe inputs)
    if [[ $is_password -eq 1 ]]; then
        # Silent input for passwords
        if read -rs -t 60 input 2>/dev/null; then
            echo "" >&2  # Add newline after silent input
            if [[ -z "$input" ]]; then
                echo "$default"
            else
                echo "$input"
            fi
        else
            echo "" >&2  # Add newline on timeout
            echo "$default"
        fi
    else
        # Normal input for other fields
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
    fi
}

prompt_password_with_confirm() {
    local prompt="$1"
    local default="$2"
    local password1 password2

    # If non-interactive or default is being used, return default
    if ! [[ -t 0 ]]; then
        echo "$default"
        return
    fi

    while true; do
        # First password prompt
        printf "[setup] %s [%s]: " "$prompt" "$default" >&2
        if read -rs -t 60 password1 2>/dev/null; then
            echo "" >&2
        else
            echo "" >&2
            echo "$default"
            return
        fi

        # Use default if empty
        if [[ -z "$password1" ]]; then
            password1="$default"
        fi

        # Confirm password prompt
        printf "[setup] %s (confirm) [%s]: " "$prompt" "$default" >&2
        if read -rs -t 60 password2 2>/dev/null; then
            echo "" >&2
        else
            echo "" >&2
            echo "$default"
            return
        fi

        # Use default if empty
        if [[ -z "$password2" ]]; then
            password2="$default"
        fi

        # Check if passwords match
        if [[ "$password1" == "$password2" ]]; then
            echo "$password1"
            return
        else
            printf "[setup] ERROR: Passwords do not match. Please try again.\n" >&2
            echo "" >&2
        fi
    done
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
        django_pass=$(prompt_password_with_confirm "Password" "admin1234")
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
        basic_pass=$(prompt_password_with_confirm "Password (/admin)" "admin1234")
        
        export BASIC_AUTH_USER="$basic_user"
        export BASIC_AUTH_PASS="$basic_pass"
    else
        log "Using env vars: BASIC_AUTH_USER=$BASIC_AUTH_USER"
    fi

    log ""
    log "=== Server Configuration ==="
    
    local domain_name debug_mode
    domain_name=$(prompt_user_input "Domain name or IP:port" "localhost:8080")
    debug_mode=$(prompt_user_input "Debug mode (True/False)" "False")
    
    export DOMAIN_NAME="$domain_name"
    export DEBUG_MODE="$debug_mode"

    log ""
    log "=== Database Configuration ==="

    local db_user db_password
    db_user=$(prompt_user_input "DB Username" "microcoupon_user")
    db_password=$(prompt_password_with_confirm "DB Password" "microcoupon_pass")

    export POSTGRES_USER="$db_user"
    export POSTGRES_PASSWORD="$db_password"

    log ""
    log "Creating .env from .env.template"

    local secret
    secret="$(generate_secret_key)"
    local htpasswd_path="$PROJECT_ROOT/.htpasswd"
    local domain_name="${DOMAIN_NAME:-localhost:8080}"
    local debug_mode="${DEBUG_MODE:-False}"
    local db_user="${POSTGRES_USER:-microcoupon_user}"
    local db_password="${POSTGRES_PASSWORD:-microcoupon_pass}"

    # Use Python to read template, process values, and write with proper line endings (LF only)
    python3 - <<PYEOF
import sys

template_file = "$env_template"
output_file = "$env_file"
secret = "$secret"
htpasswd_path = "$htpasswd_path"
domain_name = "$domain_name"
debug_mode = "$debug_mode"
db_user = "$db_user"
db_password = "$db_password"

try:
    import re
    
    with open(template_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove any CRLF and normalize to LF
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    
    # Generate BASE_URL from DOMAIN_NAME
    if '://' in domain_name:
        base_url = domain_name
    else:
        base_url = f'http://{domain_name}'
    
    # Replace key=value lines (handles existing values correctly)
    # Uses regex to match "KEY=anything" and replace with "KEY=newvalue"
    content = re.sub(r'^SECRET_KEY=.*$', f'SECRET_KEY={secret}', content, flags=re.MULTILINE)
    content = re.sub(r'^DEBUG=.*$', f'DEBUG={debug_mode}', content, flags=re.MULTILINE)
    content = re.sub(r'^DOMAIN_NAME=.*$', f'DOMAIN_NAME={domain_name}', content, flags=re.MULTILINE)
    content = re.sub(r'^BASE_URL=.*$', f'BASE_URL={base_url}', content, flags=re.MULTILINE)
    content = re.sub(r'^POSTGRES_USER=.*$', f'POSTGRES_USER={db_user}', content, flags=re.MULTILINE)
    content = re.sub(r'^POSTGRES_PASSWORD=.*$', f'POSTGRES_PASSWORD={db_password}', content, flags=re.MULTILINE)
    content = re.sub(r'^BASIC_AUTH_FILE_HOST=.*$', f'BASIC_AUTH_FILE_HOST={htpasswd_path}', content, flags=re.MULTILINE)
    
    # Write with LF only (no CRLF)
    with open(output_file, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    
    print(f"[setup] Created {output_file} with proper line endings")
except Exception as e:
    print(f"[setup] ERROR: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
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

check_prerequisites() {
    log ""
    log "========================================================"
    log "Checking prerequisites..."
    log "========================================================"
    
    local all_ok=true
    
    # Check Docker installation
    log ""
    log "Checking Docker..."
    if ! command -v docker >/dev/null 2>&1; then
        log "  ✗ Docker is not installed"
        all_ok=false
    else
        log "  ✓ Docker is installed"
    fi
    
    # Check Docker Daemon
    log "Checking Docker Daemon..."
    if ! docker info >/dev/null 2>&1; then
        log "  ✗ Docker Daemon is not running"
        all_ok=false
    else
        log "  ✓ Docker Daemon is running"
    fi
    
    # Check Python 3
    log "Checking Python 3..."
    if ! command -v python3 >/dev/null 2>&1; then
        log "  ✗ Python 3 is not installed"
        all_ok=false
    else
        local python_version=$(python3 --version 2>&1 | awk '{print $2}')
        log "  ✓ Python 3 is installed ($python_version)"
    fi
    
    # Check docker compose/docker-compose
    log "Checking docker compose..."
    if docker compose version >/dev/null 2>&1; then
        local compose_version=$(docker compose version --short 2>&1)
        log "  ✓ docker compose is available ($compose_version)"
    elif command -v docker-compose >/dev/null 2>&1; then
        local compose_version=$(docker-compose --version 2>&1 | awk '{print $3}')
        log "  ✓ docker-compose is available ($compose_version)"
    else
        log "  ✗ Neither 'docker compose' nor 'docker-compose' is available"
        all_ok=false
    fi
    
    # Check required files
    log "Checking required files..."
    if [[ ! -f "$PROJECT_ROOT/.env.template" ]]; then
        log "  ✗ .env.template not found"
        all_ok=false
    else
        log "  ✓ .env.template found"
    fi
    
    if [[ ! -f "$PROJECT_ROOT/docker-compose.yml" ]]; then
        log "  ✗ docker-compose.yml not found"
        all_ok=false
    else
        log "  ✓ docker-compose.yml found"
    fi
    
    log ""
    if [[ "$all_ok" == "false" ]]; then
        log "========================================================"
        log "Prerequisites check failed!"
        log "========================================================"
        fail "Please install and configure missing prerequisites"
    fi
    
    log "========================================================"
    log "✓ All prerequisites are satisfied"
    log "========================================================"
}

    # Check prerequisites before starting setup
    check_prerequisites
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
    
    # Determine base URL from DOMAIN_NAME
    local domain="${DOMAIN_NAME:-localhost:8080}"
    local base_url
    if [[ "$domain" == *"://"* ]]; then
        base_url="$domain"
    else
        base_url="http://$domain"
    fi
    
    log "Open: $base_url"
    log "Login page: $base_url/account/login/"
    log ""
    log "Server Configuration:"
    log "  Domain: ${DOMAIN_NAME:-localhost:8080}"
    log "  Debug: ${DEBUG_MODE:-False}"
    log ""
    log "Django Admin:"
    log "  Username: ${DJANGO_ADMIN_USERNAME:-admin}"
    log "  Password: **********"
    log "  Email: ${DJANGO_ADMIN_EMAIL:-admin@example.com}"
    log ""
    log "Basic Auth (/admin path):"
    log "  Username: ${BASIC_AUTH_USER:-admin}"
    log "  Password: **********"
    log ""
}

main "$@" < /dev/tty || main "$@" < /dev/null
