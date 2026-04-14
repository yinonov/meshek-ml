# Phase 6: Recommendation Engine - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Mode:** Auto (autonomous workflow, --only 6)

<domain>
## Phase Boundary

Deliver a recommendation service capability that produces a confidence-scored
per-product order recommendation for any merchant, using three cold-start tiers
selected by available history. The LightGBM model must load once at service
startup via FastAPI lifespan. HTTP/API surface is explicitly deferred to Phase 8;
this phase ships the internal engine plus the lifespan hook.

</domain>

<decisions>
## Implementation Decisions

### Tier Selection
- **D-01:** Tier thresholds per ROADMAP.md success criteria — Tier 1 = 0 days of
  history, Tier 2 = 1-13 days, Tier 3 = ≥14 days. Threshold computed from
  distinct sale dates in the merchant's SQLite sales table.
- **D-02:** Tier is determined per-request from the merchant store — no cached
  tier state. Single source of truth = sales history row count.

### Tier 1 — Category Defaults
- **D-03:** Defaults sourced from a static YAML config under `configs/`
  keyed by product category. Hardcoded fallback (e.g., 5 units/day) if category
  is unknown, so Tier 1 never errors.
- **D-04:** `confidence_score = 0.2` (low) for Tier 1.

### Tier 2 — Pooled Priors
- **D-05:** Pooled prior = mean daily quantity per product across all other
  merchants with ≥14 days history, blended with the merchant's own partial
  history via a simple shrinkage weight `n/(n+14)`.
- **D-06:** `confidence_score` scales linearly from 0.3 (1 day) to 0.6 (13 days).

### Tier 3 — LightGBM Forecast
- **D-07:** Reuse existing `forecasting.tree_models` / `forecasting.pipeline`
  LightGBM infrastructure. Wrap with a `RecommendationEngine` façade.
- **D-08:** Feed the LightGBM forecast into existing `optimization.newsvendor`
  to convert expected demand → order quantity (reusing Phase 3 baseline).
- **D-09:** `confidence_score` derived from forecast interval width or quantile
  coverage, clipped to [0.6, 0.95].

### Model Loading (INFRA-01)
- **D-10:** Add a `lifespan` module under `src/meshek_ml/service/` (new package)
  exposing an `async contextmanager` compatible with FastAPI lifespan. Loads a
  single shared LightGBM model from a configured path at startup; tears down on
  shutdown.
- **D-11:** Model path resolved via env var `MESHEK_MODEL_PATH` with a sensible
  default under `models/`.
- **D-12:** FastAPI app wiring (the actual `app = FastAPI(lifespan=...)`) is
  deferred to Phase 8. This phase only provides the reusable lifespan factory
  and ensures it works with a bare `FastAPI()` smoke test.

### Response Shape (REC-04)
- **D-13:** `RecommendationResponse` = pydantic model with fields:
  `merchant_id: str`, `recommendations: list[ProductRecommendation]`,
  `reasoning_tier: Literal["category_default","pooled_prior","ml_forecast"]`,
  `confidence_score: float`, `generated_at: datetime`.
- **D-14:** `ProductRecommendation` = `{product_id, quantity, unit}`.

### Code Location
- **D-15:** New package `src/meshek_ml/recommendation/` with modules
  `engine.py` (façade + tier router), `tiers.py` (3 tier implementations),
  `schema.py` (pydantic models), `config.py` (category defaults loader).
- **D-16:** New package `src/meshek_ml/service/` with `lifespan.py` (model
  loader) and `state.py` (app-state dataclass holding the loaded model).

### Testing
- **D-17:** Unit tests per tier with synthetic merchant stores (0, 7, 30 days).
  Integration test that exercises `engine.recommend()` through all three tiers.
  Lifespan test uses FastAPI `TestClient` with a bare app.

### Claude's Discretion
- Confidence score formulas (within the ranges above)
- Internal module layout within `recommendation/` and `service/`
- LightGBM hyperparameters and model file format (joblib or LightGBM native txt)
- Pooled-prior shrinkage exact weighting
- Category defaults YAML schema

</decisions>

<canonical_refs>
## Canonical References

### Requirements & Roadmap
- `.planning/ROADMAP.md` — Phase 6 goal + success criteria
- `.planning/REQUIREMENTS.md` — REC-01..REC-04, INFRA-01

### Upstream Phase Context
- `.planning/phases/05-data-foundation/05-CONTEXT.md` — MerchantStore API,
  isolation model, schema
- `.planning/phases/05-data-foundation/05-VERIFICATION.md` — what Phase 5 ships

### Existing Code
- `src/meshek_ml/storage/merchant_store.py` — sales read API
- `src/meshek_ml/forecasting/pipeline.py` — LightGBM training/inference
- `src/meshek_ml/forecasting/tree_models.py` — LightGBM model wrapper
- `src/meshek_ml/optimization/newsvendor.py` — demand → order quantity

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MerchantStore`: read sales history by merchant_id + date range
- `forecasting.pipeline`: existing LightGBM training/forecast plumbing
- `optimization.newsvendor`: expected-demand → order-quantity transform
- `forecasting.schema.validate_demand_schema`: schema validation

### Established Patterns
- Pydantic models for schemas (see `storage/merchant_store.py::MerchantProfile`)
- `from __future__ import annotations` + explicit typing throughout
- Config via env vars with sensible defaults (MESHEK_DATA_DIR pattern)
- Fail-fast validation at module boundaries

### Integration Points
- `recommendation.engine.RecommendationEngine(store, model)` is the façade
  Phase 8 will import
- `service.lifespan.lifespan(app)` is what Phase 8 will pass to FastAPI()

</code_context>

<specifics>
## Specific Ideas

- Keep Phase 6 strictly engine + lifespan — no HTTP routes. Phase 8 owns the
  API surface per ROADMAP.md.
- Follow Phase 5's pattern: pydantic models, explicit type hints, fail-fast
  validation, tests adjacent to code.

</specifics>

<deferred>
## Deferred Ideas

- REC-05 (async retrain endpoint) — v1.2 or later
- REC-06 (hdate Hebrew calendar) — nice-to-have, not REC-01..04
- REC-07 (per-product asymmetric costs in request) — future
- HTTP endpoints wiring — Phase 8
- Docker container — Phase 8 (INFRA-02)

</deferred>

---

*Phase: 06-recommendation-engine*
*Context gathered: 2026-04-14 (auto mode — /gsd-autonomous --only 6)*
