FROM python:3.12-slim

# LightGBM dlopens libgomp.so.1 (OpenMP runtime) at import time.
# python:3.12-slim ships without it, so ctypes.cdll.LoadLibrary raises
# "libgomp.so.1: cannot open shared object file" during model load.
# Installing libgomp1 fixes Tier 3 recommendations.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first for layer caching.
# README.md is required because pyproject.toml references it as the project readme.
COPY pyproject.toml uv.lock README.md ./

# Install dependencies only (no project) — cached layer independent of src/ changes.
RUN uv sync --locked --no-dev --no-install-project --extra service --extra runtime

# Copy application source
COPY src/ ./src/
COPY configs/ ./configs/

# Install the project itself now that src/ is in place.
RUN uv sync --locked --no-dev --extra service --extra runtime

# Copy model bundle directory (may contain only .gitkeep at build time;
# degraded-start contract in create_app() handles the missing-model case at runtime)
COPY models/ ./models/

# Create persistent data directory and a non-root system user
RUN mkdir -p /var/lib/meshek/merchants \
    && adduser --system --no-create-home appuser \
    && chown -R appuser /var/lib/meshek/merchants /app

USER appuser

EXPOSE 8000

ENV MESHEK_DATA_DIR=/var/lib/meshek/merchants \
    MESHEK_MODEL_PATH=/app/models/lightgbm_v1.bundle \
    MESHEK_MODELS_DIR=/app/models \
    MESHEK_API_HOST=0.0.0.0 \
    MESHEK_API_PORT=8000 \
    MESHEK_LOG_LEVEL=info \
    PATH="/app/.venv/bin:$PATH"

# Accept 503 as "alive" — degraded service still responds.
# Fly.io http_service.checks tightens this to 200-only at the platform level.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status in (200,503) else 1)" || exit 1

# Shell-form CMD so ${PORT:-8000} expands at container start. Cloud Run injects
# PORT=8080 (D-23); Fly.io does not inject PORT, so the :-8000 default preserves
# the Fly.io contract (D-25).
CMD uvicorn meshek_ml.service.app:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}
