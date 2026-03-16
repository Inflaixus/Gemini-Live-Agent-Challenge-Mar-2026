#!/usr/bin/env bash
# Set up the development environment.
set -euo pipefail

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example — edit it with your API key."
else
    echo ".env already exists."
fi

pip install -e .
echo "Dependencies installed. Run: uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload"
