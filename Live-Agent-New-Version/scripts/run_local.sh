#!/usr/bin/env bash
# Run the server locally.
set -euo pipefail

PORT="${PORT:-8080}"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --reload
