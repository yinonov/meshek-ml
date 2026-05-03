# Phase 6: Recommendation Engine - Research

**Researched:** 2026-04-14
**Domain:** ML inference service (three-tier cold-start recommendation + FastAPI lifespan model load)
**Confidence:** HIGH

## Summary

Phase 6 sits on top of a mature codebase: Phase 5 MerchantStore (verified 11/11), a working
LightGBM forecasting pipeline (`forecasting.pipeline.run_forecast_pipeline`), and a newsvendor
optimizer (`optimization.newsvendor`). None of these are "missing" — the risk in Phase 6 is
**glue code, not algorithmic work**: tier routing, cross-merchant aggregation, model
persistence (new), and a FastAPI lifespan factory (new).

Three facts shape the plan:

1. **FastAPI is not a direct project dependency yet.** It shows up in uv.lock 0.135.3 only
   transitively (via gradio). Phase 6 must add it explicitly to `pyproject.toml` under a new
   `service` optional-extra, otherwise `import fastapi` is not contractually guaranteed.
   [VERIFIED: uv.lock line 1370 + pyproject.toml read]
2. **There is no model persistence today.** `forecasting.pipeline.run_forecast_pipeline`
   trains-and-evaluates in one call and returns metrics — it never saves a model. Phase 6 must
   introduce a training entry point that **writes** a LightGBM model file, plus a loader the
   lifespan hook consumes. `models/` directory exists but is empty.
   [VERIFIED: Grep for `save_model|joblib` in `src/meshek_ml` — only `ppo_agent.py` hits;
   Bash `ls models/` empty]
3. **MerchantStore has no list-merchants method.** Tier 2 pooled priors need to enumerate
   "all other merchants with ≥14 days history," but `MerchantStore` is strictly per-merchant.
   The plan must add a small directory-scan helper (filesystem scan of `MESHEK_DATA_DIR` for
   `*.sqlite` files) — this is the cleanest way and stays consistent with the filesystem-as-
   registry model D-01/D-02 from Phase 5.
   [VERIFIED: Read `src/meshek_ml/storage/merchant_store.py` — no list/scan methods]

**Primary recommendation:** Land Phase 6 in four focused waves — (a) contracts + configs +
pydantic schemas, (b) Tier 1 + Tier 2 tiers with a `PooledStore` filesystem helper, (c) Tier 3
model training/save + loader + LightGBM façade reusing `forecasting.features`, (d) FastAPI
lifespan factory + engine wiring + end-to-end integration test covering all three tiers.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Tier Selection**
- D-01: Tier thresholds — Tier 1 = 0 days, Tier 2 = 1-13 days, Tier 3 = ≥14 days. Threshold
  computed from distinct sale dates in the merchant's SQLite sales table.
- D-02: Tier is determined per-request from the merchant store; no cached tier state.

**Tier 1 — Category Defaults**
- D-03: Defaults sourced from a static YAML config under `configs/` keyed by product category.
  Hardcoded fallback (e.g., 5 units/day) if category is unknown so Tier 1 never errors.
- D-04: `confidence_score = 0.2` for Tier 1.

**Tier 2 — Pooled Priors**
- D-05: Pooled prior = mean daily quantity per product across all other merchants with ≥14
  days history, blended with the merchant's own partial history via `n/(n+14)` shrinkage.
- D-06: `confidence_score` scales linearly from 0.3 (1 day) to 0.6 (13 days).

**Tier 3 — LightGBM Forecast**
- D-07: Reuse existing `forecasting.tree_models` / `forecasting.pipeline` LightGBM plumbing.
  Wrap with a `RecommendationEngine` façade.
- D-08: Feed the LightGBM forecast into `optimization.newsvendor` to convert expected demand
  into an order quantity.
- D-09: `confidence_score` derived from forecast interval width or quantile coverage, clipped
  to [0.6, 0.95].

**Model Loading (INFRA-01)**
- D-10: Add `src/meshek_ml/service/lifespan.py` exposing an `async contextmanager` compatible
  with FastAPI lifespan. Loads a single shared LightGBM model at startup; tears down at
  shutdown.
- D-11: Model path resolved via env var `MESHEK_MODEL_PATH` with a sensible default under
  `models/`.
- D-12: FastAPI app wiring is Phase 8. Phase 6 only provides the reusable lifespan factory
  and verifies it works with a bare `FastAPI()` smoke test.

**Response Shape (REC-04)**
- D-13: `RecommendationResponse` fields: `merchant_id: str`, `recommendations:
  list[ProductRecommendation]`, `reasoning_tier: Literal["category_default","pooled_prior",
  "ml_forecast"]`, `confidence_score: float`, `generated_at: datetime`.
- D-14: `ProductRecommendation` = `{product_id, quantity, unit}`.

**Code Location**
- D-15: `src/meshek_ml/recommendation/` — `engine.py`, `tiers.py`, `schema.py`, `config.py`.
- D-16: `src/meshek_ml/service/` — `lifespan.py`, `state.py`.

**Testing**
- D-17: Unit tests per tier (0, 7, 30 days). Integration test exercising all three tiers.
  Lifespan test uses FastAPI `TestClient` with a bare app.

### Claude's Discretion

- Confidence score formulas within the locked ranges
- Internal module layout within `recommendation/` and `service/`
- LightGBM hyperparameters and model file format (joblib or LightGBM native `txt`)
- Pooled-prior shrinkage exact weighting
- Category defaults YAML schema

### Deferred Ideas (OUT OF SCOPE)

- REC-05 (async retrain endpoint) — v1.2+
- REC-06 (hdate Hebrew calendar)
- REC-07 (per-product asymmetric costs in request)
- HTTP endpoints — Phase 8
- Docker container — Phase 8 (INFRA-02)

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REC-01 | New merchant (0 days) → category defaults | Tier 1 design (§Tiers, YAML config loader pattern) |
| REC-02 | Limited history (1-13 days) → pooled priors | Tier 2 design (`PooledStore` scan + shrinkage) |
| REC-03 | ≥14 days → LightGBM forecast | Reuse `forecasting.pipeline` features + `tree_models.train_lightgbm` + `newsvendor.optimal_order_normal` |
| REC-04 | Every response has `reasoning_tier` + `confidence_score` | Pydantic `RecommendationResponse` schema (§Response Shape) |
| INFRA-01 | LightGBM loads once at startup via lifespan | FastAPI `asynccontextmanager` lifespan pattern (§Lifespan) |

## Standard Stack

### Core (already in project — versions verified)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| lightgbm | ≥4.0 (declared) | Tier 3 forecasting | Already in `[forecasting]` extra and used by `tree_models.py` [VERIFIED: pyproject.toml] |
| pandas | ≥2.0 | DataFrame I/O contract across pipeline | Already the lingua franca of `MerchantStore.read_sales` and `forecasting.pipeline` [VERIFIED: pyproject.toml] |
| pydantic | ≥2.0 | Response schemas, config models | Already used for `MerchantProfile`; Phase 5 pattern [VERIFIED: pyproject.toml] |
| scipy | ≥1.11 | `newsvendor.optimal_order_normal` uses `scipy.stats.norm.ppf` | Already used by `optimization.newsvendor` [VERIFIED: optimization/newsvendor.py] |
| PyYAML | transitive via hydra-core | Tier 1 category-defaults YAML loader | `hydra-core>=1.3` already pulls pyyaml; `omegaconf` also available [VERIFIED: pyproject.toml] |

### New (Phase 6 must add)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.135.3 | Lifespan factory (INFRA-01) | Current stable on PyPI 2026-04-01 [VERIFIED: `curl https://pypi.org/pypi/fastapi/json` → 0.135.3]. Already in uv.lock transitively via gradio, but NOT a direct dep — must be declared. |
| httpx | latest stable | `TestClient` transport for lifespan integration test | FastAPI `TestClient` wraps it; standard testing dep [CITED: fastapi.tiangolo.com/advanced/testing-events] |
| joblib | ≥1.3 | LightGBM model persistence | Cleanest persistence for an sklearn-API `LGBMRegressor` (which is what `tree_models.train_lightgbm` returns) [CITED: scikit-learn.org/stable/model_persistence.html]. Alternative: `model.booster_.save_model(path)` then `lgb.Booster(model_file=path)` — native LightGBM `txt` format is smaller and forward-compatible but loses the sklearn wrapper. **Recommendation: joblib** for simplicity unless deployment constraints force native format. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| joblib persistence | LightGBM native `booster.save_model("model.txt")` + `Booster(model_file=...)` | Smaller file, forward-compat across LightGBM versions, but you lose the `LGBMRegressor` wrapper and must call `booster.predict()` instead of `model.predict()`. Pick joblib unless Phase 8 deployment rejects it. |
| Filesystem scan in `PooledStore` | A global `merchants.sqlite` registry DB | Would violate Phase 5 D-01 (no global registry) and add a second source of truth. Filesystem scan is the consistent choice. |
| Reuse `run_forecast_pipeline` as-is | Extract a `train_and_save` + `load_and_predict` pair | The existing pipeline trains and **returns metrics** — it has no save hook. A thin wrapper that calls the same feature-engineering steps then persists is the minimum viable change. Do not modify `pipeline.py` public API. |

**Installation:**
```bash
# Add to pyproject.toml under a new [project.optional-dependencies] group
# (do NOT drop into core deps — service layer is optional)
service = [
    "fastapi>=0.135,<0.136",
    "httpx>=0.27",
    "joblib>=1.3",
]
```

**Version verification:**
- `fastapi 0.135.3` — verified via `curl https://pypi.org/pypi/fastapi/json` on 2026-04-14,
  published 2026-04-01. [VERIFIED: pypi registry]
- `lightgbm>=4.0` — already declared. [VERIFIED: pyproject.toml line 31]
- `joblib` — standard sklearn companion; pin `>=1.3` (permissive). [ASSUMED: not verified this session]

## Architecture Patterns

### Recommended Package Layout

```
src/meshek_ml/
├── recommendation/
│   ├── __init__.py          # re-export RecommendationEngine, RecommendationResponse
│   ├── schema.py            # pydantic: ProductRecommendation, RecommendationResponse
│   ├── config.py            # CategoryDefaultsConfig + YAML loader
│   ├── tiers.py             # tier_1_category, tier_2_pooled, tier_3_lightgbm functions
│   ├── pooled_store.py      # filesystem scan + cross-merchant aggregation
│   └── engine.py            # RecommendationEngine façade + tier-routing recommend()
├── service/
│   ├── __init__.py          # re-export lifespan, AppState
│   ├── state.py             # AppState dataclass (holds loaded model + metadata)
│   └── lifespan.py          # async contextmanager factory
configs/
└── recommendation/
    └── category_defaults.yaml   # new file — Tier 1 source of truth
models/
└── .gitkeep                 # model artifacts; .gitignore the actual files
```

### Pattern 1: FastAPI Lifespan Factory (INFRA-01)

**What:** An `@asynccontextmanager` async function that receives the FastAPI `app` instance,
loads state before `yield`, and tears it down after. Phase 6 ships the **factory**; Phase 8
calls `FastAPI(lifespan=lifespan_factory(...))`.

**When to use:** Any expensive resource (ML model, DB pool) that must be loaded exactly once
per process and live as long as the app. This is the officially recommended replacement for
the deprecated `@app.on_event("startup"/"shutdown")` pattern.
[CITED: fastapi.tiangolo.com/advanced/events/]

**Canonical shape:**
```python
# src/meshek_ml/service/lifespan.py
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import joblib
from fastapi import FastAPI

from meshek_ml.service.state import AppState

DEFAULT_MODEL_PATH = Path("models/lightgbm_v1.joblib")

def build_lifespan(model_path: Path | None = None):
    """Return an async contextmanager bound to a specific model path.

    Factory pattern lets Phase 8 pass a deploy-specific path, and lets tests
    pass a tmp_path-constructed model without touching env state.
    """
    resolved = (
        model_path
        or Path(os.environ.get("MESHEK_MODEL_PATH", DEFAULT_MODEL_PATH))
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if not resolved.exists():
            raise RuntimeError(
                f"Model file not found at {resolved}. "
                f"Set MESHEK_MODEL_PATH or train a model first."
            )
        model = joblib.load(resolved)
        app.state.ml = AppState(model=model, model_path=resolved)
        try:
            yield
        finally:
            # LightGBM has no explicit close; drop the reference so GC can run
            app.state.ml = None

    return lifespan
```

**Testing lifespan without a live server:** Use `TestClient` as a context manager —
entering the `with` block triggers lifespan startup, exit triggers shutdown.
```python
# tests/service/test_lifespan.py
from fastapi import FastAPI
from fastapi.testclient import TestClient

def test_lifespan_loads_model(tmp_path, trained_model):
    model_path = tmp_path / "m.joblib"
    joblib.dump(trained_model, model_path)

    app = FastAPI(lifespan=build_lifespan(model_path=model_path))
    with TestClient(app) as client:
        # Inside the `with` block, lifespan startup has completed
        assert app.state.ml is not None
        assert app.state.ml.model is trained_model
    # After the `with` block, lifespan teardown has run
```
[CITED: fastapi.tiangolo.com/advanced/testing-events/]

### Pattern 2: Tier Router in the Engine Façade

```python
# src/meshek_ml/recommendation/engine.py
class RecommendationEngine:
    def __init__(
        self,
        store_factory,          # callable: merchant_id -> MerchantStore
        pooled_store,           # PooledStore (filesystem scan)
        model,                  # loaded LGBMRegressor or None
        category_defaults,      # CategoryDefaultsConfig
    ):
        ...

    def recommend(self, merchant_id: str) -> RecommendationResponse:
        with self._store_factory(merchant_id, must_exist=True) as store:
            sales = store.read_sales()
            n_days = sales["date"].nunique() if not sales.empty else 0

            if n_days == 0:
                return tier_1_category_defaults(merchant_id, self._category_defaults)
            if n_days < 14:
                return tier_2_pooled_priors(
                    merchant_id, sales, self._pooled_store, n_days
                )
            return tier_3_lightgbm(merchant_id, sales, self._model)
```

**Why a factory, not an instance, of MerchantStore:** the engine must not own a long-lived
connection; Phase 5 short-lived short-connection pattern is the contract.

### Pattern 3: PooledStore Filesystem Scan

```python
# src/meshek_ml/recommendation/pooled_store.py
from meshek_ml.storage.merchant_store import MerchantStore, _data_root  # or public helper

class PooledStore:
    """Cross-merchant aggregation over MESHEK_DATA_DIR/*.sqlite files."""

    MIN_HISTORY_DAYS_FOR_PRIOR = 14

    def list_merchant_ids(self) -> list[str]:
        root = _data_root()  # prefer exposing a public get_data_root() helper
        return sorted(p.stem for p in root.glob("*.sqlite"))

    def pooled_mean_by_product(
        self, exclude_merchant_id: str
    ) -> dict[str, float]:
        """Mean daily quantity per product across all OTHER merchants with
        ≥ MIN_HISTORY_DAYS_FOR_PRIOR distinct sale dates."""
        ...
```

**CRITICAL:** The filesystem scan should not call `_data_root()` (private). Phase 6 plan
should also add a tiny public helper `storage.get_data_root()` to the `storage` package to
keep the import boundary clean. This is a 3-line additive change to Phase 5 code.

### Pattern 4: Tier 3 — Reuse features.py, not the pipeline

`run_forecast_pipeline` trains AND evaluates with a hardcoded `train_end_date="2024-06-30"`
default. It cannot be called for inference. The right approach for Tier 3 at recommend-time:

1. Build features from the merchant's recent sales using the existing
   `add_lag_features` + `add_rolling_features` + `add_calendar_features` directly.
2. Take the last-available row (tomorrow's feature row, with lags filled from today).
3. `model.predict(X_last)` → expected demand per product.
4. Estimate σ from training residuals (see Pitfall 4 below).
5. `optimal_order_normal(mean, std, underage, overage)` per product.

This keeps training (offline, once) separate from inference (per-request, fast).

### Anti-Patterns to Avoid

- **Retraining on every `/recommend` call.** Explicitly forbidden by REQUIREMENTS.md
  "Out of Scope" row ("Synchronous model retraining on /recommend"). Training is a
  one-time offline step in Phase 6; `/retrain` is REC-05, deferred.
- **Loading the model per request.** INFRA-01's whole purpose is to forbid this. Tests must
  assert that `RecommendationEngine` holds a reference and does not touch disk per call.
- **Global `_data_root()` reach-in.** Private helper. Add `storage.get_data_root()` (a
  one-liner re-export) and depend on that.
- **Computing "n days of history" via `len(sales)`.** A merchant with 30 products over 3 days
  has 90 rows but only 3 distinct dates. Always use `sales["date"].nunique()`. This matches
  D-01 "distinct sale dates".
- **Using `run_forecast_pipeline` for inference.** It's a train+evaluate entry point; it
  rebuilds a val split and returns metrics. Inference needs a different code path.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Model persistence | Custom serialize-to-disk helper | `joblib.dump` / `joblib.load` | Handles sklearn estimators including `LGBMRegressor` out of the box; the scikit-learn recommended way. [CITED: scikit-learn.org/stable/model_persistence.html] |
| Async resource lifecycle | `@app.on_event("startup")` + module globals | `contextlib.asynccontextmanager` + FastAPI `lifespan=` | `on_event` is deprecated. Lifespan is the canonical API. [CITED: fastapi.tiangolo.com/advanced/events/] |
| Order-quantity derivation | Custom Q = μ × (1 + safety%) heuristic | `optimization.newsvendor.optimal_order_normal` | Already ships in Phase 3. Reuse with standard underage/overage costs. |
| Feature engineering for inference | Re-implement lag/rolling from sales rows | `forecasting.features.add_lag_features` + siblings | Identical feature set to training = no train/serve skew. |
| Schema validation | Ad-hoc column checks | `forecasting.schema.validate_demand_schema` | Phase 5 already reuses this contract; keeps the whole pipeline aligned. |
| Cross-merchant listing | Global DB registry | Filesystem scan of `MESHEK_DATA_DIR/*.sqlite` | Matches Phase 5 D-01 "filesystem-as-registry"; zero new infrastructure. |

**Key insight:** The temptation in Phase 6 is to "build an ML service." The work is almost
entirely wiring existing assets — the ML is already written. Resist writing anything that
starts with "let me reimplement …".

## Runtime State Inventory

*Not applicable — Phase 6 is greenfield additive (new packages, no renames/migrations).*

## Common Pitfalls

### Pitfall 1: NaN feature rows on low-history merchants
**What goes wrong:** `add_lag_features` and `add_rolling_features` produce NaNs for the first
~28 rows of each merchant/product. A merchant with exactly 14 days has almost no usable
rolling-28 values.
**Why it happens:** The lag/rolling features were designed for training with many months of
data, not for day-of inference on a 14-day history.
**How to avoid:** For Tier 3 inference, select *only* the features actually populated at day N.
Either (a) shorten the lags to `[1, 7]` for a low-history model, (b) impute NaN with a per-
product mean, or (c) require ≥28 days for Tier 3 and move 14-27 into Tier 2. **Recommendation:**
impute with per-product running mean. Document the choice in the tier selection logic.
**Warning signs:** `model.predict()` returns NaN, or LightGBM complains about input dtype.

### Pitfall 2: Confidence score with no calibration
**What goes wrong:** D-09 says "derived from forecast interval width or quantile coverage"
but `LGBMRegressor` with `objective='regression'` (the current default in `tree_models.py`)
produces **point estimates only** — no intervals, no quantiles.
**Why it happens:** Quantile regression requires `objective='quantile', alpha=0.1` (and a
second model for `alpha=0.9`).
**How to avoid:** Simplest defensible signal for v1.1 = training residual std. After training:
compute `residual_std = np.std(y_train - model.predict(x_train))`. Persist it alongside the
model. Confidence = `clip(1 - residual_std / y_mean, 0.6, 0.95)`. Document this as a
placeholder until quantile forecasting lands in v1.2.
**Warning signs:** Confidence score is constant across merchants → you forgot to personalize
it to the merchant's sales volume.

### Pitfall 3: Lifespan factory that hardcodes a module-level model global
**What goes wrong:** Test isolation breaks — one test loads a model into a module global, the
next test sees it.
**Why it happens:** Easy to write `_MODEL = None` at module scope and assign to it in lifespan.
**How to avoid:** Always attach state to `app.state.ml`. Tests create their own `FastAPI()`
instance per test, so state is naturally per-app.
**Warning signs:** Flaky lifespan tests under parallel pytest-xdist.

### Pitfall 4: Empty-DataFrame `.dt` dereference
**What goes wrong:** `MerchantStore.read_sales()` runs `parse_dates=["date"]` and WR-01 coerces
to `datetime64[ns]`. But downstream code that does `sales["date"].dt.date` crashes on empty
DataFrames if dtype coercion did not fire.
**Why it happens:** Empty DataFrame edge case.
**How to avoid:** Branch on `sales.empty` **first**, then compute `nunique()`. Never dereference
`.dt` on empty.
**Warning signs:** Tier 1 integration test passes but real 0-day merchant returns 500.

### Pitfall 5: Filesystem scan picks up WAL/journal sidecar files
**What goes wrong:** `MerchantStore` uses `PRAGMA journal_mode = WAL`, so you get
`shop_a.sqlite`, `shop_a.sqlite-wal`, `shop_a.sqlite-shm` on disk. A naive `glob("*.sqlite*")`
picks them all up.
**Why it happens:** WAL mode creates sidecars.
**How to avoid:** Scan for exactly `*.sqlite` (no trailing wildcard). `Path.glob("*.sqlite")`
will not match `.sqlite-wal` because the pattern requires exact suffix.
**Warning signs:** `list_merchant_ids()` returns duplicates or strings ending in `-wal`.

### Pitfall 6: Training data source mismatch
**What goes wrong:** The Phase 6 plan trains on synthetic data from
`simulation.generator.run_simulation`, but production will have real merchant data. Model
artifacts shipped with the repo bake in the synthetic distribution.
**Why it happens:** No real data exists yet at v1.1.
**How to avoid:** The Phase 6 plan must explicitly document that `models/lightgbm_v1.joblib`
is a **placeholder trained on synthetic data**, valid for API contract verification, not
production forecasting accuracy. Retraining with real data happens post-deployment.
**Warning signs:** None at Phase 6 — this is a v1.2 concern to log, not fix.

## Code Examples

### Example 1: Tier 1 — Category Defaults
```python
# src/meshek_ml/recommendation/tiers.py
from datetime import datetime, timezone

from meshek_ml.recommendation.schema import (
    ProductRecommendation,
    RecommendationResponse,
)
from meshek_ml.recommendation.config import CategoryDefaultsConfig


def tier_1_category_defaults(
    merchant_id: str, cfg: CategoryDefaultsConfig
) -> RecommendationResponse:
    recs = [
        ProductRecommendation(
            product_id=p.product_id, quantity=p.default_quantity, unit=p.unit
        )
        for p in cfg.products
    ]
    return RecommendationResponse(
        merchant_id=merchant_id,
        recommendations=recs,
        reasoning_tier="category_default",
        confidence_score=0.2,  # D-04
        generated_at=datetime.now(timezone.utc),
    )
```

### Example 2: Tier 2 — Pooled Prior with Shrinkage
```python
def tier_2_pooled_priors(
    merchant_id: str,
    own_sales: pd.DataFrame,
    pooled: PooledStore,
    n_days: int,
) -> RecommendationResponse:
    pooled_means = pooled.pooled_mean_by_product(exclude_merchant_id=merchant_id)
    own_means = own_sales.groupby("product")["quantity"].mean().to_dict()

    shrink = n_days / (n_days + 14)  # D-05
    recs: list[ProductRecommendation] = []
    for product, pooled_mean in pooled_means.items():
        own_mean = own_means.get(product, pooled_mean)
        q = shrink * own_mean + (1 - shrink) * pooled_mean
        recs.append(
            ProductRecommendation(
                product_id=product, quantity=round(q, 1), unit="kg"
            )
        )

    confidence = 0.3 + (0.6 - 0.3) * ((n_days - 1) / 12)  # D-06 linear 0.3→0.6
    return RecommendationResponse(
        merchant_id=merchant_id,
        recommendations=recs,
        reasoning_tier="pooled_prior",
        confidence_score=round(confidence, 3),
        generated_at=datetime.now(timezone.utc),
    )
```

### Example 3: Tier 3 — LightGBM + Newsvendor
```python
from meshek_ml.forecasting.features import (
    add_calendar_features,
    add_lag_features,
    add_rolling_features,
)
from meshek_ml.optimization.newsvendor import optimal_order_normal


def tier_3_lightgbm(
    merchant_id: str,
    sales: pd.DataFrame,
    model,                      # loaded LGBMRegressor
    residual_std: float,        # persisted with the model
    underage_cost: float = 2.0,
    overage_cost: float = 1.0,
) -> RecommendationResponse:
    df = sales.copy()
    df = add_lag_features(df, target_col="quantity")
    df = add_rolling_features(df, target_col="quantity")
    df = add_calendar_features(df)

    # Last row per product is "tomorrow's" feature vector
    last_rows = df.sort_values("date").groupby("product").tail(1)
    feature_cols = [c for c in last_rows.columns
                    if c not in ("date", "merchant_id", "product", "quantity")]
    X = last_rows[feature_cols].fillna(
        last_rows[feature_cols].mean()  # Pitfall 1 mitigation
    )
    mu = model.predict(X)

    recs = []
    for (product, mean_demand) in zip(last_rows["product"], mu):
        q = optimal_order_normal(
            mean_demand=float(mean_demand),
            std_demand=float(residual_std),
            underage_cost=underage_cost,
            overage_cost=overage_cost,
        )
        recs.append(ProductRecommendation(
            product_id=product, quantity=round(q, 1), unit="kg"
        ))

    y_mean = float(sales["quantity"].mean()) or 1.0
    raw = 1.0 - residual_std / y_mean
    confidence = max(0.6, min(0.95, raw))

    return RecommendationResponse(
        merchant_id=merchant_id,
        recommendations=recs,
        reasoning_tier="ml_forecast",
        confidence_score=round(confidence, 3),
        generated_at=datetime.now(timezone.utc),
    )
```

### Example 4: Training entry point that saves a model
```python
# src/meshek_ml/recommendation/train_model.py (new)
import joblib
import numpy as np
from meshek_ml.forecasting.pipeline import FEATURE_COLS_TO_DROP, TARGET_COL
from meshek_ml.forecasting.features import (
    add_calendar_features, add_lag_features, add_rolling_features,
)
from meshek_ml.forecasting.schema import (
    normalize_simulation_data, validate_demand_schema,
)
from meshek_ml.forecasting.tree_models import train_lightgbm


def train_and_save(output_path: Path, data: pd.DataFrame) -> None:
    if "realized_demand" in data.columns:
        data = normalize_simulation_data(data)
    df = validate_demand_schema(data)
    df = add_lag_features(df, target_col="quantity")
    df = add_rolling_features(df, target_col="quantity")
    df = add_calendar_features(df).dropna()

    feature_cols = [c for c in df.columns if c not in FEATURE_COLS_TO_DROP]
    model = train_lightgbm(df[feature_cols], df[TARGET_COL].values)
    residual_std = float(np.std(df[TARGET_COL].values - model.predict(df[feature_cols])))

    joblib.dump({"model": model, "residual_std": residual_std,
                 "feature_cols": feature_cols}, output_path)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup"/"shutdown")` | `FastAPI(lifespan=async_context_manager)` | FastAPI 0.93+ (2023), deprecation notice added 0.100+ | Phase 6 must use lifespan; `on_event` would trip deprecation warnings and miss test-client integration. [CITED: fastapi.tiangolo.com/advanced/events/] |
| Custom serialization for sklearn | `joblib.dump(model, path)` | sklearn has recommended joblib for years | Safer, faster for numpy-heavy objects. |
| Point-estimate regression + heuristic safety stock | Quantile regression (LightGBM `objective="quantile"`) for direct interval | LightGBM 3.0+ | v1.2 upgrade path for confidence score. Not in v1.1 scope. |

**Deprecated/outdated:**
- `on_event` startup/shutdown — do not introduce new usages.
- `realized_demand` column name — `normalize_simulation_data` converts to `quantity` already;
  Phase 6 code should only speak in `quantity`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `joblib>=1.3` is a safe lower bound and no breaking changes block us | Standard Stack | Low — joblib has been API-stable; worst case bump bound |
| A2 | Residual-std-based confidence score is "defensible enough" for v1.1 | Pitfall 2, Example 3 | Medium — if meshek app surfaces the score visually, users may misread it. Flag in SUMMARY. |
| A3 | Training data for the v1 model artifact will be `simulation.generator.run_simulation` output | Pitfall 6 | Medium — baked-in distribution bias until first real-data retraining in v1.2 |
| A4 | Default underage/overage cost ratio of 2:1 is acceptable for the Phase 6 placeholder | Example 3 | Low — matches newsvendor conventions; trivially tunable |
| A5 | `Path.glob("*.sqlite")` does NOT match `-wal`/`-shm` sidecars | Pitfall 5 | Low — verified by fnmatch semantics; would be caught by a unit test |

## Open Questions (RESOLVED)

1. **Category defaults YAML shape — per-category or flat per-product?**
   - **RESOLVED:** Ship `configs/recommendation/category_defaults.yaml` with a flat
     `products:` list for v1.1. Phase 7 will migrate this to category-keyed defaults once
     the Hebrew parser produces canonical product→category mappings. Locked in Plan 01.

2. **Where do underage/overage costs come from for Tier 3?**
   - **RESOLVED:** Hardcoded constants `underage=2.0`, `overage=1.0` in `tiers.py` for
     v1.1, with a module-level comment referencing REC-07 for future per-request costs.
     Locked in Plan 03.

3. **Should `storage.get_data_root()` be publicly exported?**
   - **RESOLVED:** Yes — a 3-line public `get_data_root()` wrapper is added to
     `storage/merchant_store.py` and re-exported from `storage/__init__.py`. Additive,
     no risk. Locked in Plan 01.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | ✓ | ≥3.10 | — |
| lightgbm | Tier 3 training + inference | ✓ (declared in `[forecasting]`) | ≥4.0 | — |
| pandas | Throughout | ✓ | ≥2.0 | — |
| scipy | newsvendor | ✓ | ≥1.11 | — |
| pydantic | schemas | ✓ | ≥2.0 | — |
| fastapi | Lifespan factory | ✗ (only transitive via gradio) | 0.135.3 available | Add to `[project.optional-dependencies].service` |
| httpx | TestClient | ✗ as direct dep | — | Add to same `service` extra (TestClient imports it) |
| joblib | Model persistence | ✗ as direct dep | — | Add to `service` extra |

**Missing dependencies with no fallback:** None — all can be added as a new `service`
optional-extra in `pyproject.toml`.

**Missing dependencies with fallback:** None blocking.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.4+ with pytest-cov, markers `slow` and `integration` |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` + existing `tests/conftest.py` |
| Quick run command | `pytest tests/recommendation tests/service -q --no-cov` |
| Full suite command | `pytest -q --no-cov` (69 tests currently green post Phase 5) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| REC-01 | 0-day merchant → `reasoning_tier == "category_default"` | unit | `pytest tests/recommendation/test_tier_1.py -x` | ❌ Wave 0 |
| REC-02 | 7-day merchant → `reasoning_tier == "pooled_prior"` and `confidence_score` in [0.3, 0.6] | unit | `pytest tests/recommendation/test_tier_2.py -x` | ❌ Wave 0 |
| REC-02 | Pooled prior actually aggregates across *other* merchants (excludes self) | unit | `pytest tests/recommendation/test_pooled_store.py::test_excludes_self -x` | ❌ Wave 0 |
| REC-03 | 30-day merchant → `reasoning_tier == "ml_forecast"` with non-negative quantities | integration | `pytest tests/recommendation/test_tier_3.py -x -m integration` | ❌ Wave 0 |
| REC-03 | Loaded model produces finite predictions on a synthetic merchant feature matrix | integration | `pytest tests/recommendation/test_tier_3.py::test_predict_no_nan` | ❌ Wave 0 |
| REC-04 | Every `RecommendationResponse` has non-null `reasoning_tier` and `confidence_score` | unit | `pytest tests/recommendation/test_schema.py::test_required_fields` | ❌ Wave 0 |
| REC-04 | Confidence bounds per tier are enforced (0.2 / [0.3,0.6] / [0.6,0.95]) | unit | `pytest tests/recommendation/test_engine.py::test_confidence_bounds` | ❌ Wave 0 |
| INFRA-01 | Model loads exactly once during lifespan startup; `app.state.ml` is populated | integration | `pytest tests/service/test_lifespan.py::test_loads_on_startup` | ❌ Wave 0 |
| INFRA-01 | Lifespan raises on missing model file (fail-fast) | unit | `pytest tests/service/test_lifespan.py::test_missing_model_file` | ❌ Wave 0 |
| INFRA-01 | Recommend path does NOT open the model file per request (mock disk, assert called-once) | integration | `pytest tests/service/test_lifespan.py::test_model_not_reloaded` | ❌ Wave 0 |
| Success #5 (ROADMAP) | End-to-end `engine.recommend()` walks all three tiers across three synthetic merchants (0, 7, 30 days) | integration | `pytest tests/recommendation/test_engine_e2e.py -x -m integration` | ❌ Wave 0 |

### Sampling Rate (Nyquist Validation)

The five ROADMAP success criteria collapse to 3 observable axes — tier routing, response
contract, and startup loading. Each axis needs at least two independent samples to pass
Nyquist (one positive, one boundary/negative):

- **Axis A — Tier routing (ROADMAP success 1, 2, 3):** sample at n_days = 0, 13 (upper edge
  of Tier 2), 14 (lower edge of Tier 3), 30. Four samples cover both boundaries plus the
  interior of Tier 1 and Tier 3. This is the minimum sampling that can detect an off-by-one
  in tier selection.
- **Axis B — Response contract (ROADMAP success 4):** every tier test asserts the full
  `RecommendationResponse` pydantic model round-trips and contains `reasoning_tier` and
  `confidence_score` in the documented range. Sampled in all three tier unit tests plus the
  engine confidence-bounds test (≥4 positive samples).
- **Axis C — Lifespan startup (ROADMAP success 5, INFRA-01):** sample at (1) happy path —
  file exists, loads, `app.state.ml` non-null; (2) fail-fast — file missing, raises;
  (3) inference isolation — a second recommend call does not reopen the file (mocked
  `joblib.load` asserted called exactly once across N calls).

**Per-task commit:** `pytest tests/recommendation tests/service -q --no-cov` — fast, under
5 seconds once Tier 3 uses a session-scoped pre-trained fixture model.

**Per-wave merge:** `pytest -q --no-cov` — full 69+ test regression to prove Phase 5 stays
green.

**Phase gate:** Full suite green + `test_engine_e2e` passes covering all three tiers in one
run.

### Wave 0 Gaps

- [ ] `tests/recommendation/__init__.py` — package marker
- [ ] `tests/recommendation/conftest.py` — shared fixtures:
    - `trained_lightgbm_model` — trains once via `train_and_save` against synthetic data,
      session-scoped to avoid retraining per test
    - `merchant_store_factory` — writes N days of sales into a tmp_path-rooted store
    - `populated_data_root` — creates 3 merchants (0, 7, 30 days) for Tier 2 aggregation tests
- [ ] `tests/recommendation/test_schema.py` — pydantic model contract
- [ ] `tests/recommendation/test_tier_1.py` — category defaults
- [ ] `tests/recommendation/test_tier_2.py` — pooled prior shrinkage
- [ ] `tests/recommendation/test_tier_3.py` — LightGBM inference path (marked `integration`)
- [ ] `tests/recommendation/test_pooled_store.py` — filesystem scan + WAL-sidecar safety
- [ ] `tests/recommendation/test_engine.py` — tier-router behavior + confidence bounds
- [ ] `tests/recommendation/test_engine_e2e.py` — end-to-end across all three tiers
- [ ] `tests/service/__init__.py`
- [ ] `tests/service/test_lifespan.py` — lifespan startup/shutdown via `TestClient`
- [ ] `tests/service/conftest.py` — `model_path` fixture (joblib-dumped trained model)
- [ ] `configs/recommendation/category_defaults.yaml` — Tier 1 source of truth fixture
- [ ] `pyproject.toml` — add `service` extra with `fastapi`, `httpx`, `joblib`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no (Phase 8 concern) | — |
| V3 Session Management | no (stateless) | — |
| V4 Access Control | partial | `merchant_id` whitelist already enforced by `MerchantStore._validate_merchant_id` (reused transitively) |
| V5 Input Validation | yes | Pydantic response schema; `merchant_id` re-validated by calling `MerchantStore(merchant_id, must_exist=True)` |
| V6 Cryptography | no | Model artifact is not secret material |
| V12 File/Resources | yes | `MESHEK_MODEL_PATH` must not be a caller-controlled value — it is an env var read once at startup. Filesystem scan in `PooledStore` must anchor to `_data_root()` to inherit Phase 5's path-traversal defense. |

### Known Threat Patterns for Phase 6

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `merchant_id` in `PooledStore.list_merchant_ids` | Tampering / Info Disclosure | Use `Path.glob("*.sqlite")` anchored to validated `_data_root()`; strip with `.stem`; re-validate each stem through `_validate_merchant_id` before opening a store |
| Loading a malicious joblib model file (joblib uses Python object serialization under the hood) | Remote code execution (Tampering) | Only load from a path controlled by the deploy environment (`MESHEK_MODEL_PATH`). Document in SUMMARY that model files are trusted build artifacts, not user uploads. REC-05 (retrain endpoint) will revisit this — deferred. |
| Denial of service via huge merchant history at inference time | DoS | For v1.1 volumes (one shop, <365 days), negligible. Accept and document. |
| Cross-merchant data leak via pooled prior | Info Disclosure | `pooled_mean_by_product(exclude_merchant_id=…)` must explicitly exclude the requesting merchant. Test coverage mandatory (`test_excludes_self`). |
| Confidence score leaks training residuals | Info Disclosure | The `residual_std` is a scalar derived from aggregate training data; not PII. Accept. |

## Project Constraints (from CLAUDE.md)

No project-level `./CLAUDE.md` file exists. Global user `CLAUDE.md` mandates automated
verification; the Phase 6 plan must include self-verification steps (run pytest, run
lifespan integration test) and must not ask the user to verify manually. No
`.claude/skills/` or `.agents/skills/` directory present either.

## Sources

### Primary (HIGH confidence)
- `src/meshek_ml/storage/merchant_store.py` — read in full; confirms short-lived connection
  contract, private `_data_root()`, whitelist, WAL mode
- `src/meshek_ml/forecasting/pipeline.py` — read in full; confirms `run_forecast_pipeline` is
  train+eval only (no save), uses `TARGET_COL="quantity"` and `FEATURE_COLS_TO_DROP`
- `src/meshek_ml/forecasting/tree_models.py` — read in full; `train_lightgbm` returns
  `LGBMRegressor`
- `src/meshek_ml/forecasting/features.py` — read in full; confirms lag/rolling/calendar
  helpers reusable at inference
- `src/meshek_ml/forecasting/schema.py` — read in full; canonical contract
- `src/meshek_ml/optimization/newsvendor.py` — read in full; `optimal_order_normal` signature
- `pyproject.toml` + `uv.lock` — confirm version availability
- `https://pypi.org/pypi/fastapi/json` — fastapi 0.135.3 (published 2026-04-01)
- `.planning/phases/05-data-foundation/05-VERIFICATION.md` — Phase 5 shipped 11/11 truths,
  35/35 storage tests green

### Secondary (MEDIUM confidence — cited, not loaded this session)
- FastAPI lifespan events: https://fastapi.tiangolo.com/advanced/events/
- FastAPI testing with events: https://fastapi.tiangolo.com/advanced/testing-events/
- scikit-learn model persistence (joblib recommendation):
  https://scikit-learn.org/stable/model_persistence.html

### Tertiary (LOW confidence / assumed)
- Exact joblib lower bound `>=1.3` is an assumption — trivial to bump.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every library inspected in pyproject.toml / uv.lock; fastapi version verified against PyPI
- Architecture: HIGH — read all target integration points directly
- Pitfalls: HIGH — NaN feature problem and empty-DataFrame edge case both observable in the Phase 5 code
- Validation: HIGH — existing test framework and patterns fully inspected

**Research date:** 2026-04-14
**Valid until:** 2026-05-14 (30 days; FastAPI + LightGBM are stable)
