# Stage 1: Build React UI
FROM node:20-slim AS ui-builder

WORKDIR /ui

COPY ui/package.json ui/package-lock.json ./
RUN npm ci

COPY ui/ ./
RUN npm run build

# Stage 2: Python backend
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY Live-Agent-New-Version/pyproject.toml .
COPY Live-Agent-New-Version/app/ app/
COPY Live-Agent-New-Version/kb/ kb/

# Copy built React UI (served as static files by FastAPI)
COPY --from=ui-builder /ui/dist ui/

RUN pip install --upgrade pip \
    && pip install --no-cache-dir \
        torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir .

ENV PORT=8080

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
