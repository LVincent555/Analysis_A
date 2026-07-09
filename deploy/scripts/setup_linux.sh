#!/usr/bin/env bash
set -euo pipefail

# Linux setup helper for stock_analysis_app.
# It intentionally keeps operational entry scripts under devops/.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend-client"
DEVOPS_DIR="$PROJECT_ROOT/devops"
DATA_DIR="$PROJECT_ROOT/data"

info() {
    printf '\033[0;34m[INFO]\033[0m %s\n' "$1"
}

warn() {
    printf '\033[1;33m[WARN]\033[0m %s\n' "$1"
}

ok() {
    printf '\033[0;32m[ OK ]\033[0m %s\n' "$1"
}

fail() {
    printf '\033[0;31m[FAIL]\033[0m %s\n' "$1" >&2
    exit 1
}

need_cmd() {
    command -v "$1" >/dev/null 2>&1 || fail "$1 is not installed"
}

echo "=========================================="
echo "stock_analysis_app Linux setup"
echo "=========================================="
info "Project root: $PROJECT_ROOT"

need_cmd python3
need_cmd node
need_cmd npm

if command -v psql >/dev/null 2>&1; then
    ok "PostgreSQL client detected: $(psql --version)"
else
    warn "PostgreSQL client is not installed. Skip this if the database is remote."
fi

[ -d "$BACKEND_DIR" ] || fail "Missing backend directory: $BACKEND_DIR"
[ -d "$FRONTEND_DIR" ] || fail "Missing frontend directory: $FRONTEND_DIR"
[ -d "$DEVOPS_DIR" ] || fail "Missing devops directory: $DEVOPS_DIR"

mkdir -p "$DATA_DIR" "$PROJECT_ROOT/logs"

info "Configuring backend"
cd "$BACKEND_DIR"
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        warn "Created backend/.env from .env.example. Review database settings before starting services."
    else
        warn "backend/.env and backend/.env.example are both missing."
    fi
else
    ok "backend/.env exists"
fi

if [ ! -d venv ]; then
    python3 -m venv venv
    ok "Created backend/venv"
else
    ok "backend/venv exists"
fi

source venv/bin/activate
python -m pip install --upgrade pip
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
else
    warn "backend/requirements.txt is missing"
fi
deactivate

info "Configuring frontend-client"
cd "$FRONTEND_DIR"
if [ ! -d node_modules ]; then
    npm install
else
    ok "frontend-client/node_modules exists"
fi

read -r -p "Build frontend-client now? [y/N] " build_frontend
if [[ "$build_frontend" =~ ^[Yy]$ ]]; then
    npm run build
    ok "frontend-client build complete"
else
    warn "Skipped frontend build"
fi

info "Checking data directory"
xlsx_count="$(find "$DATA_DIR" -maxdepth 1 -type f -name '*.xlsx' | wc -l | tr -d ' ')"
if [ "$xlsx_count" = "0" ]; then
    warn "No Excel files found in $DATA_DIR"
else
    ok "Found $xlsx_count Excel files in data/"
fi

info "Checking database connection"
cd "$BACKEND_DIR"
source venv/bin/activate
if python -c "from app.database import test_connection; import sys; sys.exit(0 if test_connection() else 1)" >/dev/null 2>&1; then
    ok "Database connection succeeded"
else
    warn "Database connection check failed. Review backend/.env before starting services."
fi
deactivate

info "Ensuring devops scripts are executable"
find "$DEVOPS_DIR" -maxdepth 1 -type f -name '*.sh' -exec chmod +x {} \;
if [ -d "$DEVOPS_DIR/certs" ]; then
    find "$DEVOPS_DIR/certs" -maxdepth 1 -type f -name '*.sh' -exec chmod +x {} \;
fi
ok "devops scripts are executable"

echo
echo "Next commands:"
echo "  bash devops/start_all.sh dev"
echo "  bash devops/start_all.sh"
echo "  bash devops/stop.sh"
echo
echo "Setup complete."
