# Architecture Research

**Domain:** ML inference service integrated into a TypeScript monorepo via HTTP
**Researched:** 2026-04-10
**Confidence:** HIGH — based on direct inspection of both codebases (meshek-ml and meshek)

## Standard Architecture

### System Overview

```
┌──────────────────────────── meshek (TypeScript monorepo) ────────────────────────────┐
│                                                                                        │
│  ┌──────────────────────┐    ┌───────────────────────────────────────────────────┐   │
│  │  packages/dashboard  │    │             packages/api                          │   │
│  │  React 19 + Vite     │    │   Fastify 5 + Drizzle/PostgreSQL                  │   │
│  │  order queue         │    │   /routes/whatsapp (existing)                     │   │
│  │  catalog, insights   │    │   /routes/orders   (existing)                     │   │
│  └──────────────────────┘    │   /services/llm-client.ts  (existing)             │   │
│                              │   /services/ml-client.ts   (NEW — mirrors above)  │   │
│                              └──────────────────┬────────────────────────────────┘   │
│                                                 │                                     │
└─────────────────────────────────────────────────┼─────────────────────────────────────┘
                                                  │  HTTP POST  (ML_ENGINE_URL env var)
                                                  │
┌──────────────────────────── meshek-ml (Python service) ──────────────────────────────┐
│                                                 ▼                                     │
│  ┌────────────────────────────────────────────────────────────────────────────────┐  │
│  │                    services/api/  (NEW in this milestone)                      │  │
│  │   main.py  — FastAPI app                                                       │  │
│  │     GET  /health                                                               │  │
│  │     POST /recommend    ← primary endpoint                                      │  │
│  │     POST /sales        ← sales ingestion from meshek                          │  │
│  └──────────────┬────────────────────────────────────────────┬────────────────────┘  │
│                 │                                            │                        │
│  ┌──────────────▼──────────────────────────┐  ┌────────────▼──────────────────────┐ │
│  │  recommendation_engine.py               │  │  sales_store.py                   │ │
│  │  cold_start_router()                    │  │  SQLite, one file per merchant    │ │
│  │    < 30d  → product defaults            │  │  insert(merchant, product, date,  │ │
│  │    30-89d → newsvendor(mean, std)       │  │          quantity)                │ │
│  │    90d+   → lgbm + newsvendor           │  │  history_length(merchant,product) │ │
│  └──────────────┬──────────────────────────┘  │  get_history(merchant, product)   │ │
│                 │                              └───────────────────────────────────┘ │
│  ┌──────────────▼──────────────────────────────────────────────────────────────────┐ │
│  │              Existing src/meshek_ml/ modules (unchanged)                        │ │
│  │   forecasting/pipeline.py  → run_forecast_pipeline()                            │ │
│  │   forecasting/schema.py    → validate_demand_schema()                            │ │
│  │   optimization/newsvendor.py → optimal_order_normal()                            │ │
│  │   common/types.py, common/seed.py                                                │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                       │
│  data/sales/{merchant_id}.db          (SQLite, one file per merchant, gitignored)    │
│  models/forecasting/{merchant_id}.lgbm (serialized LightGBM, updated offline)       │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `packages/api/services/ml-client.ts` | HTTP calls to `/recommend` and `/sales` with typed responses | New in meshek — mirrors `llm-client.ts` exactly: fetch, auth headers, error handling |
| `packages/api/config.ts` | `mlEngineUrl` + `validateProductionEnv()` entry | Extend existing config, add `ML_ENGINE_URL` env var |
| `services/api/main.py` | FastAPI app with `/health`, `/recommend`, `/sales` | New in meshek-ml |
| `services/api/recommendation_engine.py` | Cold-start routing → newsvendor → LightGBM | New in meshek-ml, imports existing `run_forecast_pipeline` and `optimal_order_normal` |
| `services/api/sales_store.py` | Persist and query per-merchant daily sales in SQLite | New in meshek-ml |
| `services/api/schemas.py` | Pydantic request/response models | New in meshek-ml — the API contract |
| `src/meshek_ml/forecasting/pipeline.py` | Existing: validate → features → train → predict | Unchanged |
| `src/meshek_ml/optimization/newsvendor.py` | Existing: `optimal_order_normal()` | Unchanged |

## Recommended Project Structure

```
meshek-ml/
├── src/meshek_ml/              # existing ML library — unchanged
│   ├── forecasting/
│   ├── optimization/
│   ├── simulation/
│   ├── federated/
│   └── common/
├── services/
│   └── api/                    # NEW — FastAPI inference service
│       ├── Dockerfile           # mirrors services/llm-engine/Dockerfile in meshek repo
│       ├── requirements.txt     # fastapi, uvicorn, python-dotenv + meshek-ml deps
│       ├── src/
│       │   ├── __init__.py
│       │   ├── main.py          # FastAPI app, routes, exception handler
│       │   ├── schemas.py       # Pydantic request/response models (the contract)
│       │   ├── recommendation_engine.py  # cold-start router + pipeline orchestration
│       │   ├── sales_store.py   # SQLite persistence layer
│       │   ├── hebrew_parser.py # dictionary-based Hebrew text → {product, quantity}
│       │   └── config.py        # DATA_DIR, MODEL_DIR, ENV env vars
│       └── tests/
│           ├── __init__.py
│           └── test_recommendation_engine.py
├── data/
│   └── sales/                  # gitignored — SQLite files written at runtime
│       └── {merchant_id}.db
├── models/
│   └── forecasting/            # gitignored — serialized LightGBM files
│       └── {merchant_id}.lgbm
└── pyproject.toml              # add [api] optional extra: fastapi, uvicorn, python-dotenv
```

### Structure Rationale

- **services/api/ mirrors services/llm-engine/ in the meshek repo.** Same layout (Dockerfile, requirements.txt, src/, tests/). Both teams follow identical patterns; zero new operational conventions to learn.
- **src/meshek_ml/ is untouched.** The API layer is a consumer of the library, not part of it. This preserves the Colab research workflow and means the API adds no risk to existing tests.
- **data/ and models/ are runtime dirs, not in git.** Injected via `DATA_DIR` / `MODEL_DIR` env vars in `config.py`; defaults to `./data/sales` and `./models/forecasting` for local dev.

## Architectural Patterns

### Pattern 1: Cold-Start Router (Progressive Enrichment)

**What:** A single function selects the recommendation strategy based on how many days of sales history exist for a given merchant-product pair. No data → safe category defaults. Thin data → newsvendor from historical mean/std. Rich data → LightGBM + newsvendor.

**When to use:** Every `/recommend` request routes through this function.

**Trade-offs:** Each tier is independently testable. Boundary conditions (29→30 days, 89→90 days) need explicit coverage. The LightGBM tier will produce worse results than newsvendor if history is noisy at exactly 90 days — the thresholds are conservative on purpose.

**Thresholds rationale:** `run_forecast_pipeline()` uses 14-day lag features and 7-day rolling windows; 90 days gives enough warm-up rows after NaN-dropping. 30 days gives enough history for a meaningful mean and standard deviation for newsvendor.

```python
def route_recommendation(merchant_id: str, product: str, store: SalesStore) -> RecommendResult:
    days = store.history_length(merchant_id, product)
    if days < 30:
        return cold_start_defaults(product)        # hardcoded safe quantities by category
    history_df = store.get_history(merchant_id, product)
    if days < 90:
        return newsvendor_from_history(history_df)  # optimal_order_normal(mean, std, costs)
    return lgbm_pipeline_recommend(history_df, merchant_id, product)
```

### Pattern 2: Data Ownership — meshek-ml Owns Sales History

**What:** meshek pushes individual daily sales observations to meshek-ml via `POST /sales`. meshek-ml persists them in SQLite, keyed by merchant_id and product. meshek never stores sales history in its PostgreSQL schema.

**When to use:** Every time a merchant reports sales via WhatsApp ("מכרתי 40 עגבניות"), meshek parses the message through the existing llm-engine, then forwards the result to meshek-ml's `/sales` endpoint.

**Trade-offs:** Correct separation — ML data and order management data stay in their respective stores. SQLite is adequate (hundreds of rows/year per product per merchant). The downside is meshek cannot independently query sales history without calling the ML service.

**Why not pass full history per /recommend call:** History grows unboundedly. Serializing and sending 365+ days × 8+ products on every WhatsApp recommendation request is wasteful, slow, and creates versioning surface on the caller side.

**Why not store history in meshek's PostgreSQL:** Avoids dual ownership of the same data across two ORMs in two languages. Sales history feeds ML pipelines — not order management — so it belongs with the ML service.

### Pattern 3: Service Auth Mirrors llm-engine

**What:** In production (Cloud Run), meshek fetches a Google Cloud Run identity token and sends it as `Authorization: Bearer <token>` on every request to meshek-ml. In development, no auth header is sent. meshek-ml's Cloud Run service validates the token automatically.

**When to use:** Copy `getAuthHeaders()` and `fetchIdentityToken()` from the existing `llm-client.ts` into the new `ml-client.ts` verbatim. The only change is replacing `llmEngineUrl` with `mlEngineUrl`.

**Trade-offs:** Zero new infrastructure. No API key management. Works identically to the already-deployed llm-engine auth flow.

### Pattern 4: Offline Training, Online Inference Only

**What:** The FastAPI service never runs `model.fit()` or `run_forecast_pipeline()` in training mode. Models are trained offline (Colab or future cron job), serialized to `models/forecasting/{merchant_id}.lgbm`, and loaded at startup or lazily on first request. Replacing the file is sufficient to update a model.

**When to use:** Always in v1.1. Do not add a `POST /train` endpoint.

**Trade-offs:** Simple inference service with predictable latency. The operational burden is manually triggering Colab retraining when data volume warrants it. This is acceptable for v1.1 scale (handful of merchants).

## Data Flow

### Recommendation Request Flow

```
WhatsApp: "מה להזמין מחר?"
    ↓
meshek: Fastify routes/recommendations.ts
    ↓  POST {ML_ENGINE_URL}/recommend
       body: { merchant_id, product, target_date, cost_params? }
meshek-ml: FastAPI /recommend
    ↓
sales_store.history_length(merchant_id, product)
    ↓ cold-start router
    ├─ <30d:  cold_start_defaults(product)           → { quantity: N, strategy: "defaults" }
    ├─ 30-89d: newsvendor_from_history(df)            → { quantity: N, strategy: "newsvendor" }
    └─ 90d+:   lgbm_pipeline_recommend(df, ...)       → { quantity: N, strategy: "lgbm_newsvendor" }
    ↓
RecommendResponse: { product, recommended_quantity, strategy, confidence, history_days }
    ↓
meshek: formats Hebrew WhatsApp message, sends via WhatsApp Cloud API
```

### Sales Ingestion Flow

```
WhatsApp: "מכרתי 40 עגבניות"
    ↓
meshek: existing llm-engine /process parses → { product: "עגבניות", quantity: 40 }
    ↓
meshek: Fastify WhatsApp handler (or dedicated sales route)
    ↓  POST {ML_ENGINE_URL}/sales
       body: { merchant_id, product, date, quantity }
meshek-ml: FastAPI /sales
    ↓
sales_store.insert(merchant_id, product, date, quantity)
    ↓
200 OK  { status: "ok" }
```

### Key Data Flows

1. **Recommendation:** meshek requests → meshek-ml reads its own SQLite → returns a quantity integer and strategy label. meshek never interprets the ML logic.
2. **Sales ingestion:** meshek pushes one observation per WhatsApp sales message. One-directional write; no polling; fire-and-forget acceptable (failures logged, not fatal to the WhatsApp response).
3. **Model retraining:** Not triggered by API calls. Colab runs `run_forecast_pipeline()` on accumulated history, serializes the model, and the file-replace updates the inference service on restart.

## API Contract

### POST /recommend

**Request:**
```json
{
  "merchant_id": "550e8400-e29b-41d4-a716-446655440000",
  "product": "עגבניות",
  "target_date": "2026-04-11",
  "cost_params": {
    "underage_cost": 3.0,
    "overage_cost": 5.0
  }
}
```

`cost_params` is optional. Defaults to `CostParams` from `optimization/rewards.py` (underage=3.0, overage=5.0).

**Response:**
```json
{
  "product": "עגבניות",
  "recommended_quantity": 42,
  "strategy": "lgbm_newsvendor",
  "confidence": "high",
  "history_days": 120
}
```

`strategy` values: `"defaults"` | `"newsvendor"` | `"lgbm_newsvendor"`. meshek logs this for debugging; it is not shown to the merchant.

### POST /sales

**Request (mirrors canonical schema from `forecasting/schema.py`):**
```json
{
  "merchant_id": "550e8400-e29b-41d4-a716-446655440000",
  "product": "עגבניות",
  "date": "2026-04-10",
  "quantity": 38
}
```

**Response:** `{ "status": "ok" }`

### GET /health

**Response:** `{ "status": "ok" }` — identical shape to llm-engine.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0–50 merchants | SQLite per merchant, one FastAPI process, one Cloud Run instance. Current plan. |
| 50–500 merchants | SQLite files can stay on Cloud Filestore shared volume. Pin Cloud Run to 1 instance to avoid concurrent write contention, or switch to append-only pattern. |
| 500+ merchants | Replace SQLite with Cloud SQL PostgreSQL. Separate inference service from training service. This is the federated learning milestone scope, not v1.1. |

### Scaling Priorities

1. **First bottleneck:** SQLite file locking under concurrent Cloud Run instances. Mitigation: pin `--max-instances=1` in Cloud Run for v1.1. If multi-instance is needed before a DB migration, switch to append-only writes with daily aggregation reads.
2. **Second bottleneck:** LightGBM training time on long histories. Mitigation: cache the trained model per merchant. Only retrain when a meaningful new-data threshold is crossed (e.g., 7 new rows since last training).

## Anti-Patterns

### Anti-Pattern 1: Passing Full Sales History in /recommend Request Body

**What people do:** Have meshek serialize and send the entire sales DataFrame as part of the recommendation request to avoid meshek-ml needing its own database.

**Why it's wrong:** Payload grows unboundedly with time. Caller must understand and serialize the ML data schema. The cold-start router needs to know history length first — the caller would have to count rows anyway. Adds latency to every WhatsApp response.

**Do this instead:** meshek-ml owns its SQLite store. meshek only sends new sales events via `POST /sales`. `/recommend` is fully self-contained.

### Anti-Pattern 2: Retraining on Every /recommend Call

**What people do:** Re-run `run_forecast_pipeline()` inside the request handler to keep the model current.

**Why it's wrong:** Training on 90+ days of data takes several seconds. WhatsApp users expect a response in under 3 seconds. Cloud Run will time out the request before training completes.

**Do this instead:** Train offline in Colab. Serialize to `models/forecasting/{merchant_id}.lgbm`. Load the model at service startup or lazily on first request per merchant. Update by file replacement + restart.

### Anti-Pattern 3: Adding a POST /train Endpoint to the Inference Service

**What people do:** Expose training as an HTTP endpoint so meshek can trigger retraining on-demand.

**Why it's wrong:** Training is long-running and stateful. It ties up the web worker process. Cloud Run instances are meant to be stateless and interchangeable; running a training job on one instance creates inconsistency if the instance restarts.

**Do this instead:** Keep training in Colab for v1.1. If automation is needed later, use a Cloud Run Job (separate container + Cloud Scheduler trigger) — not a route on the inference server.

### Anti-Pattern 4: Diverging from the llm-engine Dockerfile Pattern

**What people do:** Use a different base image, multi-stage build, or CMD format for the new service.

**Why it's wrong:** Two different container patterns in the same codebase creates ops debt. The llm-engine Dockerfile is already proven in production.

**Do this instead:** Copy `services/llm-engine/Dockerfile` as the starting point. Replace `python:3.12-slim` with `python:3.11-slim` (Python 3.10+ is the meshek-ml requirement; 3.11 provides better LightGBM build compatibility than 3.12 as of April 2026). Keep `uvicorn src.main:app --host 0.0.0.0 --port 8080` as the CMD.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| meshek Fastify API | HTTP POST to `ML_ENGINE_URL` env var | Add `mlEngineUrl` to meshek `config.ts`. Add `ML_ENGINE_URL` to `validateProductionEnv()` alongside the existing `LLM_ENGINE_URL` entry. |
| Google Cloud Run (production auth) | Identity token in `Authorization: Bearer` header | Reuse `getAuthHeaders()` and `fetchIdentityToken()` from `llm-client.ts` verbatim in the new `ml-client.ts`. Zero new infrastructure. |

### Internal Boundaries (within meshek-ml)

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `services/api/` ↔ `src/meshek_ml/` | Direct Python import | API layer imports library functions. No HTTP between them. The library has no knowledge of the API layer. |
| `recommendation_engine.py` ↔ `sales_store.py` | Direct function call | Engine queries store for history; store is a plain Python class, not a subprocess or service. |
| `services/api/` ↔ `data/sales/` | SQLite via `sqlite3` stdlib | Path injected via `DATA_DIR` env var. Default `./data/sales` for local dev. |
| `services/api/` ↔ `models/forecasting/` | File load at startup or lazy | Path injected via `MODEL_DIR` env var. Default `./models/forecasting`. |

### New Components in meshek Repo (built there, not here)

| Component | File | What it does |
|-----------|------|-------------|
| ML client | `packages/api/src/services/ml-client.ts` | Typed HTTP wrapper around `/recommend` and `/sales` |
| ML config | `packages/api/src/config.ts` | Add `mlEngineUrl: process.env.ML_ENGINE_URL ?? "http://localhost:8001"` |
| Env validation | `packages/api/src/config.ts` | Add `ML_ENGINE_URL` to `validateProductionEnv()` required array |
| Recommendation route | `packages/api/src/routes/recommendations.ts` | Fastify plugin receiving merchant + product, calling ml-client |
| Sales forwarding | Inside existing WhatsApp message handler | After llm-engine parses a sales observation, call ml-client `/sales` |

## Build Order (Dependency-Respecting)

The following order ensures each step is testable before the next begins:

1. **`services/api/schemas.py`** — Pydantic request/response models. The API contract both sides code against. No other dependencies.
2. **`services/api/sales_store.py`** — SQLite persistence. Independently testable. No ML dependency.
3. **`services/api/recommendation_engine.py`** — Wraps existing `run_forecast_pipeline` and `optimal_order_normal`. Unit-testable with synthetic DataFrames before the FastAPI layer exists.
4. **`services/api/main.py`** — Wire FastAPI routes. Depends on store and engine from steps 2–3.
5. **`services/api/Dockerfile` + `requirements.txt`** — Containerize. Confirm `GET /health` returns 200 in Docker before any meshek integration work begins.
6. **`packages/api/src/services/ml-client.ts` (meshek repo)** — Implement against the schema from step 1. Integration-test against the running Docker container.
7. **`packages/api/src/routes/recommendations.ts` (meshek repo)** — Fastify route calling ml-client. End-to-end testable.
8. **Sales forwarding in WhatsApp handler (meshek repo)** — Final integration: parsed sales automatically flow into meshek-ml.

## Sources

- Direct read of `meshek/packages/api/src/services/llm-client.ts` — auth pattern (`getAuthHeaders`, `fetchIdentityToken`), typed HTTP client structure, error handling
- Direct read of `meshek/packages/api/src/config.ts` — `llmEngineUrl` env var pattern, `validateProductionEnv()` convention
- Direct read of `meshek/services/llm-engine/Dockerfile` — container pattern: `python:3.12-slim`, uvicorn CMD, `EXPOSE 8080`
- Direct read of `meshek/services/llm-engine/src/main.py` — FastAPI structure, `/health` endpoint shape, Pydantic request models, env validation at startup
- Direct read of `meshek/packages/api/src/db/schema.ts` — confirmed no sales history tables exist in meshek's PostgreSQL; sales ownership must live in meshek-ml
- Direct read of `meshek-ml/src/meshek_ml/forecasting/pipeline.py` — `run_forecast_pipeline()` signature; 14-day lag + 7-day rolling window determines 90-day minimum for LightGBM tier
- Direct read of `meshek-ml/src/meshek_ml/optimization/newsvendor.py` — `optimal_order_normal(mean, std, underage_cost, overage_cost)` signature
- Direct read of `meshek-ml/src/meshek_ml/optimization/rewards.py` — `CostParams` defaults (selling_price=7, purchase_cost=5, holding_cost=0.1, waste_penalty=5, stockout_penalty=3)
- Direct read of `meshek-ml/pyproject.toml` — FastAPI not yet a dependency; needs adding under a new `[api]` optional extra

---
*Architecture research for: meshek-ml FastAPI inference service + meshek integration (v1.1)*
*Researched: 2026-04-10*
