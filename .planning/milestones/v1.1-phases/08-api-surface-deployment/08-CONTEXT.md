# Phase 8: API Surface & Deployment - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning
**Mode:** Auto (autonomous workflow, --only 8)

<domain>
## Phase Boundary

Wire the Phase 6 recommendation engine and Phase 7 Hebrew parser behind a
FastAPI HTTP surface with four endpoints (`GET /health`, `POST /merchants`,
`POST /sales`, `POST /recommend`) and ship a Docker image that runs the
service on Railway or Fly.io. No new ML, parsing, or storage logic — only
transport, request/response schemas, error mapping, startup wiring, and
container packaging.

</domain>

<decisions>
## Implementation Decisions

### Framework & Server
- **D-01:** FastAPI (already in `pyproject.toml` service extra) with
  `uvicorn` as the ASGI server. Add `uvicorn[standard]` to the `service`
  extra — currently missing.
- **D-02:** Single `FastAPI(lifespan=...)` app instance built by a factory
  `create_app()` in `src/meshek_ml/service/app.py`, consuming the existing
  `build_lifespan()` from `service/lifespan.py` (D-10..D-12 from Phase 6).
- **D-03:** Entry point exposed as `meshek_ml.service.app:create_app` so
  uvicorn can launch via `uvicorn meshek_ml.service.app:create_app --factory`.

### Routing Layout
- **D-04:** Routes live under `src/meshek_ml/service/routes/` as APIRouters:
  `health.py`, `merchants.py`, `sales.py`, `recommend.py`. `create_app()`
  includes them. Keeps each endpoint independently testable.
- **D-05:** All routes are synchronous `def` handlers (no `async def`) —
  underlying storage is stdlib `sqlite3` and the model call is CPU-bound,
  so FastAPI will run them in the threadpool. No asyncio benefit, simpler
  stack traces.

### Request / Response Schemas
- **D-06:** Pydantic v2 request/response models live in
  `src/meshek_ml/service/schemas.py`. Reuse existing domain pydantic models
  where they exist (`RecommendationResponse`, `ProductRecommendation`,
  `MerchantProfile`) rather than duplicating.
- **D-07:** `POST /merchants` request body: `{merchant_id?: str,
  display_name?: str}`. If `merchant_id` omitted, server generates a
  ULID/uuid4 hex; server always echoes the final id. Response: the stored
  `MerchantProfile`.
- **D-08:** `POST /sales` request body supports BOTH shapes in one
  endpoint:
    - **structured:** `{merchant_id, date, items: [{product_id, quantity, unit}]}`
    - **free_text:** `{merchant_id, date, text: "20 עגבניות, 5 מלפפונים"}`
  Exactly one of `items` or `text` required; free-text routed through the
  Phase 7 parser before persist. Response: `{accepted_rows: int,
  skipped: list[{line, reason}]}`.
- **D-09:** `POST /recommend` request body: `{merchant_id: str}`. Response
  = existing `RecommendationResponse` from Phase 6 verbatim.
- **D-10:** `GET /health` response: `{status: "ok", model_loaded: bool,
  version: str}`. Reads `app.state.ml` to determine `model_loaded`. Returns
  200 if the lifespan loaded a model, 503 otherwise.

### Error Handling
- **D-11:** Central exception handler maps domain errors to HTTP:
    - `UnknownMerchantError` → 404
    - `SchemaValidationError` / pydantic `ValidationError` → 422
    - `HebrewParseError` (or equivalent Phase 7 error) → 422 with
      per-line reasons
    - `RuntimeError` from Tier 3 missing model → 503
    - everything else → 500 with an opaque `request_id` (uuid4) logged
      server-side, no stack trace in response body.
- **D-12:** All error responses share a `{error: {code, message,
  details?}}` envelope. Success responses are the raw pydantic model
  (no envelope) to keep the meshek app client simple.

### Merchant ID Validation at the Edge
- **D-13:** Request-level `merchant_id` validation mirrors the storage
  layer's `_MERCHANT_ID_PATTERN` (`^[A-Za-z0-9_-]{1,64}$`) — enforced via
  a pydantic `constr` so 422 is raised before any filesystem I/O. Defense
  in depth against path traversal (T-5-01).

### Configuration
- **D-14:** All runtime config via env vars, loaded once at startup:
    - `MESHEK_MODEL_PATH` (existing) — LightGBM bundle path
    - `MESHEK_DATA_DIR` (existing) — per-merchant SQLite root
    - `MESHEK_API_HOST` (default `0.0.0.0`)
    - `MESHEK_API_PORT` (default `8000`)
    - `MESHEK_LOG_LEVEL` (default `info`)
  No `.env` file required; container ships with sensible defaults.
- **D-15:** No auth in v1.1. The meshek app is the sole caller and runs
  in the same private network. Noted as deferred; do NOT add API keys,
  JWT, or CORS wildcards in this phase. CORS disabled by default.

### Docker Image (INFRA-02)
- **D-16:** Single-stage `Dockerfile` at repo root based on
  `python:3.12-slim`. Uses `uv` for dependency install (matches the
  existing `uv.lock`). Installs only the `service` + runtime extras —
  NOT `dev`, NOT `simulation`, NOT `federated`. LightGBM wheel pulls in
  its own libgomp.
- **D-17:** Image layout:
    ```
    /app
      src/meshek_ml/...
      models/              ← baked-in default model bundle
      configs/             ← category defaults YAML
    ```
  `WORKDIR /app`, non-root `appuser`, `EXPOSE 8000`, `CMD ["uvicorn",
  "meshek_ml.service.app:create_app", "--factory", "--host", "0.0.0.0",
  "--port", "8000"]`.
- **D-18:** `HEALTHCHECK` hits `GET /health` every 30s. Railway/Fly.io
  both honor this.
- **D-19:** Model bundle path inside the container: `/app/models/lightgbm_v1.bundle`.
  Override via `MESHEK_MODEL_PATH` at deploy time. A placeholder bundle
  must exist at that path for the image to start; training is out of
  scope for Phase 8.
- **D-20:** `.dockerignore` excludes `.venv`, `notebooks/`, `reports/`,
  `outputs/`, `data/`, `.planning/`, `academic/`, test files, and
  `__pycache__`.

### Deployment Target
- **D-21:** Ship a `fly.toml` for Fly.io as the primary deployment
  target (simpler auto-scaling, free allowance). Railway works with the
  same Dockerfile with no extra config — document a one-paragraph
  "deploy to Railway" section in the phase SUMMARY, no railway.json
  needed.
- **D-22:** No CI/CD pipeline in this phase — image builds locally via
  `docker build`. GitHub Actions automation deferred.

### Logging & Observability
- **D-23:** Structured JSON logs to stdout using Python's `logging` with
  a minimal custom formatter (no new dep). Each request logs
  `{request_id, method, path, status, duration_ms}`. No metrics endpoint
  in v1.1.

### Testing
- **D-24:** Integration tests under `tests/service/` using FastAPI's
  `TestClient` (which uses `httpx`, already a dep). Cover:
    - `/health` with and without model loaded
    - `/merchants` create (auto-id and explicit id)
    - `/sales` structured path and Hebrew free-text path
    - `/recommend` across all three tiers with seeded merchant stores
    - 404 / 422 / 503 error envelopes
- **D-25:** A Docker smoke test (`tests/service/test_docker_smoke.py`,
  marked `@pytest.mark.integration`) that builds the image and curls
  `/health` — guarded by an env flag so it doesn't run in normal test
  passes.

### Code Location Summary
```
src/meshek_ml/service/
  app.py              ← create_app() factory (NEW)
  lifespan.py         ← existing (Phase 6)
  state.py            ← existing (Phase 6)
  schemas.py          ← request/response models (NEW)
  errors.py           ← exception → HTTP mapping (NEW)
  routes/
    __init__.py       ← (NEW)
    health.py         ← (NEW)
    merchants.py      ← (NEW)
    sales.py          ← (NEW)
    recommend.py      ← (NEW)
Dockerfile            ← (NEW)
.dockerignore         ← (NEW)
fly.toml              ← (NEW)
tests/service/        ← (NEW)
```

### Claude's Discretion
- Exact pydantic field validators / error codes enum values
- Request id generation (uuid4 hex vs ulid)
- Log formatter implementation details
- Whether to factor a small `dependencies.py` for `Depends(get_engine)`
- Minor Dockerfile tweaks for smaller image size

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/ROADMAP.md` — Phase 8 goal, success criteria, deps
- `.planning/REQUIREMENTS.md` §API-01..API-04, INFRA-02

### Upstream Phase Context
- `.planning/phases/06-recommendation-engine/06-CONTEXT.md` — engine API,
  lifespan contract, `RecommendationResponse` shape (D-10..D-14)
- `.planning/phases/06-recommendation-engine/06-VERIFICATION.md` — what
  Phase 6 actually shipped
- `.planning/phases/07-hebrew-input-parsing/07-CONTEXT.md` — parser API,
  error types, line-level reasons
- `.planning/phases/07-hebrew-input-parsing/07-VERIFICATION.md` — what
  Phase 7 actually shipped
- `.planning/phases/05-data-foundation/05-CONTEXT.md` — MerchantStore
  API, `_MERCHANT_ID_PATTERN`, error hierarchy

### Existing Code
- `src/meshek_ml/service/lifespan.py` — `build_lifespan()` factory
- `src/meshek_ml/service/state.py` — `AppState` dataclass
- `src/meshek_ml/recommendation/engine.py` — `RecommendationEngine`
- `src/meshek_ml/recommendation/schema.py` — `RecommendationResponse`
- `src/meshek_ml/storage/merchant_store.py` — `MerchantStore`,
  `MerchantProfile`, `UnknownMerchantError`
- `src/meshek_ml/parsing/` — Phase 7 parser entry points

### External
- FastAPI lifespan docs — https://fastapi.tiangolo.com/advanced/events/
- Fly.io Python Docker guide — https://fly.io/docs/languages-and-frameworks/dockerfile/
- `uv` in Docker — https://docs.astral.sh/uv/guides/integration/docker/

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `service.lifespan.build_lifespan(model_path)`: ready-made FastAPI
  lifespan factory; Phase 8 just passes it to `FastAPI(lifespan=...)`.
- `service.state.AppState`: holds loaded model, `model_path`,
  `residual_std`, `feature_cols`. Accessed via `request.app.state.ml`.
- `RecommendationEngine`: stateless façade — instantiate once per
  request or cache on `app.state`, pass the preloaded model.
- `MerchantStore`: context-manager API, creates/reads per-merchant
  SQLite files. Raises `UnknownMerchantError` — map directly to 404.
- `RecommendationResponse` pydantic model: can be returned directly
  from `POST /recommend` with no wrapping.
- Phase 7 parser: converts Hebrew free text → list of
  `(product_id, quantity, unit)` with per-line error reporting —
  exactly the shape `POST /sales` needs.

### Established Patterns
- `from __future__ import annotations` + explicit type hints
- Pydantic v2 models for all schemas
- Env-var config with sensible defaults (`MESHEK_*` prefix)
- Fail-fast validation at module boundaries
- Errors subclass a domain base (e.g., `MerchantStoreError`) — central
  FastAPI exception handler can catch those bases cleanly

### Integration Points
- FastAPI `create_app()` is the new top-level entry for uvicorn
- `app.state.ml` set by lifespan, read by `/health` and `/recommend`
- `RecommendationEngine` built once at startup inside the lifespan
  (extend Phase 6's `build_lifespan` or wrap it in `create_app`)
- `MerchantStore(merchant_id)` instantiated per request inside handlers
- Dockerfile new — no prior container exists; `uv.lock` drives install

</code_context>

<specifics>
## Specific Ideas

- Keep response schemas thin — the meshek app is the only consumer and
  its contract is "one JSON object in, one JSON object out." Don't add
  HATEOAS links, pagination envelopes, or OpenAPI tags beyond the FastAPI
  defaults.
- Deploy target is Fly.io first because it has a cheaper free tier for
  always-on containers; Railway stays as a documented fallback with no
  extra config required.
- Container must start in under ~10s on a 256MB instance — don't import
  `torch`, `stable-baselines3`, `flwr`, or `streamlit` on the service
  hot path (they live in other extras and must not be installed in the
  image).
- Hebrew free-text parsing happens inline in `POST /sales`. Per-line
  failures are REPORTED but do not fail the whole request unless ALL
  lines fail — partial ingestion is better than no ingestion for a
  merchant phoning in sales at 2 AM.

</specifics>

<deferred>
## Deferred Ideas

- Auth / API keys / JWT — meshek app is the sole caller in a private
  network; revisit if we ever expose the service publicly.
- CORS — not needed until a browser client talks to the service directly.
- CI/CD for Docker image builds — GitHub Actions workflow is its own
  phase.
- Prometheus metrics endpoint / OpenTelemetry — observability phase,
  post-v1.1.
- `POST /retrain/{merchant_id}` — v2 per REQUIREMENTS.md §REC-05.
- `PATCH /merchants/{id}` for profile updates — not in API-01..04.
- Rate limiting / request quotas — not needed at current scale.
- Multi-arch (`linux/arm64`) Docker builds — ship amd64 first.
- Schema migration on boot beyond what `MerchantStore` already handles.

</deferred>

---

*Phase: 08-api-surface-deployment*
*Context gathered: 2026-04-15 (auto mode — /gsd-autonomous --only 8)*
