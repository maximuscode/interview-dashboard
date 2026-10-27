#!/usr/bin/env bash
# Start both halves of the dashboard with one command.
#
#   ./dev.sh          start backend + frontend
#   ./dev.sh --reseed regenerate the database first
#
# Ctrl-C stops both.

set -euo pipefail
cd "$(dirname "$0")"

BACKEND_PORT=8000
FRONTEND_PORT=5173

for tool in python3 bun; do
  command -v "$tool" >/dev/null || { echo "Missing $tool. Install it and retry."; exit 1; }
done

# --- backend ---------------------------------------------------------------
cd backend

if [ ! -d .venv ]; then
  echo "Creating virtualenv and installing backend dependencies..."
  python3 -m venv .venv
  ./.venv/bin/pip install --quiet --upgrade pip
  ./.venv/bin/pip install --quiet -e ".[dev]"
fi

if [ "${1:-}" = "--reseed" ]; then
  rm -f interviews.db
fi

# Seeding is its own step: with multiple workers a check-then-insert at startup
# would race and multiply the dataset.
./.venv/bin/python -m app.seed

./.venv/bin/uvicorn app.main:app --port "$BACKEND_PORT" --reload &
BACKEND_PID=$!

# --- frontend --------------------------------------------------------------
cd ../frontend

[ -d node_modules ] || { echo "Installing frontend dependencies..."; bun install; }

bun run dev --port "$FRONTEND_PORT" &
FRONTEND_PID=$!

# Stop both on Ctrl-C, and if either dies on its own.
cleanup() { kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

cat <<BANNER

  Dashboard   http://localhost:$FRONTEND_PORT
  API docs    http://localhost:$BACKEND_PORT/docs

  Ctrl-C stops both.

BANNER

# `wait -n` needs bash 4; macOS ships 3.2, so poll instead.
while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
  sleep 1
done
