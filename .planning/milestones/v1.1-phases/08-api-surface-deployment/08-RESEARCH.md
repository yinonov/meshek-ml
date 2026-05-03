# Phase 8: API Surface & Deployment - Research

**Researched:** 2026-04-15
**Domain:** FastAPI endpoint wiring, Docker/uv packaging, Fly.io deployment
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** FastAPI + uvicorn[standard] (uvicorn missing from service extra — must add)
- **D-02:** `create_app()` factory in `src/meshek_ml/service/app.py`, consuming `build_lifespan()` from Phase 6
- **D-03:** Entry point `meshek_ml.service.app:create_app`, launched via `--factory` flag
- **D-04:** Routers under `src/meshek_ml/service/routes/{health,merchants,sales,recommend}.py`
- **D-05:** All route handlers are sync `def` (not `async def`) — threadpool execution
- **D-06:** Pydantic v2 schemas in `src/meshek_ml/service/schemas.py`; reuse existing domain models
- **D-07:** POST /merchants: `{merchant_id?: str, display_name?: str}`, server echoes final id
- **D-08:** POST /sales: `{merchant_id, date, items: [...]} | {merchant_id, date, text: "..."}`, partial-success semantics
- **D-09:** POST /recommend: `{merchant_id: str}` → `RecommendationResponse` verbatim
- **D-10:** GET /health: `{status, model_loaded, version}`, 503 if `app.state.ml is None`
- **D-11:** Central exception handler: UnknownMerchantError→404, validation→422, Tier3-no-model→503, else→500+request_id
- **D-12:** Error envelope `{error: {code, message, details?}}`; success = raw pydantic model
- **D-13:** merchant_id validated via `_MERCHANT_ID_PATTERN` (`^[A-Za-z0-9_-]{1,64}$`) pydantic `constr`
- **D-14:** Config via env vars: `MESHEK_MODEL_PATH`, `MESHEK_DATA_DIR`, `MESHEK_API_HOST`, `MESHEK_API_PORT`, `MESHEK_LOG_LEVEL`
- **D-15:** No auth, no CORS in v1.1
- **D-16:** Single-stage Dockerfile, `python:3.12-slim`, uv, installs `service` + runtime extras only
- **D-17:** Image layout: `/app` with WORKDIR, non-root `appuser`, EXPOSE 8000, CMD uvicorn factory
- **D-18:** HEALTHCHECK hits GET /health every 30s
- **D-19:** Model bundle at `/app/models/lightgbm_v1.bundle` (override via `MESHEK_MODEL_PATH`)
- **D-20:** .dockerignore excludes `.venv`, `notebooks/`, `reports/`, `outputs/`, `data/`, `.planning/`, `academic/`, tests, `__pycache__`
- **D-21:** `fly.toml` for Fly.io primary; Railway works with same Dockerfile, no extra config
- **D-22:** No CI/CD pipeline in this phase
- **D-23:** Structured JSON logs to stdout; per-request `{request_id, method, path, status, duration_ms}`
- **D-24:** TestClient integration tests under `tests/service/`
- **D-25:** Docker smoke test `tests/service/test_docker_smoke.py` @pytest.mark.integration, guarded by env flag

### Claude's Discretion

- Exact pydantic field validators / error codes enum values
- Request id generation (uuid4 hex vs ulid)
- Log formatter implementation details
- Whether to factor a small `dependencies.py` for `Depends(get_engine)`
- Minor Dockerfile tweaks for smaller image size

### Deferred Ideas (OUT OF SCOPE)

- Auth / API keys / JWT
- CORS
- CI/CD for Docker image builds
- Prometheus metrics / OpenTelemetry
- POST /retrain/{merchant_id}
- PATCH /merchants/{id}
- Rate limiting
- Multi-arch (linux/arm64) Docker builds
- Schema migration on boot beyond what MerchantStore already handles
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| API-01 | meshek app can check service health via `GET /health` | GET /health endpoint wired to app.state.ml; 503 when model absent |
| API-02 | meshek app can create a new merchant via `POST /merchants` | MerchantStore.create_profile() signature confirmed; auto-id generation pattern documented |
| API-03 | meshek app can submit daily sales records via `POST /sales` | parse_sales_lines() signature confirmed; write_sales DataFrame shape documented |
| API-04 | meshek app can get per-product recommendations via `POST /recommend` | RecommendationEngine.recommend() signature confirmed; error types documented |
| INFRA-02 | Service runs in Docker container deployable to Railway/Fly.io | Dockerfile recipe with uv; fly.toml format confirmed; lightgbm dependency gap identified |
</phase_requirements>

---

## Summary

Phase 8 wires three independently verified subsystems (Phase 6 recommendation engine + lifespan, Phase 7 Hebrew parser, Phase 5 storage) behind four FastAPI endpoints. All upstream contracts are stable and verified — this phase has zero new algorithmic work. The implementation is pure transport + schema + error-mapping.

**The one non-obvious dependency gap:** `lightgbm` is in the `forecasting` extra, not `service`. At runtime, `joblib.load()` deserializes an `LGBMRegressor` object — which requires `lightgbm` to be importable. The Docker image therefore needs a second extra (or `lightgbm` added directly to the `service` extra). CONTEXT.md D-16 references "service + runtime extras" — this aligns with adding a new `runtime` extra to `pyproject.toml` containing `lightgbm>=4.0`. The `service` extra also needs `uvicorn[standard]>=0.44` added (D-01 explicitly flags this as missing).

**Primary recommendation:** Create a minimal `runtime` extra in `pyproject.toml` with `lightgbm>=4.0`, add `uvicorn[standard]>=0.44` to the `service` extra, then build all four endpoints against the verified upstream APIs documented below.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.135.2 (installed); 0.135.3 latest | ASGI framework | Already in service extra; pyproject pins `>=0.135,<0.136` |
| uvicorn[standard] | 0.44.0 (lock); 0.42.0 (venv) | ASGI server | Locked to 0.44.0 in uv.lock; [standard] adds uvloop + httptools for production throughput |
| pydantic | 2.12.5 (installed) | Request/response validation | Core dep; v2 already used throughout |
| httpx | 0.28.1 (installed) | TestClient transport | Already in service extra |
| lightgbm | 4.6.0 (installed) | Deserialize LGBMRegressor via joblib | Needed at inference time; must add to runtime extra |
| joblib | >=1.3 | Model bundle load/save | Already in service extra |

[VERIFIED: pip show fastapi uvicorn httpx pydantic lightgbm joblib]

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uuid (stdlib) | — | request_id generation | Use `uuid.uuid4().hex` for opaque 32-char request ids |
| logging (stdlib) | — | Structured JSON logs to stdout | Custom `JSONFormatter`; no new dep needed |
| pandas | >=2.0 (core dep) | DataFrame for write_sales | Required by MerchantStore.write_sales signature |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| uvicorn[standard] | plain uvicorn | Without httptools/uvloop, no significant throughput benefit; [standard] is negligible extra weight |
| Custom JSONFormatter | python-json-logger | No new dep; stdlib logging + manual dict → json.dumps is sufficient for v1.1 |

**Installation (new additions to pyproject.toml):**

```toml
# In [project.optional-dependencies]:
service = [
    "fastapi>=0.135,<0.136",
    "httpx>=0.27",
    "joblib>=1.3",
    "pyyaml>=6.0",
    "uvicorn[standard]>=0.44",   # ADD: currently missing per D-01
]
runtime = [
    "lightgbm>=4.0",             # ADD: needed for joblib.load(LGBMRegressor)
]
```

Then run `uv lock` to update `uv.lock`.

**Version verification:** [VERIFIED: npm view / pip index versions fastapi 2026-04-15; uvicorn 0.44.0 in uv.lock; lightgbm 4.6.0 from pip show]

---

## Architecture Patterns

### Recommended Project Structure

```
src/meshek_ml/service/
  app.py              # create_app() factory — NEW
  lifespan.py         # build_lifespan() — EXISTS (Phase 6)
  state.py            # AppState — EXISTS (Phase 6)
  schemas.py          # request/response Pydantic models — NEW
  errors.py           # exception → HTTP mapping + JSONFormatter — NEW
  routes/
    __init__.py       # empty — NEW
    health.py         # GET /health — NEW
    merchants.py      # POST /merchants — NEW
    sales.py          # POST /sales — NEW
    recommend.py      # POST /recommend — NEW
Dockerfile            # NEW
.dockerignore         # NEW
fly.toml              # NEW
tests/service/
  __init__.py         # EXISTS
  conftest.py         # EXISTS (has model_bundle_path fixture)
  test_lifespan.py    # EXISTS (Phase 6)
  test_health.py      # NEW
  test_merchants.py   # NEW
  test_sales.py       # NEW
  test_recommend.py   # NEW
  test_errors.py      # NEW
  test_docker_smoke.py # NEW (@pytest.mark.integration, env-guarded)
```

### Pattern 1: create_app() Factory

`create_app()` is the top-level composition root. It instantiates the `RecommendationEngine` and catalog once inside the lifespan, attaches them to `app.state`, and includes all four routers.

```python
# src/meshek_ml/service/app.py
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from meshek_ml.parsing import load_catalog, DEFAULT_CATALOG_PATH
from meshek_ml.recommendation.config import load_category_defaults
from meshek_ml.recommendation.engine import RecommendationEngine
from meshek_ml.recommendation.pooled_store import PooledStore
from meshek_ml.service.errors import register_exception_handlers
from meshek_ml.service.lifespan import build_lifespan
from meshek_ml.service.routes import health, merchants, sales, recommend
from meshek_ml.storage import MerchantStore


def _build_engine_lifespan(app: FastAPI):
    """Wrap Phase 6 lifespan to also attach RecommendationEngine + catalog."""
    phase6_lifespan = build_lifespan()  # resolves MESHEK_MODEL_PATH

    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with phase6_lifespan(app):
            # Phase 6 lifespan has populated app.state.ml at this point.
            ml = app.state.ml  # AppState
            catalog = load_catalog(DEFAULT_CATALOG_PATH)
            category_defaults = load_category_defaults(
                # configs/recommendation/category_defaults.yaml
                ...
            )
            app.state.engine = RecommendationEngine(
                store_factory=lambda mid: MerchantStore(mid, must_exist=True),
                pooled_store=PooledStore(),
                category_defaults=category_defaults,
                model=ml.model if ml else None,
                residual_std=ml.residual_std if ml else 0.0,
                feature_cols=ml.feature_cols if ml else [],
            )
            app.state.catalog = catalog
            yield
            app.state.engine = None
            app.state.catalog = None

    return _lifespan


def create_app() -> FastAPI:
    app = FastAPI(
        title="meshek-ml",
        version="1.1.0",
        lifespan=_build_engine_lifespan,
    )
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(merchants.router)
    app.include_router(sales.router)
    app.include_router(recommend.router)
    return app
```

**Key composition detail:** The inner lifespan wraps Phase 6's `build_lifespan()` using `async with phase6_lifespan(app):`. This ensures the model is loaded before `RecommendationEngine` is instantiated, and ensures teardown order is correct (engine clears before model clears). [VERIFIED: confirmed by reading lifespan.py — it uses `asynccontextmanager` with yield, so nesting is safe]

### Pattern 2: Accessing app.state from Sync Handlers

FastAPI passes the `Request` object when declared as a handler parameter. `request.app.state` is the `app.state` namespace populated by the lifespan.

```python
# src/meshek_ml/service/routes/health.py
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from meshek_ml.service.schemas import HealthResponse

router = APIRouter()


@router.get("/health")
def get_health(request: Request) -> JSONResponse:
    ml = getattr(request.app.state, "ml", None)
    model_loaded = ml is not None
    status_code = 200 if model_loaded else 503
    body = HealthResponse(
        status="ok",
        model_loaded=model_loaded,
        version="1.1.0",
    )
    return JSONResponse(content=body.model_dump(), status_code=status_code)
```

**Sync handlers and app.state:** FastAPI runs `def` (sync) handlers in a threadpool via `anyio.to_thread.run_sync`. `request.app.state` is a `Starlette.State` object — it is thread-safe for reads after the lifespan yield (no mutation during request handling). [VERIFIED: FastAPI docs confirm sync `def` route handlers run in threadpool; app.state is populated at startup before requests arrive]

### Pattern 3: Partial-Success POST /sales

```python
# src/meshek_ml/service/routes/sales.py
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Request
from pydantic import ValidationError

from meshek_ml.parsing import ParsedSale, ParseError, parse_sales_lines
from meshek_ml.service.schemas import SalesRequest, SalesResponse, SkippedLine
from meshek_ml.storage import MerchantStore

router = APIRouter()


@router.post("/sales")
def post_sales(body: SalesRequest, request: Request) -> SalesResponse:
    catalog = request.app.state.catalog

    if body.text is not None:
        # Hebrew free-text path
        lines = [line.strip() for line in body.text.split(",") if line.strip()]
        results = parse_sales_lines(lines, catalog)
        accepted_items = []
        skipped = []
        for result in results:
            if isinstance(result, ParsedSale):
                accepted_items.append(result)
            else:
                skipped.append(SkippedLine(line=result.raw_text, reason=result.kind))
    else:
        # Structured items path
        accepted_items = body.items  # already validated by pydantic
        skipped = []

    if not accepted_items:
        # ALL lines failed — return 422 so the caller knows nothing was stored
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="All sales lines failed to parse")

    rows = [
        {
            "date": body.date,
            "merchant_id": body.merchant_id,
            "product": item.product_id if isinstance(item, ParsedSale) else item.product_id,
            "quantity": item.quantity,
        }
        for item in accepted_items
    ]
    df = pd.DataFrame(rows)

    with MerchantStore(body.merchant_id, must_exist=True) as store:
        n = store.write_sales(df)

    return SalesResponse(accepted_rows=n, skipped=skipped)
```

### Pattern 4: Central Exception Handler

```python
# src/meshek_ml/service/errors.py
from __future__ import annotations

import json
import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from meshek_ml.storage.merchant_store import UnknownMerchantError
from meshek_ml.forecasting.schema import SchemaValidationError

logger = logging.getLogger(__name__)


def _error_response(code: str, message: str, status: int, details=None) -> JSONResponse:
    body = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(content=body, status_code=status)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(UnknownMerchantError)
    async def handle_unknown_merchant(request: Request, exc: UnknownMerchantError):
        return _error_response("merchant_not_found", str(exc), 404)

    @app.exception_handler(ValidationError)
    async def handle_pydantic_validation(request: Request, exc: ValidationError):
        return _error_response("validation_error", "Request validation failed", 422,
                               details=exc.errors())

    @app.exception_handler(SchemaValidationError)
    async def handle_schema_validation(request: Request, exc: SchemaValidationError):
        return _error_response("schema_validation_error", str(exc), 422)

    @app.exception_handler(RuntimeError)
    async def handle_runtime_error(request: Request, exc: RuntimeError):
        # Tier 3 no-model case surfaces as RuntimeError from engine.py:80
        if "Tier 3 requires a loaded model" in str(exc):
            return _error_response("model_unavailable", "ML model not loaded", 503)
        request_id = uuid.uuid4().hex
        logger.error("Unhandled error request_id=%s: %s", request_id, exc, exc_info=True)
        return _error_response("internal_error", "An unexpected error occurred", 500,
                               details={"request_id": request_id})

    @app.exception_handler(Exception)
    async def handle_generic(request: Request, exc: Exception):
        request_id = uuid.uuid4().hex
        logger.error("Unhandled exception request_id=%s", request_id, exc_info=True)
        return _error_response("internal_error", "An unexpected error occurred", 500,
                               details={"request_id": request_id})
```

**Important:** FastAPI exception handlers are `async def` even when the app uses sync routes. This is correct — exception handlers run in the event loop, not the threadpool. [VERIFIED: FastAPI docs; confirmed by Phase 6 test patterns]

### Pattern 5: Pydantic v2 Request/Response Schemas

```python
# src/meshek_ml/service/schemas.py
from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

MerchantIdStr = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")]


class CreateMerchantRequest(BaseModel):
    merchant_id: MerchantIdStr | None = None
    display_name: str | None = None


class SalesItem(BaseModel):
    product_id: str
    quantity: float = Field(gt=0)
    unit: str = "unit"


class SalesRequest(BaseModel):
    merchant_id: MerchantIdStr
    date: date
    items: list[SalesItem] | None = None
    text: str | None = None

    @model_validator(mode="after")
    def exactly_one_of_items_or_text(self) -> "SalesRequest":
        if (self.items is None) == (self.text is None):
            raise ValueError("Exactly one of 'items' or 'text' must be provided")
        return self


class SkippedLine(BaseModel):
    line: str
    reason: str


class SalesResponse(BaseModel):
    accepted_rows: int
    skipped: list[SkippedLine] = Field(default_factory=list)


class RecommendRequest(BaseModel):
    merchant_id: MerchantIdStr


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    model_loaded: bool
    version: str
```

**Pydantic v2 notes:**
- Use `Field(pattern=...)` instead of v1's `constr(regex=...)` — the v1 form still works but emits deprecation warnings in Pydantic v2.12. [VERIFIED: pydantic 2.12.5 installed; v2 API confirmed]
- `@model_validator(mode="after")` is the v2 replacement for `@validator` with `always=True`.
- `Field(gt=0)` is cleaner than `ge=1` for float quantities (allows 0.5 kg).

### Anti-Patterns to Avoid

- **Importing `build_lifespan` multiple times:** Call it once in `create_app()`. Calling it twice creates two independent model-load sequences.
- **Using `app.state.engine` before lifespan yield:** If a route is hit before lifespan completes (rare with TestClient), `getattr(request.app.state, "engine", None)` is safer than direct attribute access.
- **Passing `merchant_id` from request directly to `MerchantStore` without pydantic validation:** D-13 enforces the regex at the Pydantic layer. Do not skip this — it is the path-traversal defense.
- **Async def route handlers:** CONTEXT.md D-05 mandates sync `def`. Using `async def` for CPU/SQLite routes blocks the event loop. [VERIFIED: confirmed pattern in existing tests/service/test_lifespan.py]
- **`model_validator` in mode="before" for the items/text check:** Use `mode="after"` so field defaults are applied first; otherwise `None` vs omitted fields behave differently.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Merchant ID validation | Custom regex in handler | Pydantic `Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")` | Already tested in storage layer; pydantic raises 422 automatically |
| Error envelope serialization | Custom JSONResponse builder per handler | Central `register_exception_handlers()` on the FastAPI app | DRY; catches exceptions from MerchantStore and engine regardless of call depth |
| Partial sales parse tracking | Manual try/except per item | `parse_sales_lines()` returns `list[ParsedSale | ParseError]` — iterate and bucket | Phase 7 already provides the per-line error dataclass |
| Model loading per request | `joblib.load()` in route handler | `app.state.engine` populated by lifespan at startup | Phase 6 lifespan guarantees single load; re-loading would break INFRA-01 |
| DataFrame construction for write_sales | Custom SQL INSERT | `MerchantStore.write_sales(df)` | Handles upsert, schema validation, cross-merchant guard, WAL mode |

**Key insight:** Every hard problem (model loading, Hebrew parsing, SQLite upsert, schema validation) is already solved in upstream phases. Phase 8 is assembly, not construction.

---

## Upstream API Reference (Verified Signatures)

### Phase 6: RecommendationEngine

```python
# src/meshek_ml/recommendation/engine.py
class RecommendationEngine:
    def __init__(
        self,
        *,
        store_factory: Callable[[str], MerchantStore],
        pooled_store: PooledStore,
        category_defaults: CategoryDefaultsConfig,
        model: Any = None,
        residual_std: float = 0.0,
        feature_cols: list[str] | None = None,
    ) -> None: ...

    def recommend(self, merchant_id: str) -> RecommendationResponse:
        # Raises UnknownMerchantError if merchant has no store
        # Raises RuntimeError("Tier 3 requires a loaded model...") if n_days>=14 but model=None
        ...
```

[VERIFIED: read engine.py lines 36-90]

### Phase 6: AppState

```python
# src/meshek_ml/service/state.py
@dataclass
class AppState:
    model: Any
    model_path: Path
    residual_std: float
    feature_cols: list[str]
```

Accessed at `request.app.state.ml`. Is `None` after lifespan teardown. [VERIFIED: read state.py]

### Phase 6: build_lifespan

```python
# src/meshek_ml/service/lifespan.py
def build_lifespan(model_path: Path | None = None) -> Callable:
    # Returns an @asynccontextmanager function
    # Sets app.state.ml = AppState(...) on enter
    # Sets app.state.ml = None on exit
    # Raises RuntimeError("Model file not found...") if file missing at enter
```

[VERIFIED: read lifespan.py lines 44-75]

### Phase 7: Parser

```python
# from meshek_ml.parsing import ...
def parse_sales_line(text: str, catalog: ProductCatalog) -> ParsedSale | ParseError: ...
def parse_sales_lines(lines: list[str], catalog: ProductCatalog) -> list[ParsedSale | ParseError]: ...

@dataclass(frozen=True)
class ParsedSale:
    product_id: str   # canonical slug, e.g. "tomato"
    quantity: float
    unit: Unit        # Unit enum: KG | GRAM | UNIT | CRATE
    raw_text: str

@dataclass(frozen=True)
class ParseError:
    kind: ParseErrorKind  # "empty_input"|"input_too_long"|"unknown_product"|"missing_quantity"|"bad_quantity"|"ambiguous_quantity"
    raw_text: str
    hint: str | None  # Hebrew-language hint, optional

# Catalog loading
from meshek_ml.parsing import load_catalog, DEFAULT_CATALOG_PATH
catalog = load_catalog(DEFAULT_CATALOG_PATH)  # loads from packaged YAML
```

[VERIFIED: read parser.py, catalog.py, __init__.py]

### Phase 5: MerchantStore

```python
# from meshek_ml.storage import MerchantStore, MerchantProfile, UnknownMerchantError

class MerchantStore:
    def __init__(self, merchant_id: str, *, must_exist: bool = False) -> None:
        # must_exist=True raises UnknownMerchantError if no SQLite file exists
        # must_exist=False (default) creates the file

    # Context manager: use as `with MerchantStore(...) as store:`

    def create_profile(self, profile: MerchantProfile) -> MerchantProfile:
        # INSERT; profile.merchant_id must match store.merchant_id

    def get_profile(self) -> Optional[MerchantProfile]: ...

    def write_sales(self, df: pd.DataFrame) -> int:
        # df must have columns: ["date", "merchant_id", "product", "quantity"]
        # date: parseable by pd.Timestamp
        # merchant_id: all rows must match store.merchant_id (cross-merchant guard)
        # product: str (canonical slug after Phase 7 parsing)
        # quantity: float
        # Returns: number of rows written (upsert on date+product PK)
        # Raises SchemaValidationError on bad schema

    def read_sales(self, start=None, end=None) -> pd.DataFrame: ...
```

**write_sales DataFrame shape:**

```python
df = pd.DataFrame({
    "date": [pd.Timestamp("2026-04-14")],   # or ISO string — pd.Timestamp coerces
    "merchant_id": ["shop_a"],               # must match MerchantStore's merchant_id
    "product": ["tomato"],                   # canonical product slug from parser
    "quantity": [20.0],                      # float
})
```

[VERIFIED: read merchant_store.py lines 305-346]

**ParsedSale → DataFrame conversion:**

```python
# In the POST /sales handler, after parse_sales_lines():
rows = [
    {
        "date": body.date.isoformat(),           # date field from request
        "merchant_id": body.merchant_id,
        "product": sale.product_id,              # ParsedSale.product_id
        "quantity": sale.quantity,               # ParsedSale.quantity (float)
    }
    for sale in accepted_sales  # list[ParsedSale]
]
df = pd.DataFrame(rows)
with MerchantStore(body.merchant_id, must_exist=True) as store:
    n = store.write_sales(df)
```

**For the structured items path** (body.items), items are already validated by pydantic (`SalesItem.product_id`, `SalesItem.quantity`). The same DataFrame conversion applies, using `item.product_id` and `item.quantity` directly.

**Important:** `MerchantStore(must_exist=True)` raises `UnknownMerchantError` if the merchant doesn't exist. For POST /sales the merchant must already exist (created via POST /merchants). The central exception handler maps this to 404.

---

## Error → HTTP Mapping

| Exception | HTTP Status | Error Code | Source |
|-----------|-------------|------------|--------|
| `UnknownMerchantError` | 404 | `merchant_not_found` | storage.merchant_store |
| Pydantic `ValidationError` | 422 | `validation_error` | request body parsing |
| `SchemaValidationError` | 422 | `schema_validation_error` | forecasting.schema |
| `RuntimeError("Tier 3 requires...")` | 503 | `model_unavailable` | recommendation.engine:80 |
| `RuntimeError("Model file not found...")` | 500 | `internal_error` | lifespan.py (startup only) |
| All others | 500 | `internal_error` + request_id | catch-all |

**Critical implementation note:** FastAPI's built-in 422 handler fires for request body `ValidationError` before the handler is called. Register a custom `exception_handler(RequestValidationError)` (from `fastapi.exceptions`) in addition to `ValidationError` (pydantic) to ensure the `{error: {...}}` envelope is returned instead of FastAPI's default `{detail: [...]}` format.

```python
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def handle_request_validation(request: Request, exc: RequestValidationError):
    return _error_response("validation_error", "Request validation failed", 422,
                           details=exc.errors())
```

[VERIFIED: FastAPI source — RequestValidationError wraps pydantic ValidationError for request parsing; they are different classes]

---

## Docker with uv

### Verified Dockerfile Recipe

```dockerfile
FROM python:3.12-slim

# Install uv from official image (fastest, no pip, follows uv docs pattern)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency manifests first (layer cache: deps change less often than code)
COPY pyproject.toml uv.lock ./

# Install service + runtime extras only; no dev/simulation/federated/optimization
# --locked: asserts lock file is up-to-date (safer than --frozen for production)
# --no-dev: excludes [dev] optional group
# --extra service --extra runtime: only these two optional groups
RUN uv sync --locked --no-dev --extra service --extra runtime

# Copy source code + static assets
COPY src/ ./src/
COPY configs/ ./configs/
COPY models/ ./models/

# Non-root user (D-17 security)
RUN adduser --system --no-create-home appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENV MESHEK_DATA_DIR=/var/lib/meshek/merchants \
    MESHEK_MODEL_PATH=/app/models/lightgbm_v1.bundle \
    MESHEK_API_HOST=0.0.0.0 \
    MESHEK_API_PORT=8000 \
    MESHEK_LOG_LEVEL=info

CMD [".venv/bin/uvicorn", "meshek_ml.service.app:create_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8000"]
```

[VERIFIED: uv docs https://docs.astral.sh/uv/guides/integration/docker/ — `COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/` is the documented pattern; `--locked` vs `--frozen` confirmed]

**Single-stage vs multi-stage:** CONTEXT.md D-16 chose single-stage. This is correct for this project: the Python source is tiny (no compiled assets), and a multi-stage build would save only the uv binary copy (~30MB) at the cost of complexity. LightGBM pulls in its own `libgomp` (OpenMP), which is needed at runtime anyway.

**Image size considerations:**

Packages NOT installed (because not in service/runtime extras):
- `torch` (~2GB) — optimization extra
- `stable-baselines3` + gymnasium (~500MB) — optimization extra
- `flwr` — federated extra
- `streamlit` (~200MB) — demo extra
- `u8darts` — forecasting extra (heavy; includes Prophet, darts)

Expected image size: ~800MB–1.1GB (python:3.12-slim 150MB + pandas/numpy/scipy ~400MB + lightgbm ~100MB + fastapi/uvicorn ~50MB + source).

**uv virtual environment path:** `uv sync` creates `.venv/` at `WORKDIR`. The CMD uses `.venv/bin/uvicorn` directly. Alternatively, set `PATH="/app/.venv/bin:$PATH"` and use plain `uvicorn`. Both work.

**MESHEK_DATA_DIR requirement:** The MerchantStore hard-fails if `MESHEK_DATA_DIR` is unset (verified: merchant_store.py:99-106). The volume mount for persistent data should be at `/var/lib/meshek/merchants`; this directory must exist before the service starts. Add `RUN mkdir -p /var/lib/meshek/merchants && chown appuser /var/lib/meshek/merchants` before the `USER appuser` instruction.

---

## fly.toml

```toml
# fly.toml — minimal Fly.io config for meshek-ml service
app = "meshek-ml"
primary_region = "ams"  # Amsterdam; closest to Israel for latency

[build]
  dockerfile = "Dockerfile"

[env]
  MESHEK_API_HOST = "0.0.0.0"
  MESHEK_API_PORT = "8000"
  MESHEK_LOG_LEVEL = "info"
  # MESHEK_DATA_DIR and MESHEK_MODEL_PATH set via fly secrets or [mounts]

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 0

[[http_service.checks]]
  grace_period = "15s"
  interval = "30s"
  method = "GET"
  path = "/health"
  timeout = "5s"

[[vm]]
  memory = "512mb"
  cpus = 1

[[mounts]]
  source = "meshek_data"
  destination = "/var/lib/meshek/merchants"
  initial_size = "1gb"
```

[VERIFIED: fly.toml reference https://fly.io/docs/reference/configuration/ — `[[http_service.checks]]`, `[[vm]]`, `[[mounts]]` confirmed syntax]

**Notes:**
- `primary_region = "ams"`: Amsterdam is closest Fly.io region to Israel (TLV not available as of 2026). [ASSUMED]
- `memory = "512mb"`: LightGBM inference on a loaded model is CPU-bound but fast; 512MB is sufficient. 256MB may OOM on pandas DataFrame operations for a merchant with 90 days of history. [ASSUMED — needs validation with real data]
- `[[mounts]]`: Persistent volume for SQLite files. Without this, data is ephemeral and lost on machine restart.
- `auto_stop_machines = "stop"`: Reduces cost for low-traffic periods; machines restart on first request. Adds ~2s cold-start latency.
- `min_machines_running = 0`: Use `1` if the always-on latency SLA matters.
- **Railway fallback:** Same Dockerfile works unchanged. Set env vars `MESHEK_DATA_DIR`, `MESHEK_MODEL_PATH`, `MESHEK_DATA_DIR` via Railway's dashboard. Railway auto-detects `EXPOSE 8000` and routes accordingly.

---

## Testing Strategy

### TestClient Setup

FastAPI `TestClient` (from `starlette.testclient`) uses `httpx` synchronously and triggers the lifespan on entry. This is already the established pattern in Phase 6.

```python
# tests/service/conftest.py (additions needed alongside existing Phase 6 fixtures)
import os
import pytest
from fastapi.testclient import TestClient
from meshek_ml.service.app import create_app
from meshek_ml.recommendation.training import train_and_save
from meshek_ml.simulation.generator import run_simulation


@pytest.fixture(scope="session")
def model_bundle_path(tmp_path_factory):
    """Reuse existing Phase 6 fixture — already in tests/service/conftest.py"""
    # ... (already exists)


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Temporary MESHEK_DATA_DIR for isolation between tests."""
    d = tmp_path / "merchants"
    d.mkdir()
    monkeypatch.setenv("MESHEK_DATA_DIR", str(d))
    return d


@pytest.fixture
def app_client(model_bundle_path, data_dir, monkeypatch):
    """A TestClient wrapping a fully initialized create_app() instance."""
    monkeypatch.setenv("MESHEK_MODEL_PATH", str(model_bundle_path))
    monkeypatch.setenv("MESHEK_MODELS_DIR", str(model_bundle_path.parent))
    app = create_app()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def no_model_client(data_dir, monkeypatch, tmp_path):
    """TestClient where the model file does not exist — for 503 testing."""
    monkeypatch.setenv("MESHEK_MODEL_PATH", str(tmp_path / "missing.bundle"))
    monkeypatch.setenv("MESHEK_MODELS_DIR", str(tmp_path))
    # The lifespan will raise RuntimeError on startup.
    # TestClient wraps this — but the app starts and health returns 503.
    # Actually: build_lifespan raises at enter if file missing.
    # Need a different approach: monkeypatch build_lifespan to NOT raise,
    # but leave app.state.ml = None.
    ...
```

**Testing the 503-when-model-missing case:**

The 503 case for `/health` requires `app.state.ml is None`. This is tricky because `build_lifespan` raises `RuntimeError` if the model file doesn't exist — it never yields with `ml = None`. Two approaches:

1. **Monkeypatch `build_lifespan`** to yield without setting `app.state.ml`:
   ```python
   from contextlib import asynccontextmanager
   @asynccontextmanager
   async def null_lifespan(app):
       app.state.ml = None
       yield
   monkeypatch.setattr("meshek_ml.service.app.build_lifespan", lambda: null_lifespan)
   ```

2. **Monkeypatch `load_model_bundle`** to raise `FileNotFoundError` and catch it in the lifespan rather than letting it propagate. However, the current `build_lifespan` raises `RuntimeError` before calling `load_model_bundle` if the file doesn't exist.

**Recommended approach:** In `create_app()`'s `_build_engine_lifespan`, catch `RuntimeError` from the Phase 6 lifespan and set `app.state.ml = None` rather than re-raising, allowing the service to start in a degraded state where `/health` returns 503 but other endpoints still work for Tier 1/2. This aligns better with the 503 design in D-10. Alternatively, start the app with a placeholder model file that exists on disk but has no valid LightGBM content — `get_health` will detect `app.state.ml is None` if the lifespan failed to populate it.

The cleanest testable design: **`create_app()` catches the model-load failure and logs a warning rather than crashing**, so `app.state.ml` can be `None` at startup. Health returns 503. Tier 1/2 recommendations still work.

[ASSUMED — this is a design choice not explicitly stated in CONTEXT.md; the planner should decide]

### Docker Smoke Test Pattern

```python
# tests/service/test_docker_smoke.py
import os
import subprocess
import time
import pytest
import urllib.request


SMOKE_TEST_ENABLED = os.environ.get("MESHEK_DOCKER_SMOKE", "").lower() in ("1", "true", "yes")


@pytest.mark.integration
@pytest.mark.skipif(not SMOKE_TEST_ENABLED, reason="Set MESHEK_DOCKER_SMOKE=1 to run")
def test_docker_health_endpoint():
    """Build the image and verify /health returns 200."""
    image_tag = "meshek-ml-smoke:test"
    subprocess.run(["docker", "build", "-t", image_tag, "."], check=True, timeout=300)
    container_id = subprocess.check_output([
        "docker", "run", "-d",
        "-p", "18000:8000",
        "-e", "MESHEK_DATA_DIR=/tmp/merchants",
        image_tag,
    ]).strip().decode()
    try:
        time.sleep(5)  # Allow startup
        with urllib.request.urlopen("http://localhost:18000/health", timeout=5) as r:
            assert r.status in (200, 503)  # 503 OK if no model baked in
    finally:
        subprocess.run(["docker", "rm", "-f", container_id], check=True)
```

**Guard by env flag** (`MESHEK_DOCKER_SMOKE=1`) so it doesn't run in normal `pytest` invocations. Requires Docker to be running (`docker --version` confirmed available). [VERIFIED: Docker 29.2.1 available]

### Test Coverage Map

| Req ID | Behavior | Test File | Test Name Pattern | Type |
|--------|----------|-----------|-------------------|------|
| API-01 | GET /health → 200 + model_loaded=true | test_health.py | test_health_with_model | integration |
| API-01 | GET /health → 503 + model_loaded=false | test_health.py | test_health_without_model | integration |
| API-02 | POST /merchants auto-id | test_merchants.py | test_create_merchant_auto_id | integration |
| API-02 | POST /merchants explicit id | test_merchants.py | test_create_merchant_explicit_id | integration |
| API-02 | POST /merchants invalid id → 422 | test_merchants.py | test_create_merchant_invalid_id | integration |
| API-03 | POST /sales structured items | test_sales.py | test_sales_structured_items | integration |
| API-03 | POST /sales Hebrew free text | test_sales.py | test_sales_hebrew_text | integration |
| API-03 | POST /sales partial parse failure | test_sales.py | test_sales_partial_skipped | integration |
| API-03 | POST /sales unknown merchant → 404 | test_sales.py | test_sales_unknown_merchant | integration |
| API-04 | POST /recommend Tier 1 (0 days) | test_recommend.py | test_recommend_tier1 | integration |
| API-04 | POST /recommend Tier 3 (14+ days) | test_recommend.py | test_recommend_tier3 | integration |
| API-04 | POST /recommend 503 no model | test_recommend.py | test_recommend_503_no_model | integration |
| INFRA-02 | Docker image starts, /health responds | test_docker_smoke.py | test_docker_health_endpoint | integration (MESHEK_DOCKER_SMOKE=1) |
| D-12 | Error envelope shape | test_errors.py | test_404_envelope, test_422_envelope, test_503_envelope | integration |

---

## Common Pitfalls

### Pitfall 1: lifespan composition order matters

**What goes wrong:** If `RecommendationEngine` is instantiated outside the Phase 6 lifespan context, `app.state.ml` will be `None` because the model hasn't loaded yet.
**Why it happens:** Python's `contextlib.asynccontextmanager` nesting requires careful attention to when code runs relative to the `yield`.
**How to avoid:** Use `async with phase6_lifespan(app): # app.state.ml is set here` and build the engine inside that `async with` block, after the nested `yield`.
**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'model'` in `RecommendationEngine.__init__` or Tier 3.

### Pitfall 2: RequestValidationError vs ValidationError

**What goes wrong:** Registering only `pydantic.ValidationError` as an exception handler doesn't catch FastAPI's automatic 422 for invalid request bodies — those surface as `fastapi.exceptions.RequestValidationError`.
**Why it happens:** FastAPI wraps pydantic validation errors in `RequestValidationError` before they reach the exception handler.
**How to avoid:** Register both `exception_handler(RequestValidationError)` AND `exception_handler(ValidationError)`.
**Warning signs:** `{"detail": [{"type": "...", "loc": [...]}]}` response format instead of `{"error": {...}}` envelope.

### Pitfall 3: MESHEK_DATA_DIR not set → MerchantStoreError at startup

**What goes wrong:** `get_data_root()` raises `MerchantStoreError("MESHEK_DATA_DIR must be set...")` immediately on import if the env var is unset.
**Why it happens:** `_data_root()` in `merchant_store.py:99-106` is called eagerly in `PooledStore` during startup.
**How to avoid:** Ensure `MESHEK_DATA_DIR` is set in the container CMD or `fly.toml [env]` before the lifespan runs. In tests: `monkeypatch.setenv("MESHEK_DATA_DIR", str(tmp_path))` in the `data_dir` fixture.
**Warning signs:** `MerchantStoreError: MESHEK_DATA_DIR must be set` in container logs before any request.

### Pitfall 4: uvicorn --factory with async vs sync create_app

**What goes wrong:** If `create_app` is `async def`, uvicorn's `--factory` flag won't call it correctly.
**Why it happens:** uvicorn `--factory` expects the factory to be a regular sync callable that returns the ASGI app.
**How to avoid:** `create_app()` must be a plain `def`, not `async def`. [VERIFIED: uvicorn docs confirm --factory expects a sync callable]

### Pitfall 5: pydantic v2 Field(pattern=...) vs constr

**What goes wrong:** Using `from pydantic import constr; MerchantIdStr = constr(regex=r"...")` works but emits `PydanticDeprecatedSince20` warnings.
**Why it happens:** Pydantic v2 replaced `constr` with `Annotated[str, Field(pattern=...)]`.
**How to avoid:** Use `Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")]` instead. [VERIFIED: pydantic 2.12.5 installed; v2 API confirmed]

### Pitfall 6: Unit enum serialization in SalesResponse

**What goes wrong:** `ParsedSale.unit` is a `Unit` enum. When building the DataFrame or the JSON response, `.value` must be called to get the string (`"kg"`, `"unit"`, etc.).
**Why it happens:** Pydantic v2 serializes enum members by value by default, but pandas `.DataFrame()` stores enum objects if not converted.
**How to avoid:** Use `sale.unit.value` when building the DataFrame's `product` column, or ensure the `SalesItem.unit` field is `str`, not `Unit`.

### Pitfall 7: TestClient lifespan and session-scoped model fixture

**What goes wrong:** Using a session-scoped `model_bundle_path` fixture with a function-scoped `TestClient` causes the lifespan to fire on every test, which is expensive (51 existing service tests already do this carefully).
**Why it happens:** `TestClient(app)` triggers lifespan enter/exit in the `with` block.
**How to avoid:** Make the `app_client` fixture `scope="module"` or `scope="session"` if tests in a module share the same merchant state. For tests that mutate state (merchant creation, sales writes), use function scope with a fresh `data_dir`.

### Pitfall 8: uv sync --locked fails if pyproject.toml changes are not reflected in uv.lock

**What goes wrong:** Adding `uvicorn[standard]>=0.44` and `runtime = ["lightgbm>=4.0"]` to `pyproject.toml` without running `uv lock` first causes `uv sync --locked` in the Dockerfile to fail with "lock file is out of date".
**Why it happens:** `--locked` asserts the lock is consistent; the Dockerfile bakes in `uv.lock` from the repo.
**How to avoid:** Always run `uv lock` after `pyproject.toml` changes and commit the updated `uv.lock` before building the Docker image.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup")` | `FastAPI(lifespan=...)` | FastAPI 0.93 | Old events deprecated; lifespan is the v2 pattern |
| `pydantic.constr(regex=...)` | `Annotated[str, Field(pattern=...)]` | Pydantic v2 (2.0) | constr still works but deprecated |
| `@validator` | `@field_validator` / `@model_validator` | Pydantic v2 | Old decorators deprecated |
| `uvicorn app:app` (module-level app) | `uvicorn app:create_app --factory` | uvicorn 0.20+ | Factory pattern enables TestClient lifespan |

---

## Validation Architecture

> nyquist_validation: true (from .planning/config.json)

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.4+ (installed) |
| Config file | `pyproject.toml` [tool.pytest.ini_options] — testpaths=["tests"], markers registered |
| Quick run command | `.venv/bin/python -m pytest tests/service/ -q --no-cov -m "not integration"` |
| Full suite command | `.venv/bin/python -m pytest tests/service/ -q --no-cov` |
| Docker smoke | `MESHEK_DOCKER_SMOKE=1 .venv/bin/python -m pytest tests/service/test_docker_smoke.py -m integration` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| API-01 | GET /health 200 when model loaded | integration | `pytest tests/service/test_health.py::test_health_with_model` | ❌ Wave 0 |
| API-01 | GET /health 503 when model absent | integration | `pytest tests/service/test_health.py::test_health_without_model` | ❌ Wave 0 |
| API-02 | POST /merchants creates with auto-id | integration | `pytest tests/service/test_merchants.py::test_create_auto_id` | ❌ Wave 0 |
| API-02 | POST /merchants explicit id roundtrip | integration | `pytest tests/service/test_merchants.py::test_create_explicit_id` | ❌ Wave 0 |
| API-03 | POST /sales structured items stored | integration | `pytest tests/service/test_sales.py::test_sales_structured` | ❌ Wave 0 |
| API-03 | POST /sales Hebrew text parsed+stored | integration | `pytest tests/service/test_sales.py::test_sales_hebrew_text` | ❌ Wave 0 |
| API-03 | POST /sales partial parse → skipped list | integration | `pytest tests/service/test_sales.py::test_sales_partial_skipped` | ❌ Wave 0 |
| API-04 | POST /recommend returns RecommendationResponse | integration | `pytest tests/service/test_recommend.py::test_recommend_tier1` | ❌ Wave 0 |
| API-04 | POST /recommend 503 when no model | integration | `pytest tests/service/test_recommend.py::test_recommend_no_model` | ❌ Wave 0 |
| INFRA-02 | Docker image starts, /health responds | integration | `MESHEK_DOCKER_SMOKE=1 pytest tests/service/test_docker_smoke.py` | ❌ Wave 0 |
| D-12 | Error envelopes match `{error:{code,message,details?}}` | integration | `pytest tests/service/test_errors.py` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/service/ -q --no-cov -m "not integration"` (schema/unit tests only)
- **Per wave merge:** `.venv/bin/python -m pytest tests/service/ -q --no-cov` (all service tests including integration)
- **Phase gate:** Full suite green (`pytest tests/ -q --no-cov`) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/service/test_health.py` — covers API-01 (200 + 503)
- [ ] `tests/service/test_merchants.py` — covers API-02
- [ ] `tests/service/test_sales.py` — covers API-03 (structured + Hebrew + partial)
- [ ] `tests/service/test_recommend.py` — covers API-04 (Tier 1, Tier 3, 503)
- [ ] `tests/service/test_errors.py` — covers D-12 error envelope contract
- [ ] `tests/service/test_docker_smoke.py` — covers INFRA-02 (env-guarded)
- [ ] Extend `tests/service/conftest.py` with `data_dir`, `app_client`, `no_model_client` fixtures

*(Existing `test_lifespan.py` and `conftest.py` are in place from Phase 6 — no regressions expected.)*

---

## Security Domain

> security_enforcement: not explicitly set → treated as enabled

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth in v1.1 (D-15); private network only |
| V3 Session Management | No | Stateless REST; no sessions |
| V4 Access Control | No | No roles; sole caller is meshek app in private network |
| V5 Input Validation | Yes | Pydantic `Field(pattern=...)` on merchant_id; pydantic validates all request bodies |
| V6 Cryptography | No | No encryption; no secrets at this layer |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via merchant_id | Tampering | `Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")` at pydantic layer; `_validate_merchant_id()` + `Path.resolve()` parent check in storage layer (defense-in-depth, T-5-01) |
| Oversized free-text input (DoS) | DoS | `parse_sales_line` caps input at 2048 chars (`_MAX_INPUT_CHARS = 2048`, MD-02 in parser.py:63) |
| Stack trace leakage | Information Disclosure | Generic 500 handler returns only `request_id`; stack trace logged server-side only |
| YAML injection via catalog | Tampering | `yaml.safe_load` only (T-7-03 in catalog.py); catalog is a package asset, not user input |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | INFRA-02 smoke test, image build | ✓ | 29.2.1 | — |
| flyctl | fly.toml deployment | ✗ | — | Install: `brew install flyctl` or `curl -L https://fly.io/install.sh | sh` |
| uv | Dockerfile build, lock update | ✓ | 0.8.22 | — |
| Python 3.12 | Dockerfile base image | ✓ (host: 3.13) | 3.12 in Docker | — |

**Missing dependencies with no fallback:**
- flyctl: required to deploy to Fly.io; not needed for local dev or Docker build; install before deployment step.

**Missing dependencies with fallback:**
- None blocking for development or testing.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `primary_region = "ams"` is closest Fly.io region to Israel | fly.toml | Higher latency; change to `fra` (Frankfurt) if latency matters |
| A2 | 512MB VM memory is sufficient for LightGBM inference with real merchant data | fly.toml | OOM on large DataFrames; upgrade to 1GB |
| A3 | The 503 design for GET /health when model absent requires `create_app()` to NOT raise on model-load failure | Testing Strategy | If lifespan raises on startup (current Phase 6 behavior), the container crashes rather than starting in degraded mode; planner must decide between crash-fast and degrade-gracefully |
| A4 | `parse_sales_lines()` can be called with comma-split lines from the free-text body | Pattern 3 | If merchants use newlines or semicolons as separators, splitting on comma will produce wrong parse results; needs confirmation of the real WhatsApp input format |

**A3 is the most important assumption.** The CONTEXT.md says "GET /health returns 503 if model missing" — this implies the service starts without a model. But the current `build_lifespan` raises `RuntimeError` at startup if the model file is absent. The planner must decide: either (1) change `build_lifespan` to not raise (set `app.state.ml = None` and log a warning), or (2) keep crash-fast and document that the 503 health case is only reachable via monkeypatching in tests. Option 1 is more testable and aligns with D-10's intent.

---

## Open Questions

1. **Should `create_app()` tolerate a missing model file at startup?**
   - What we know: `build_lifespan` currently raises `RuntimeError` if model file absent. D-10 says health returns 503 when model missing.
   - What's unclear: Does "503 when model missing" mean (a) service starts without model + returns 503, or (b) is only a test-time scenario via monkeypatching?
   - Recommendation: Implement option (a) — catch the `RuntimeError` from `build_lifespan` in `_build_engine_lifespan`, set `app.state.ml = None`, log a warning. This matches D-10 literally and is easier to test.

2. **What is the line delimiter for POST /sales `text` field?**
   - What we know: CONTEXT.md D-08 shows `"20 עגבניות, 5 מלפפונים"` as a free-text example. D-14 in Phase 7 says "caller splits lines before calling parse_sales_line".
   - What's unclear: Is comma the canonical delimiter? Could be newline from multi-line WhatsApp message.
   - Recommendation: Support both comma and newline as delimiters: `re.split(r"[,\n]+", text)`. Low risk.

**No blockers.** Both questions have clear recommended resolutions that the planner can adopt without user input.

---

## Sources

### Primary (HIGH confidence)

- `src/meshek_ml/service/lifespan.py` — `build_lifespan` signature, AppState population, teardown behavior
- `src/meshek_ml/service/state.py` — AppState fields
- `src/meshek_ml/recommendation/engine.py` — `RecommendationEngine` constructor and `recommend()` signature + error types
- `src/meshek_ml/recommendation/schema.py` — `RecommendationResponse`, `ProductRecommendation` fields
- `src/meshek_ml/storage/merchant_store.py` — `MerchantStore`, `write_sales` DataFrame shape, error hierarchy
- `src/meshek_ml/parsing/parser.py` — `parse_sales_line`, `ParsedSale`, `ParseError`, `ParseErrorKind`
- `src/meshek_ml/parsing/catalog.py` — `ProductCatalog`, `load_catalog`, `DEFAULT_CATALOG_PATH`
- `src/meshek_ml/parsing/__init__.py` — public API surface (11 exported symbols)
- `pyproject.toml` — extras layout, service extra contents, missing uvicorn
- `uv.lock` — uvicorn 0.44.0 locked, uvicorn[standard] extras confirmed
- `tests/service/conftest.py` — existing `model_bundle_path` session fixture pattern
- `tests/service/test_lifespan.py` — existing TestClient patterns for Phase 6

### Secondary (MEDIUM confidence)

- https://docs.astral.sh/uv/guides/integration/docker/ — `COPY --from=ghcr.io/astral-sh/uv:latest`, `--locked` flag
- https://fly.io/docs/reference/configuration/ — `[[http_service.checks]]`, `[[vm]]`, `[[mounts]]` syntax
- https://fastapi.tiangolo.com/advanced/events/ — lifespan async context manager pattern

### Tertiary (LOW confidence)

- Regional latency claim (A1): `primary_region = "ams"` — not benchmarked; general knowledge

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all packages verified via pip show + uv.lock
- Architecture patterns: HIGH — derived directly from reading upstream source code
- Error → HTTP mapping: HIGH — exception types read directly from source files
- Docker/uv recipe: HIGH — uv docs fetched and verified
- fly.toml syntax: HIGH — Fly.io docs fetched and verified
- Image size estimate: MEDIUM — calculated from known package sizes; not built
- Testing strategy: HIGH — follows existing Phase 6 TestClient patterns
- Pitfalls: HIGH — derived from reading actual source code + pydantic v2 docs

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (stable ecosystem; uvicorn/fastapi patch versions may change)
