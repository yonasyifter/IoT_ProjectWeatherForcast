# --- STAGE 1: Node Base (Shared Environment) ---
FROM node:20-alpine AS node-base
WORKDIR /app
# We stay in /app but don't copy specific code yet to keep the base "clean"

# --- STAGE 2: Admin Development ---
FROM node-base AS admin-side
# Copy only admin dependencies first for better caching
COPY ./admin-side/package*.json ./ 
RUN npm ci
COPY ./admin-side/ .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]

# --- STAGE 4: Backend (FastAPI) ---
FROM python:3.11-slim AS backend
# ... (your existing ENV and apt-get lines)
ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PIP_NO_CACHE_DIR=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && \
  apt-get install -y --no-install-recommends curl && \
  rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY ./backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./backend/app/ ./app/


RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
