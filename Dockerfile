# ---------------------------------------------------------------------------
# KaraokeTandem — imagen única (frontend compilado + backend FastAPI) para Render/Docker
# ---------------------------------------------------------------------------

# --- Stage 1: compila el frontend React (PWA) ---
FROM node:20-slim AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- Stage 2: runtime del backend (sirve la API + el frontend ya compilado) ---
FROM python:3.12-slim AS runtime
WORKDIR /app/backend

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

# Frontend compilado en la ruta que espera app/main.py (../frontend/dist)
COPY --from=frontend /frontend/dist /app/frontend/dist

ENV APP_ENV=production \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
