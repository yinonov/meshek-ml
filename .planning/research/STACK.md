# Stack Research

**Domain:** ML Inference API Service (FastAPI layer over existing LightGBM + PPO pipeline)
**Researched:** 2026-04-10
**Confidence:** HIGH

## Context

This is a SUBSEQUENT MILESTONE stack. The existing Python stack (LightGBM, Stable-Baselines3, Pydantic 2.0, Hydra, Gymnasium, pandas, pyarrow) is already validated and unchanged. This document covers only the NEW additions needed to expose the ML pipeline as a FastAPI inference service consumed by the meshek TypeScript app.

---

## Recommended Stack

### Core Technologies (NEW additions only)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| fastapi | >=0.115 | HTTP API framework | Already installed at 0.135.2; lifespan context manager is the standard pattern for model loading; Pydantic 2.0 native (matches existing schemas); lifespan API replaced deprecated @app.on_event since 0.93 |
| uvicorn[standard] | >=0.30 | ASGI server | Already installed at 0.42.0; since 2024 uvicorn supports --workers N directly, so Gunicorn is no longer needed in containerized single-service deployments |
| sqlmodel | 0.0.38 | ORM for SQLite merchant history storage | Same author as FastAPI; unifies Pydantic 2.0 model and SQLAlchemy table in one class — eliminates the dual-model problem (separate SQLAlchemy table class + Pydantic schema) that raw SQLAlchemy requires |
| aiosqlite | 0.22.1 | Async SQLite driver | Bridges SQLite to asyncio without blocking the event loop; production-stable (Dec 2025); no PostgreSQL needed for a single-process service with one merchant writing at a time |

### Supporting Libraries (NEW additions only)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| joblib | 1.5.3 | Persist and load sklearn-compatible pipeline artifacts | Use ONLY for the feature transformer pipeline object (e.g. a fitted sklearn Pipeline wrapping the feature builder). Do NOT use for the raw LightGBM Booster — use LightGBM native save/load instead to avoid documented prediction inconsistencies |
| python-multipart | >=0.0.9 | Form data parsing | Required by FastAPI when any endpoint accepts file uploads or form fields (e.g. bulk sales data ingestion); technically a FastAPI transitive dep but must be pinned explicitly |
| httpx | >=0.27 | Async HTTP test client | FastAPI's built-in TestClient is synchronous; httpx AsyncClient is the correct test client for async route tests with pytest-asyncio |
| pytest-asyncio | >=0.23 | Async test runner support | Required to run async def test functions; set asyncio_mode = "auto" in pyproject.toml to remove per-test decorator overhead |

**LightGBM serialization note:** Use LightGBM's native `booster.save_model("model.txt")` and `lgb.Booster(model_file="model.txt")` for the Booster object. The native text format is human-readable, version-stable across Colab environments, and avoids prediction inconsistencies that can occur with joblib/pickle serialization of raw Booster objects (documented in LightGBM GitHub issue #5951).

### Hebrew Text Parsing (NEW — zero external dependencies)

No library is needed. The requirement is dictionary-based parsing (explicitly not LLM). The correct implementation is a pure-Python lookup module:

- `data/hebrew_produce.json`: mapping of Hebrew surface forms (including common misspellings and plural variants) to canonical product names matching the existing `product` schema values (e.g., "עגבניות", "מלפפון")
- Normalization via Python's stdlib `unicodedata.normalize("NFD")` for niqqud stripping and whitespace normalization
- `src/meshek_ml/api/hebrew_parser.py`: approximately 60-80 lines, zero runtime dependencies

**Why not hebrew-tokenizer or HebPipe?** HebPipe (updated March 2025) is a full morpho-syntactic pipeline (POS tagging, dependency parsing, coreference) — overkill for a closed-vocabulary lookup of 30-40 produce items. Hebrew-Tokenizer (YontiLevin) is abandoned since 2019. The produce domain is closed-vocabulary; a dictionary is more reliable than a statistical tokenizer and has zero model weight to load.

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Docker | Container packaging for Railway deploy | Use python:3.11-slim base; model weights drive image size, not FastAPI |
| docker-compose | Local development orchestration | One service (the API); mounts ./data volume for SQLite DB and model artifact files |

---

## Installation

Add to `pyproject.toml` as a new optional-dependencies group:

```toml
[project.optional-dependencies]
api = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlmodel>=0.0.38",
    "aiosqlite>=0.22",
    "python-multipart>=0.0.9",
    "joblib>=1.4",
]

api-dev = [
    "meshek-ml[api]",
    "httpx>=0.27",
    "pytest-asyncio>=0.23",
]
```

Install locally:

```bash
pip install -e ".[api-dev,forecasting,optimization]"
```

---

## Architecture Patterns

### Model Loading (lifespan, not @app.on_event)

`@app.on_event("startup")` is deprecated since FastAPI 0.93. Use the lifespan context manager:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import lightgbm as lgb

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load once at startup — LightGBM native text format
    app.state.booster = lgb.Booster(model_file="models/lgb_booster.txt")
    app.state.newsvendor_params = load_newsvendor_params("models/newsvendor.json")
    yield
    # Cleanup: nothing required for in-memory model objects

app = FastAPI(lifespan=lifespan)
```

Access in route handlers via `request.app.state.booster`. This is the FastAPI-official pattern since 0.93.

### Database (SQLModel + aiosqlite)

SQLite is correct for this service. It stores append-heavy merchant sales logs from a single-process service. PostgreSQL adds operational complexity with zero benefit at this scale and concurrency level.

Write concurrency: SQLite uses a database-level write lock. Since this is a single FastAPI process with merchants writing sales sequentially (daily input, not concurrent streams), this is not a problem. If future horizontal scaling requires multiple concurrent writers, enable WAL mode: `PRAGMA journal_mode=WAL`.

Database URL pattern: `sqlite+aiosqlite:///./data/meshek.db`

### Cold-Start Recommendation (no external dep)

Implement as three-tier fallback in `src/meshek_ml/api/recommendation.py`:

1. No stored history — static defaults per product from `data/cold_start_defaults.json`
2. Fewer than 14 days of history — newsvendor formula using empirical mean/std of stored rows
3. 14+ days of history — LightGBM forecast feeding into newsvendor optimization

This maps cleanly to the existing `newsvendor.py` and `pipeline.py` modules without modification.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| SQLModel + aiosqlite | SQLAlchemy Core + aiosqlite directly | When complex joins, raw SQL, or SQLModel Pydantic overhead become measurable in production — unlikely at this scale |
| SQLite | PostgreSQL | When multiple service instances run concurrently (horizontal scaling); not needed for a single-container ML inference service |
| LightGBM native save_model | joblib for Booster | Never for raw Booster; joblib is fine only for sklearn pipeline wrapper objects around the feature transformer |
| Dictionary parser | HebPipe / hebrew-tokenizer | Only if morphological analysis beyond a closed produce vocabulary is required |
| uvicorn --workers N directly | gunicorn + uvicorn workers | Gunicorn remains valid on bare-metal multi-process setups; unnecessary in Docker containers where the container is the process boundary |
| Railway | Fly.io | Fly.io for global edge distribution or if you prefer CLI-first workflow; both are pay-as-you-go (no free tier as of April 2026) |
| Railway | Render | Render is a viable alternative; Railway preferred if meshek app is already there for co-location |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Redis / fastapi-cache | Adds operational complexity; LightGBM inference on CPU is under 100ms for a daily recommendation; overkill for a per-merchant request rate of at most once per day | app.state model cache via lifespan (already in-memory at startup) |
| Celery / task queues | Daily recommendations are triggered on-demand by the meshek app; there is no background scheduling role for meshek-ml | Synchronous POST /recommend endpoint; meshek handles delivery scheduling |
| HebPipe or spaCy Hebrew | Full NLP pipeline for a 30-item closed produce vocabulary adds 500MB+ to the Docker image and model download latency | Pure-Python dictionary in hebrew_parser.py |
| Pydantic v1 compatibility shims | The codebase already uses Pydantic 2.0 throughout; mixing v1 patterns causes silent validation differences | Pydantic 2.0 model syntax throughout the API layer |
| Separate inference and training containers | Over-engineering for v1.1; model retraining is a manual Colab operation, not a live endpoint | Artifacts committed to repo or stored in mounted volume, loaded at startup |
| Gunicorn | Unnecessary in containers since uvicorn added native --workers support; adds config surface for no gain | uvicorn --workers 1 in Dockerfile CMD |
| Multiple uvicorn workers in one container | Each worker independently loads the LightGBM model into RAM; one worker handles concurrent async requests sufficiently for this service | --workers 1; scale horizontally at container level if needed |

---

## Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml .
COPY src/ src/
RUN pip install -e ".[api,forecasting,optimization]" --no-cache-dir

COPY models/ models/
COPY data/ data/

EXPOSE 8000
CMD ["uvicorn", "meshek_ml.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

Single worker: multiple workers each load an independent copy of the LightGBM model. For a daily-recommendation service one async worker handles all concurrent requests.

### Platform: Railway (recommended)

Both Railway and Fly.io are pay-as-you-go with no free tier as of 2025. Railway is recommended for this project because:

- The meshek app (companion TypeScript service) may already be on Railway; co-location reduces network latency for the Fastify to FastAPI call
- Railway's GitHub-triggered deploy and web UI match the project's low-ops philosophy
- Railway's official FastAPI guide confirms Docker + uvicorn as the supported path
- Fly.io's strength is global edge distribution — irrelevant for a single-country (Israel) service

Environment variables needed on Railway: `DATABASE_URL`, `MODEL_PATH`, `LOG_LEVEL`.

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| fastapi>=0.115 | pydantic>=2.0 | FastAPI 0.100+ requires Pydantic v2; already satisfied by existing deps |
| sqlmodel>=0.0.38 | pydantic>=2.0, sqlalchemy>=2.0 | SQLModel 0.0.14+ requires both; aiosqlite is the async driver via sqlite+aiosqlite:/// URL |
| aiosqlite>=0.22 | sqlmodel>=0.0.38 | aiosqlite is the async driver SQLModel uses under the hood for SQLite |
| pytest-asyncio>=0.23 | pytest>=7.4 | Already in dev deps; add asyncio_mode = "auto" to [tool.pytest.ini_options] in pyproject.toml |
| uvicorn[standard] | fastapi>=0.115 | [standard] extra pulls websockets and httptools for full async performance |
| httpx>=0.27 | pytest-asyncio>=0.23 | Use httpx.AsyncClient(app=app, base_url="http://test") as the async test client |

---

## Sources

- [FastAPI Lifespan Events — official docs](https://fastapi.tiangolo.com/advanced/events/) — lifespan pattern and app.state usage (HIGH confidence)
- [FastAPI SQL Databases — official docs](https://fastapi.tiangolo.com/tutorial/sql-databases/) — SQLModel integration pattern (HIGH confidence)
- [SQLModel 0.0.38 — PyPI](https://pypi.org/project/sqlmodel/) — current version verified April 2026
- [aiosqlite 0.22.1 — PyPI](https://pypi.org/project/aiosqlite/) — current version verified April 2026
- [LightGBM Booster API — official docs](https://lightgbm.readthedocs.io/en/latest/pythonapi/lightgbm.Booster.html) — native save_model/load pattern (HIGH confidence)
- [LightGBM joblib vs native prediction inconsistency — GitHub issue #5951](https://github.com/microsoft/LightGBM/issues/5951) — evidence for avoiding joblib on raw Booster (HIGH confidence)
- [joblib 1.5.3 — PyPI](https://pypi.org/project/joblib/) — current version verified April 2026
- [Uvicorn deployment — official docs](https://uvicorn.dev/deployment/) — --workers flag replaces gunicorn in containers (HIGH confidence)
- [Railway FastAPI deploy guide](https://docs.railway.com/guides/fastapi) — Docker + uvicorn confirmed (HIGH confidence)
- [Railway vs Fly comparison — Railway docs](https://docs.railway.com/platform/compare-to-fly) — platform tradeoffs (MEDIUM confidence)
- [awesome-hebrew-nlp — GitHub](https://github.com/iddoberger/awesome-hebrew-nlp) — Hebrew NLP landscape survey; confirmed no lightweight dict-only library exists (MEDIUM confidence)
- [FastAPI 0.135.3 — PyPI](https://pypi.org/project/fastapi/) — current version verified April 2026

---
*Stack research for: meshek-ml v1.1 Merchant Order Advisor — FastAPI inference API layer*
*Researched: 2026-04-10*
