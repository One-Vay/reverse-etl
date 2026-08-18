#!/usr/bin/env bash
# Build and run the full Reverse ETL stack (Postgres + backend + frontend)
# with Docker Compose. Safe to re-run: it reuses the existing .env and
# rebuilds images only when their sources changed.
#
# Usage:
#   ./deploy.sh            Build and start everything (default)
#   ./deploy.sh up          Same as above
#   ./deploy.sh down        Stop and remove containers (keeps the database volume)
#   ./deploy.sh down -v     Stop and remove containers AND the database volume
#   ./deploy.sh logs        Follow logs for all services
#   ./deploy.sh restart     Restart all services without rebuilding

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

COMMAND="${1:-up}"

# --- Resolve the Docker Compose command (v2 plugin vs legacy standalone binary) ---
if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "Error: Docker Compose is not installed. Install Docker Desktop (includes the compose plugin)." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Error: the Docker daemon isn't running. Start Docker Desktop and try again." >&2
  exit 1
fi

# --- Handle simple passthrough commands ---
case "$COMMAND" in
  down)
    shift || true
    "${COMPOSE[@]}" down "$@"
    exit 0
    ;;
  logs)
    "${COMPOSE[@]}" logs -f
    exit 0
    ;;
  restart)
    "${COMPOSE[@]}" restart
    exit 0
    ;;
  up) ;;
  *)
    echo "Unknown command: $COMMAND" >&2
    echo "Usage: $0 [up|down|logs|restart]" >&2
    exit 1
    ;;
esac

# --- Ensure a .env file exists with real secrets ---
if [ ! -f .env ]; then
  echo "No .env found — creating one from .env.example with generated secrets."
  cp .env.example .env

  PYTHON=""
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PYTHON="$candidate"
      break
    fi
  done

  SECRET_KEY=""
  ENCRYPTION_KEY=""
  if [ -n "$PYTHON" ]; then
    SECRET_KEY="$("$PYTHON" -c 'import secrets; print(secrets.token_urlsafe(32))' 2>/dev/null || true)"
    ENCRYPTION_KEY="$("$PYTHON" -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' 2>/dev/null || true)"
  fi
  if [ -z "$SECRET_KEY" ]; then
    SECRET_KEY="$(openssl rand -base64 32 2>/dev/null || true)"
  fi

  if [ -z "$SECRET_KEY" ] || [ -z "$ENCRYPTION_KEY" ]; then
    echo "Error: could not auto-generate secrets (needs python3/python, ideally with the 'cryptography' package)." >&2
    echo "Set SECRET_KEY and ENCRYPTION_KEY in .env manually, then re-run this script. For example:" >&2
    echo '  python -c "import secrets; print(secrets.token_urlsafe(32))"' >&2
    echo '  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"' >&2
    exit 1
  fi

  # Portable in-place edit (works with both GNU and BSD/macOS sed).
  sed_i() { sed -i.bak "$1" .env && rm -f .env.bak; }
  sed_i "s|^SECRET_KEY=.*|SECRET_KEY=${SECRET_KEY}|"
  sed_i "s|^ENCRYPTION_KEY=.*|ENCRYPTION_KEY=${ENCRYPTION_KEY}|"
  echo "Generated SECRET_KEY and ENCRYPTION_KEY in .env."
fi

# --- Build and start everything ---
echo "Building and starting containers..."
"${COMPOSE[@]}" up -d --build

# --- Wait for the backend to become ready ---
BACKEND_PORT="$(grep -E '^BACKEND_PORT=' .env | cut -d= -f2)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="$(grep -E '^FRONTEND_PORT=' .env | cut -d= -f2)"
FRONTEND_PORT="${FRONTEND_PORT:-80}"

echo "Waiting for the backend to become ready..."
ready=false
for i in $(seq 1 60); do
  if curl -sf "http://localhost:${BACKEND_PORT}/health" >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 2
done

if [ "$ready" != true ]; then
  echo "Backend did not become ready in time. Check logs with: ${COMPOSE[*]} logs backend" >&2
  exit 1
fi

cat <<EOF

Reverse ETL is up and running.

  Frontend:   http://localhost:${FRONTEND_PORT}
  Backend:    http://localhost:${BACKEND_PORT}
  API docs:   http://localhost:${BACKEND_PORT}/docs

  View logs:      ./deploy.sh logs
  Restart:        ./deploy.sh restart
  Stop:           ./deploy.sh down
  Stop + wipe DB: ./deploy.sh down -v
EOF
