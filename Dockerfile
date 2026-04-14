FROM python:3.12-slim

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install only service + runtime extras (no dev, no simulation, no federated, no torch)
RUN uv sync --locked --no-dev --extra service --extra runtime

# Copy application source
COPY src/ ./src/
COPY configs/ ./configs/

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

CMD ["uvicorn", "meshek_ml.service.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
