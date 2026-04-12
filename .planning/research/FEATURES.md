# Feature Research

**Domain:** ML inference API for perishable goods demand forecasting (single-store greengrocer)
**Project:** meshek-ml v1.1
**Researched:** 2026-04-10
**Confidence:** HIGH (API patterns, differentiator analysis), MEDIUM (Hebrew parsing approach)

---

## Framing

This milestone adds a FastAPI inference service consumed by the meshek TypeScript app. The existing codebase already ships a working LightGBM forecasting pipeline (`forecasting/pipeline.py`), newsvendor optimizer (`optimization/newsvendor.py`), and Hebrew-locale simulation (`simulation/merchants.py`). The new API wraps those modules — it does not rewrite them. Features are evaluated through one lens: "does a greengrocer get a better order recommendation tomorrow because of this?"

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features the meshek app requires for its first real merchant interaction. Missing any of these means the WhatsApp recommendation loop cannot function.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `POST /recommend` endpoint | meshek Fastify backend needs a single callable entry point to get order quantities | LOW | Returns `{product, quantity, confidence_score, reasoning_tier}` per product; wraps existing `optimal_order_normal` |
| Per-merchant, per-product quantity recommendation | The core product promise: "how much should I order tomorrow?" | LOW | Calls `optimal_order_normal(mean_demand, std_demand, underage_cost, overage_cost)` from `optimization/newsvendor.py` — already implemented |
| Cold-start fallback — no history required | New merchants have zero sales history; service must still respond usefully on day one | MEDIUM | Three-tier: (1) hardcoded category defaults → (2) cross-merchant pooling → (3) ML forecast; cannot hard-fail; must degrade gracefully |
| JSON request/response contract with Pydantic validation | meshek communicates over HTTP; needs typed, stable contract | LOW | Pydantic models for input/output; mirrors existing `SchemaValidationError` pattern in `forecasting/schema.py`; reject bad input with 422 |
| `GET /health` endpoint | meshek Fastify verifies service is reachable before calling; same pattern as meshek's `llm-engine` service | LOW | Returns `{status: "ok", model_loaded: bool}` |
| Model-at-startup loading | LightGBM load time is non-trivial; loading per-request causes 800ms+ first-request latency | LOW | FastAPI lifespan context manager (Python 3.10+); model pinned in `app.state`; reduces inference to ~20ms |
| Per-merchant sales history ingestion | `run_forecast_pipeline` requires historical `(date, merchant_id, product, quantity)` rows; API must accept and persist them | MEDIUM | `POST /sales` endpoint; writes to per-merchant parquet files; feeds existing `run_forecast_pipeline` |
| Hebrew product name parsing | Merchants report sales via WhatsApp in Hebrew free text ("מכרתי 3 קילו עגבניות"); API must map this to canonical product IDs | MEDIUM | Dictionary-based normalization; no LLM (explicitly required by PROJECT.md); maps variant spellings to canonical English IDs used by the forecasting schema |
| Day-of-week and holiday-aware recommendations | Greengrocers have strong weekly patterns (Shabbat 1.5x, Rosh Hashana 2x); ignoring this makes recommendations wrong every week | LOW | Re-uses existing `add_calendar_features`, `weekly_factors`, `holiday_factors` from `simulation/calendar.py` — already implemented in feature pipeline |

### Differentiators (Competitive Advantage)

These are the features that make meshek-ml meaningfully different from Afresh, RELEX, and generic ML notebooks. They exist entirely in the confirmed whitespace: single-store merchants, Hebrew market, zero POS infrastructure.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Three-tier cold-start strategy | New merchants get useful recommendations on day one — not after weeks of POS data collection. Enterprise tools require months of historical data before making a recommendation. | MEDIUM | Tier 1: category defaults hardcoded (e.g., tomatoes 15 kg/day). Tier 2: cross-merchant quantile pooling from same archetype (uses `simulation/merchants.py` archetypes as priors). Tier 3: ML forecast once ≥14 days personal history exists. `reasoning_tier` field in response tells meshek which tier fired — meshek surfaces this to the merchant with honest framing ("based on similar greengrocers"). |
| `reasoning_tier` + `confidence_score` in response | meshek can format the WhatsApp message differently based on how confident the recommendation is. "We're estimating based on similar greengrocers" builds trust with skeptical merchants. Enterprise tools never expose this. No other open-source ordering tool does this. | LOW | `reasoning_tier: "default" | "cross_merchant" | "ml_forecast"`. `confidence_score: float` (0–1). Simple to add; high trust value for skeptical low-tech users. |
| Israeli holiday calendar integration | Generic demand APIs don't know that Rosh Hashana shifts by 2-3 weeks each year, or that Sukkot creates different product demand than Pesach. The existing `israeli_holidays()` in `simulation/calendar.py` uses fixed Gregorian approximations. | MEDIUM | Upgrade to `hdate` (Python Hebrew calendar library, MIT license) for accurate lunisolar conversion. Expose `upcoming_holiday` field in `/recommend` response so meshek can surface "Rosh Hashana in 3 days — order tomatoes 2x" proactively. |
| Asymmetric cost function exposed in API | Generic inventory models use symmetric costs. Perishables have asymmetric overage (waste = 100% loss of purchase cost) vs underage (missed sale = lost margin only). The existing newsvendor with `underage_cost`/`overage_cost` already encodes this. No enterprise tool exposes cost asymmetry for single stores. | LOW | Expose `underage_cost` and `overage_cost` as optional request parameters with sensible category defaults. Leafy greens: high overage cost. Root vegetables: lower. Default ratios can be hardcoded per product category for v1.1. |
| Zero-configuration merchant onboarding | Enterprise tools require data migration, ERP connectors, SKU mapping sessions. meshek-ml onboarding: merchant sends first WhatsApp message → `POST /merchants` creates merchant ID → Tier 1 defaults serve recommendations immediately. First recommendation happens before any sales are reported. | LOW | `POST /merchants` creates a minimal merchant profile. No configuration fields required. Immediate useful response. |
| Open-source, self-hostable ML pipeline | Afresh/RELEX are proprietary black boxes with enterprise contracts. meshek-ml's ML pipeline (LightGBM + newsvendor) can be audited, extended, or contributed to. This matters for potential NGO/cooperative deployments serving merchant communities. | LOW | Feature of repo structure, not API code. Enforce via permissive license on `src/meshek_ml/` modules. |

### Anti-Features (Commonly Requested, Often Problematic)

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| LLM-based Hebrew parsing | LLMs understand Hebrew well; seems obvious for free-text input | Adds network dependency, per-token cost, latency, and non-determinism to every sales ingestion call. Merchants type `עגבניות` not complex sentences. Adds an external API key requirement and failure mode. | Dictionary-based normalization with ~100 produce entries handles 90%+ of real input. Fuzzy match (rapidfuzz) handles misspellings. Flag unrecognized terms for manual review. PROJECT.md explicitly requires "dictionary-based, no LLM." |
| Real-time streaming inference | Sounds high-tech; "live recommendations" feel premium | Greengrocers order once per day at 2-3 AM. Real-time inference adds WebSocket/SSE complexity with zero user value. Merchants do not want a live feed. | Batch inference triggered by `/recommend` request. One call per merchant per day. |
| Per-product model (one LightGBM per SKU) | Seems more accurate; dedicated models per item | Explodes storage and training time. Sparse data per SKU makes per-SKU models worse, not better. M5 competition (cited in APPROACH.md) confirms one model with product as categorical feature outperforms per-SKU models at low data volumes. | One model per merchant, `product` as categorical feature in LightGBM. Already the current pipeline design. |
| Synchronous model retraining on `/recommend` | "Always fresh model" sounds appealing | LightGBM retraining takes seconds to minutes. Blocking a request on retraining means 30+ second API response. Confuses short-term noise (one bad day) with signal. | Async `POST /retrain/{merchant_id}` endpoint with `202 Accepted`. Returns immediately; retrains in background. Or nightly scheduled job. |
| Confidence intervals as primary output | Data scientists want uncertainty quantification; "tell me the range" | Merchants don't understand "order 12-18 kg." Single number plus plain-language tier is what they need. Decision paralysis is the enemy. | Single recommended quantity + `reasoning_tier` label. Reserve quantile outputs for internal logging only. |
| Federated training in API scope | Federated learning is in the repo (`federated/`) | Federated training is explicitly deferred to a future milestone in PROJECT.md. Including it in v1.1 API scope risks shipping nothing. | Keep federated stubs as-is. Cross-merchant cold-start pooling (Tier 2) achieves the practical benefit of shared priors without federated training overhead. |
| Dynamic pricing recommendations | Retailers always request "what should I charge?" | Pricing is relational for greengrocers — negotiated with suppliers and regulars. Wrong pricing advice destroys trust faster than a bad order quantity. All 8 academic papers confirm pricing coupling increases complexity. Explicitly deferred in PROJECT.md. | Order quantity only. `price` column exists in schema for future use; never recommend it in v1. |
| Dashboard or analytics endpoints in meshek-ml | "Merchants want to see their data" | Merchants have zero appetite for dashboards (confirmed merchant context). Blurs the two-repo boundary. Dashboard responsibility belongs to meshek app, not meshek-ml. Building it here duplicates work. | meshek-ml is a JSON API only. meshek app owns all UI/display logic. Strict boundary enforced by architecture. |
| PPO agent inference in v1.1 | PPO is already trained in the Colab notebook | Serving PPO requires Stable-Baselines3 in the API Docker image (heavy dependency, ~400MB), model serialization/versioning, and a stateful environment for inference. Newsvendor is analytically equivalent for single-step daily ordering and has no serving overhead. | Newsvendor for v1.1. PPO as optional inference path in v2 when benchmarking proves it beats newsvendor on real merchant data. |

---

## Feature Dependencies

```
[Hebrew Parser]
    └──requires──> [Canonical Product Dictionary] (manually curated)
                       └──enables──> [POST /sales ingestion]
                                         └──requires──> [Per-Merchant Storage]

[Per-Merchant Storage]
    ├──enables──> [ML Forecast Tier] (needs ≥14 days per-merchant history)
    └──enables──> [Cross-Merchant Pooling Tier] (reads anonymized history across merchants)

[Cold-Start Strategy]
    ├── Tier 1 (defaults) ─────────────────────── no dependencies; ships first
    ├── Tier 2 (cross-merchant pooling) ─────────requires──> [Per-Merchant Storage]
    └── Tier 3 (ML forecast) ────────────────────requires──> [Per-Merchant Storage]
                                                              + [run_forecast_pipeline] (existing)
                                                              + [optimal_order_normal] (existing)

[POST /recommend]
    ├──requires──> [Cold-Start Strategy]
    ├──requires──> [Model-at-Startup Loading]
    ├──calls──────> [optimization/newsvendor.py::optimal_order_normal] (existing)
    ├──calls──────> [forecasting/pipeline.py::run_forecast_pipeline] (existing, Tier 3)
    └──calls──────> [simulation/calendar.py holiday/weekly factors] (existing, via pipeline)

[POST /retrain/{merchant_id}]
    ├──requires──> [Per-Merchant Storage]
    └──conflicts──> [synchronous request cycle] (must be async / background task)

[Israeli Holiday Calendar upgrade]
    └──enhances──> [POST /recommend] (more accurate holiday proximity field)
    └──replaces──> [simulation/calendar.py::israeli_holidays] fixed approximations
```

### Dependency Notes

- **Per-Merchant Storage is the foundational prerequisite.** Without it, every feature beyond Tier 1 defaults is impossible. It must be the first module built in the API phase.
- **Hebrew Parser requires a manually curated dictionary.** This is the most domain-specific artifact in v1.1. It cannot be auto-generated — someone must map common Hebrew produce terms (including misspellings, diminutives, and plural forms) to canonical English product IDs. Estimate: 1-2 days of curation for 80-120 terms covering typical greengrocer inventory.
- **ML Forecast Tier (Tier 3) requires ≥14 days of sales history.** The `add_lag_features` and `add_rolling_features` in `forecasting/features.py` create NaN rows for the first 7-14 days. The pipeline's `.dropna()` call eliminates them; if no valid rows remain, `run_forecast_pipeline` raises `ValueError`. The API must catch this and fall back to Tier 2 or Tier 1.
- **Model-at-Startup Loading is a prerequisite for response latency targets.** Loading LightGBM per-request incurs 500-800ms overhead. FastAPI `lifespan` async context manager (standard Python 3.10+ pattern) pins the model in `app.state` once at startup.
- **POST /retrain must not block the event loop.** LightGBM retraining is CPU-bound; running it synchronously in an async endpoint starves other requests. Use `asyncio.create_task` with `asyncio.get_event_loop().run_in_executor` or FastAPI `BackgroundTasks`. Caller receives `202 Accepted` immediately.

---

## MVP Definition

### Launch With (v1.1)

Minimum viable to let meshek app deliver its first real order recommendation.

- [ ] `GET /health` — verify service is up before meshek calls it
- [ ] `POST /merchants` — create merchant profile, no configuration required
- [ ] `POST /sales` — ingest daily sales rows (Hebrew-parsed or pre-parsed), persist per-merchant
- [ ] `POST /recommend` — return per-product order quantity for a merchant's catalog
  - [ ] Tier 1: hardcoded category defaults (no history required)
  - [ ] Tier 3: ML forecast path using existing `run_forecast_pipeline` (≥14 days history)
  - [ ] `reasoning_tier` + `confidence_score` in response
- [ ] Hebrew product name parser — dictionary-based, ~80-120 common produce terms
- [ ] Per-merchant flat-file storage (parquet per merchant ID, no DB required for v1)
- [ ] Model-at-startup loading via FastAPI lifespan
- [ ] Pydantic request/response validation with typed error responses

### Add After Validation (v1.x)

Add once first merchants are using the recommendation loop and feedback is available.

- [ ] Tier 2 cold-start: cross-merchant pooling — add after 3+ merchants have data to pool
- [ ] Async `POST /retrain/{merchant_id}` — add when stale models appear in merchant feedback
- [ ] `hdate` Hebrew calendar upgrade — replace fixed-Gregorian approximations; current `calendar.py` is good enough for v1.1
- [ ] Asymmetric cost parameters exposed in request — add when merchants ask why a recommendation seems high/low
- [ ] Fuzzy match fallback for Hebrew parser (rapidfuzz) — add when unknown product terms appear frequently in logs

### Future Consideration (v2+)

- [ ] Federated training across merchants — explicitly deferred in PROJECT.md; need stable single-merchant pipeline first
- [ ] PPO agent inference path — requires Stable-Baselines3 in API image (~400MB), model versioning, stateful environment; defer until PPO benchmarks prove advantage on real data
- [ ] E2E forecast-optimize (replacing two-stage) — Paper 5 (Liao et al.) shows improvement; deferred in PROJECT.md
- [ ] Dynamic pricing — explicitly deferred in all 8 cited papers and PROJECT.md

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| `POST /recommend` (Tier 1 defaults) | HIGH | LOW | P1 |
| `POST /sales` + per-merchant storage | HIGH | LOW | P1 |
| `GET /health` | HIGH | LOW | P1 |
| `POST /merchants` | HIGH | LOW | P1 |
| Model-at-startup loading | HIGH | LOW | P1 |
| `POST /recommend` (Tier 3 ML path) | HIGH | MEDIUM | P1 |
| Hebrew parser — dictionary-based | HIGH | MEDIUM | P1 |
| `reasoning_tier` + `confidence_score` in response | HIGH | LOW | P1 |
| Pydantic validation + typed error responses | MEDIUM | LOW | P1 |
| `POST /recommend` (Tier 2 cross-merchant) | MEDIUM | MEDIUM | P2 |
| `hdate` holiday calendar upgrade | MEDIUM | LOW | P2 |
| Async `POST /retrain/{merchant_id}` | MEDIUM | MEDIUM | P2 |
| Asymmetric cost params in request | LOW | LOW | P2 |
| Fuzzy Hebrew match (rapidfuzz) | LOW | LOW | P3 |
| PPO agent inference path | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for v1.1 launch — meshek cannot serve merchants without these
- P2: Add after first merchants are active and generating feedback
- P3: Future consideration, v2+

---

## Competitor Feature Analysis

| Feature | Afresh | RELEX Solutions | meshek-ml approach |
|---------|--------|-----------------|-------------------|
| Target segment | 10K+ department grocery chains (US) | Enterprise grocery chains; starts ~$3K/month | Single-store Israeli greengrocers — confirmed whitespace |
| Onboarding | Months; POS integration required | ERP/WMS integration required | Zero-config: `POST /merchants`, get defaults immediately |
| Minimum history to function | ~12 months POS history | Varies; months of integration | 0 days (Tier 1), 14 days (Tier 3) |
| Cold start | Not applicable | Not applicable | Three-tier: defaults → pooling → ML |
| Hebrew language support | None | None | Native — dictionary parser for produce terms |
| Israeli holiday calendar | None | None | Built-in; `hdate` upgrade planned |
| Merchant interface | Dashboard, ERP write-back | Dashboard, complex UI | WhatsApp (via meshek app); API outputs JSON only |
| Recommendation transparency | Black box | Configurable rule audit | `reasoning_tier` exposes which tier drove the recommendation |
| Perishable asymmetric costs | Yes (proprietary) | Yes (proprietary) | Yes — newsvendor with `underage_cost`/`overage_cost`, already implemented |
| Price | Enterprise contract | Enterprise contract | Open-source ML pipeline; self-hostable |

---

## Dependencies on Existing meshek-ml Modules

The new FastAPI service wraps existing modules — it does not rewrite them.

| Existing Module | Used By | Call Interface |
|----------------|---------|----------------|
| `forecasting/pipeline.py::run_forecast_pipeline` | Tier 3 ML inference in `/recommend` | Takes `pd.DataFrame` with canonical `(date, merchant_id, product, quantity)` schema |
| `forecasting/schema.py::validate_demand_schema` | `POST /sales` ingestion | Raises `SchemaValidationError` on missing columns or nulls |
| `optimization/newsvendor.py::optimal_order_normal` | All recommendation tiers | `(mean_demand, std_demand, underage_cost, overage_cost) → float` |
| `simulation/calendar.py::holiday_factors`, `weekly_factors` | Feature engineering (called internally by `add_calendar_features` in pipeline) | DatetimeIndex → np.ndarray of multipliers |
| `forecasting/features.py` | Tier 3 path (internal to `run_forecast_pipeline`) | Called internally; no direct API call |

Three new modules introduced by v1.1 that do not exist in the current codebase:

1. `api/` — FastAPI application: routers, Pydantic schemas, lifespan handler, error handlers
2. `storage/` — per-merchant persistence layer: read/write parquet per `merchant_id`
3. `parsing/hebrew_parser.py` — canonical product dictionary + text normalization + unit/weight extraction

---

## Sources

- [FastAPI model serving production guide](https://markaicode.com/fastapi-uvicorn-model-serving-production/) — lifespan handler, worker initialization, cold-start latency benchmarks
- [How to Optimize FastAPI for ML Model Serving](https://luis-sena.medium.com/how-to-optimize-fastapi-for-ml-model-serving-6f75fb9e040d) — startup loading, ThreadPoolExecutor, 800ms → 47ms patterns
- [Cold start demand forecasting: DataRobot docs](https://docs.datarobot.com/latest/en/docs/api/accelerators/time-series/cold-start.html) — hierarchy-and-similarity cold-start strategy; pooling across comparable units
- [Awesome Hebrew NLP](https://github.com/iddoberger/awesome-hebrew-nlp) — confirms no off-the-shelf Hebrew grocery product parser exists; validates dictionary approach
- [Grid Dynamics: Time-series foundation models comparison](https://www.griddynamics.com/blog/ai-models-demand-forecasting-tsfm-comparison) — LightGBM competitive position vs foundation models at small-data scale
- Competitive landscape memory (`competitive_landscape.md`) — Afresh, RELEX, Freshflow confirmed enterprise-only; no ML ordering tool for single-store segment
- Merchant context memory (`merchant_context.md`) — Israeli greengrocer daily cycle, WhatsApp-only interface, waste patterns, tech adoption
- `.planning/PROJECT.md` — constraints (dictionary-based Hebrew, two-stage pipeline, newsvendor, LightGBM, dynamic pricing deferred, federated deferred)
- `academic/APPROACH.md` — 8 papers confirming LightGBM, newsvendor asymmetric costs, dynamic pricing complexity

---

*Feature research for: meshek-ml v1.1 — FastAPI Inference API for Perishable Goods Ordering*
*Researched: 2026-04-10*
