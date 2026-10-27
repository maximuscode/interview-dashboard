#!/usr/bin/env bash
# Everything CI would run: lint and tests, both halves.
#
#   ./check.sh
#
# Exits non-zero if any step fails.

set -euo pipefail
cd "$(dirname "$0")"

step() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }

[ -d backend/.venv ] || { echo "Run ./dev.sh first to install dependencies."; exit 1; }
[ -d frontend/node_modules ] || { echo "Run ./dev.sh first to install dependencies."; exit 1; }

step "Backend lint (ruff)"
backend/.venv/bin/ruff check backend

step "Backend tests (pytest)"
(cd backend && .venv/bin/python -m pytest -q)

step "Frontend types (tsc)"
(cd frontend && bunx tsc --noEmit)

step "Frontend lint (oxlint)"
(cd frontend && bunx oxlint src/)

step "Frontend tests (vitest)"
(cd frontend && bunx vitest run --reporter=dot)

printf '\n\033[1;32mAll checks passed.\033[0m\n'
