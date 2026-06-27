# syntax=docker/dockerfile:1.7
# Stage 1: Build the Next.js static export
FROM node:20-slim AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./frontend/
WORKDIR /build/frontend
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime with uv
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir uv==0.5.11
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock* ./backend/
WORKDIR /app/backend
RUN uv sync --frozen --no-dev || uv sync --no-dev
COPY backend/ ./
# Copy the built static export from stage 1
COPY --from=frontend-build /build/frontend/out /app/static
RUN mkdir -p /app/db
EXPOSE 8000
WORKDIR /app/backend
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
