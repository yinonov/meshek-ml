# Phase 12: wire-contract — Pattern Map

**Mapped:** 2026-05-04
**Files analyzed:** 10
**Analogs found:** 10 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/meshek_ml/recommendation/schema.py` | model | request-response | `src/meshek_ml/service/schemas.py` | exact (Pydantic v2, same project conventions) |
| `src/meshek_ml/recommendation/tiers.py` | service | request-response | self (existing file, surgical edits) | exact |
| `src/meshek_ml/recommendation/__init__.py` | config | — | self (no-op — Signal NOT added to re-exports) | exact |
| `src/meshek_ml/service/schemas.py` | model | request-response | self (single-line version bump) | exact |
| `tests/recommendation/test_schema.py` | test | request-response | self (full rewrite of helper + 4 test functions) | exact |
| `tests/recommendation/test_tier_1.py` | test | request-response | self (inline assertion migration) | exact |
| `tests/recommendation/test_tier_2.py` | test | request-response | self (inline assertion migration) | exact |
| `tests/recommendation/test_tier_3.py` | test | request-response | self (inline assertion migration + rename) | exact |
| `tests/recommendation/test_engine.py` | test | request-response | self (per-line assertion migration) | exact |
| `tests/service/test_recommend.py` | test | request-response | self (per-line migration + 2 new test functions) | exact |

---

## Pattern Assignments

### `src/meshek_ml/recommendation/schema.py` (model, request-response)

**Analog:** `src/meshek_ml/service/schemas.py` — same project, same Pydantic v2 conventions.

**Imports pattern** (schema.py current lines 1–12 / service/schemas.py lines 1–10):
```python
# Current schema.py — keep this header exactly:
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator
```
Add `model_validator` to the existing `from pydantic import BaseModel, Field` line (line 12 of current schema.py). No other imports change.

**Existing `ReasoningTier` alias to keep** (schema.py line 14):
```python
ReasoningTier = Literal["category_default", "pooled_prior", "ml_forecast"]
```

**New `Signal` model — insert before `ProductRecommendation`:**
```python
class Signal(BaseModel):
    """A single explanation signal for a recommendation line (WIRE-04)."""

    name: str
    """Stable signal name. Open str in v1.2; tightened to Literal in Phase 14.
    Documented stable values: "category_default", "pooled_prior", "ml_forecast"."""

    contribution: float
    """Signed contribution in demand units (kg). Raw demand scale, not normalized."""

    copy_key: str
    """Stable i18n key for meshek-side translation. Format: "signal.<snake_case_name>"."""
```

**`ProductRecommendation` full rewrite** (replaces current lines 17–22):
```python
class ProductRecommendation(BaseModel):
    """A single per-product recommendation line (WIRE-01 through WIRE-04)."""

    product_id: str
    unit: str
    predicted_demand: float
    demand_lower: float
    demand_upper: float
    reasoning_tier: ReasoningTier
    confidence_score: float = Field(ge=0.0, le=1.0)
    signals: list[Signal] = Field(min_length=1)

    @model_validator(mode="after")
    def band_contains_estimate(self) -> "ProductRecommendation":
        """Ensure demand_lower <= predicted_demand <= demand_upper (WIRE-01)."""
        if not (self.demand_lower <= self.predicted_demand <= self.demand_upper):
            raise ValueError(
                "demand_lower <= predicted_demand <= demand_upper required"
            )
        return self
```

**`RecommendationResponse` full rewrite** (replaces current lines 25–32):
```python
class RecommendationResponse(BaseModel):
    """Full response envelope for one merchant recommendation (WIRE-06)."""

    merchant_id: str
    recommendations: list[ProductRecommendation]
    generated_at: datetime
    # NOTE: reasoning_tier and confidence_score removed from response level (WIRE-02/WIRE-03).
```

**model_validator pattern reference** (from service/schemas.py lines 96–99 — identical `mode="after"` usage in the same project):
```python
@model_validator(mode="after")
def exactly_one_of_items_or_text(self) -> "SalesRequest":
    if (self.items is None) == (self.text is None):
        raise ValueError("Exactly one of 'items' or 'text' must be provided")
    return self
```

**Field constraint pattern reference** (from service/schemas.py line 31 — same `ge`/`le` syntax):
```python
confidence_score: float = Field(ge=0.0, le=1.0)
```

---

### `src/meshek_ml/recommendation/tiers.py` (service, request-response)

**Analog:** Self — surgical edits to three tier constructors. Full file already read (160 lines).

**Import block change** (lines 23–29 — two edits):
```python
# REMOVE line 23:
from meshek_ml.optimization.newsvendor import optimal_order_normal

# UPDATE lines 26–29 to add Signal:
from meshek_ml.recommendation.schema import (
    ProductRecommendation,
    RecommendationResponse,
    Signal,
)
```

**Tier 1 constructor rewrite** (replaces lines 38–44 inside `tier_1_category_defaults`):
```python
recs = [
    ProductRecommendation(
        product_id=p.product_id,
        unit=p.unit,
        predicted_demand=p.default_quantity,
        demand_lower=p.default_quantity,   # placeholder; Phase 14 fills with pooled-prior variance
        demand_upper=p.default_quantity,   # placeholder
        reasoning_tier="category_default",
        confidence_score=0.2,
        signals=[Signal(
            name="category_default",
            contribution=1.0,
            copy_key="signal.tier_1_default",
        )],
    )
    for p in cfg.products
]
```

**`RecommendationResponse` constructor for Tier 1** (replaces lines 45–50 — drop `reasoning_tier` and `confidence_score` from response level):
```python
return RecommendationResponse(
    merchant_id=merchant_id,
    recommendations=recs,
    generated_at=datetime.now(timezone.utc),
)
```

**Tier 2 inner-loop rewrite** (replaces lines 74–78 inside `tier_2_pooled_priors`):
```python
q = shrink * own_mean + (1 - shrink) * pooled_mean  # local var stays as q
recs.append(
    ProductRecommendation(
        product_id=product,
        unit="kg",
        predicted_demand=round(q, 4),
        demand_lower=round(q, 4),   # placeholder
        demand_upper=round(q, 4),   # placeholder
        reasoning_tier="pooled_prior",
        confidence_score=round(confidence, 6),
        signals=[Signal(
            name="pooled_prior",
            contribution=1.0,
            copy_key="signal.tier_2_default",
        )],
    )
)
```
Note: `confidence` is computed AFTER the loop (line 80), so the loop body cannot reference it until the response construction step. Move confidence computation before the loop or compute it outside and pass in — the current code computes it after, so Tier 2 constructor moves the response construction below the confidence line (lines 81–87), which already happens today.

**Tier 3 inner-loop rewrite** (replaces lines 133–146 — removes `optimal_order_normal` call):
```python
for product, mean_demand in zip(last_rows["product"], mu):
    mu_f = float(mean_demand)
    recs.append(
        ProductRecommendation(
            product_id=str(product),
            unit="kg",
            predicted_demand=round(mu_f, 4),
            demand_lower=round(max(0.0, mu_f - float(residual_std)), 4),
            demand_upper=round(mu_f + float(residual_std), 4),
            reasoning_tier="ml_forecast",
            confidence_score=round(confidence, 6),
            signals=[Signal(
                name="ml_forecast",
                contribution=1.0,
                copy_key="signal.tier_3_default",
            )],
        )
    )
```
Note: `confidence` is computed at lines 150–152 (AFTER `mu = model.predict(x)` but BEFORE this loop in the new code). The current code computes confidence after the loop; it must be moved to BEFORE the loop so `confidence` is in scope when `ProductRecommendation` is constructed per product.

**`RecommendationResponse` constructor for Tier 3** (replaces lines 153–158 — drop response-level fields):
```python
return RecommendationResponse(
    merchant_id=merchant_id,
    recommendations=recs,
    generated_at=datetime.now(timezone.utc),
)
```

---

### `src/meshek_ml/recommendation/__init__.py` (config — no changes)

**Current content** (lines 1–14 — do NOT modify):
```python
"""Recommendation engine package (Phase 6)."""
from __future__ import annotations

from meshek_ml.recommendation.engine import RecommendationEngine
from meshek_ml.recommendation.schema import (
    ProductRecommendation,
    RecommendationResponse,
)

__all__ = [
    "ProductRecommendation",
    "RecommendationEngine",
    "RecommendationResponse",
]
```
`Signal` is NOT added here (confirmed: no external consumer imports `Signal` directly; it stays import-local to `tiers.py` and schema tests in Phase 12).

---

### `src/meshek_ml/service/schemas.py` (model — single-line bump)

**Change:** Line 24 only:
```python
# Before:
SERVICE_VERSION = "1.1.0"

# After:
SERVICE_VERSION = "1.2.0"
```

---

### `tests/recommendation/test_schema.py` (test, request-response)

**Analog:** Self — full rewrite of `_valid_response_kwargs` helper and all four test functions.

**New imports block** (replaces current lines 1–12 — add `Signal`):
```python
"""Tests for meshek_ml.recommendation.schema (Phase 12 wire-contract)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from meshek_ml.recommendation.schema import (
    ProductRecommendation,
    RecommendationResponse,
    Signal,
)
```

**New `_valid_product_rec_kwargs` helper** (replaces current `_valid_response_kwargs`):
```python
def _valid_product_rec_kwargs(**overrides):
    """Return kwargs that produce a valid ProductRecommendation."""
    base = dict(
        product_id="tomato",
        unit="kg",
        predicted_demand=8.0,
        demand_lower=8.0,
        demand_upper=8.0,
        reasoning_tier="category_default",
        confidence_score=0.2,
        signals=[Signal(name="category_default", contribution=1.0, copy_key="signal.tier_1_default")],
    )
    base.update(overrides)
    return base


def _valid_response_kwargs(**overrides):
    """Return kwargs that produce a valid RecommendationResponse."""
    base = dict(
        merchant_id="shop_a",
        recommendations=[
            ProductRecommendation(**_valid_product_rec_kwargs()),
        ],
        generated_at=datetime.now(timezone.utc),
    )
    base.update(overrides)
    return base
```

**Rewrite of `test_required_fields`** — now tests a required per-line field (e.g., `reasoning_tier` on `ProductRecommendation`):
```python
def test_required_fields():
    """reasoning_tier is required on ProductRecommendation."""
    kwargs = _valid_product_rec_kwargs()
    kwargs.pop("reasoning_tier")
    with pytest.raises(ValidationError):
        ProductRecommendation(**kwargs)
```

**Rewrite of `test_reasoning_tier_literal`** — test on `ProductRecommendation`, not response:
```python
def test_reasoning_tier_literal():
    """reasoning_tier must be one of the three literal values."""
    with pytest.raises(ValidationError):
        ProductRecommendation(**_valid_product_rec_kwargs(reasoning_tier="bogus"))

    for tier in ("category_default", "pooled_prior", "ml_forecast"):
        pr = ProductRecommendation(**_valid_product_rec_kwargs(reasoning_tier=tier))
        assert pr.reasoning_tier == tier
```

**Rewrite of `test_confidence_bounds`** — test on `ProductRecommendation`:
```python
def test_confidence_bounds():
    """confidence_score must be within [0.0, 1.0]."""
    for bad in (-0.1, 1.1):
        with pytest.raises(ValidationError):
            ProductRecommendation(**_valid_product_rec_kwargs(confidence_score=bad))

    for good in (0.0, 0.2, 0.95, 1.0):
        pr = ProductRecommendation(**_valid_product_rec_kwargs(confidence_score=good))
        assert pr.confidence_score == good
```

**Rewrite of `test_product_recommendation_fields`** — tests new field set, band validator, signals:
```python
def test_product_recommendation_fields():
    """ProductRecommendation requires new per-line fields; band invariant enforced."""
    pr = ProductRecommendation(**_valid_product_rec_kwargs())
    assert pr.product_id == "tomato"
    assert pr.predicted_demand == 8.0
    assert pr.demand_lower == 8.0
    assert pr.demand_upper == 8.0
    assert pr.reasoning_tier == "category_default"
    assert pr.confidence_score == 0.2
    assert len(pr.signals) == 1
    assert pr.signals[0].copy_key == "signal.tier_1_default"

    # Band invariant: lower > predicted must raise
    with pytest.raises(ValidationError):
        ProductRecommendation(**_valid_product_rec_kwargs(demand_lower=9.0, demand_upper=8.0))

    # Signals list must have at least one entry
    with pytest.raises(ValidationError):
        ProductRecommendation(**_valid_product_rec_kwargs(signals=[]))

    # Legacy quantity field must not exist
    pr_dict = pr.model_dump()
    assert "quantity" not in pr_dict

    # Response-level reasoning_tier/confidence_score must be absent
    resp = RecommendationResponse(**_valid_response_kwargs())
    resp_dict = resp.model_dump()
    assert "reasoning_tier" not in resp_dict
    assert "confidence_score" not in resp_dict
```

---

### `tests/recommendation/test_tier_1.py` (test, request-response)

**Analog:** Self — inline assertion migration. Three assertions change; one line is added for signals.

**Line 9 — tier assertion:**
```python
# Before:
assert resp.reasoning_tier == "category_default"
# After:
assert resp.recommendations[0].reasoning_tier == "category_default"
```

**Line 14 — confidence assertion:**
```python
# Before:
assert resp.confidence_score == 0.2
# After:
assert resp.recommendations[0].confidence_score == 0.2
```

**Lines 21–22 — quantity → predicted_demand in `test_quantities_match_yaml`:**
```python
# Before:
assert rec.quantity == p.default_quantity
# After:
assert rec.predicted_demand == p.default_quantity
```

**Add signals assertion in `test_quantities_match_yaml`** (after predicted_demand assertion):
```python
assert len(rec.signals) == 1
assert rec.signals[0].copy_key == "signal.tier_1_default"
```

---

### `tests/recommendation/test_tier_2.py` (test, request-response)

**Analog:** Self — inline assertion migration.

**Line 39 — tier assertion in `test_reasoning_tier`:**
```python
# Before:
assert resp.reasoning_tier == "pooled_prior"
# After:
assert resp.recommendations[0].reasoning_tier == "pooled_prior"
```

**Lines 47–48 — confidence in `test_confidence_bounds`:**
```python
# Before:
assert r1.confidence_score == pytest.approx(0.3, abs=1e-6)
assert r13.confidence_score == pytest.approx(0.6, abs=1e-6)
# After:
assert r1.recommendations[0].confidence_score == pytest.approx(0.3, abs=1e-6)
assert r13.recommendations[0].confidence_score == pytest.approx(0.6, abs=1e-6)
```

**Line 55 — confidence in `test_confidence_monotonic`:**
```python
# Before:
scores = [
    tier_2_pooled_priors("M", df, pooled, n_days=n).confidence_score
    for n in range(1, 14)
]
# After:
scores = [
    tier_2_pooled_priors("M", df, pooled, n_days=n).recommendations[0].confidence_score
    for n in range(1, 14)
]
```

**Line 69 — quantity → predicted_demand in `test_shrinkage_weights`:**
```python
# Before:
assert rec.quantity == pytest.approx(round(40 / 3, 2), abs=1e-6)
# After:
assert rec.predicted_demand == pytest.approx(round(40 / 3, 2), abs=1e-6)
```

**Line 89 — quantity → predicted_demand in `test_uses_pooled_store`:**
```python
# Before:
assert resp.recommendations[0].quantity == pytest.approx(20.0, abs=1e-2)
# After:
assert resp.recommendations[0].predicted_demand == pytest.approx(20.0, abs=1e-2)
```

---

### `tests/recommendation/test_tier_3.py` (test, request-response)

**Analog:** Self — inline assertion migration + one test rename.

**Line 24 — tier assertion in `test_reasoning_tier_is_ml_forecast`:**
```python
# Before:
assert resp.reasoning_tier == "ml_forecast"
# After:
assert resp.recommendations[0].reasoning_tier == "ml_forecast"
```

**Line 40 — confidence in `test_confidence_bounds`:**
```python
# Before:
assert 0.6 <= resp.confidence_score <= 0.95
# After:
assert 0.6 <= resp.recommendations[0].confidence_score <= 0.95
```

**Lines 44–56 — rename + field change in `test_quantities_non_negative`:**
```python
# Rename function:
# Before: def test_quantities_non_negative(...)
# After:  def test_predicted_demand_non_negative(...)

# Line 56 — field access:
# Before: assert rec.quantity >= 0
# After:  assert rec.predicted_demand >= 0
```

**Line 99 (inside `test_inference_never_reads_disk`) — tier assertion:**
```python
# Before:
assert resp.reasoning_tier == "ml_forecast"
# After:
assert resp.recommendations[0].reasoning_tier == "ml_forecast"
```

---

### `tests/recommendation/test_engine.py` (test, request-response)

**Analog:** Self — per-line assertion migration across 7 locations.

**Lines 28–29 — `test_tier_1_routing_zero_days`:**
```python
# Before:
assert resp.reasoning_tier == "category_default"
assert resp.confidence_score == 0.2
# After:
assert resp.recommendations[0].reasoning_tier == "category_default"
assert resp.recommendations[0].confidence_score == 0.2
```

**Lines 42–43 — `test_tier_2_routing_at_1_day`:**
```python
# Before:
assert resp.reasoning_tier == "pooled_prior"
assert 0.3 <= resp.confidence_score <= 0.6
# After:
assert resp.recommendations[0].reasoning_tier == "pooled_prior"
assert 0.3 <= resp.recommendations[0].confidence_score <= 0.6
```

**Lines 54–55 — `test_tier_2_routing_at_13_days`:**
```python
# Before:
assert resp.reasoning_tier == "pooled_prior"
assert 0.3 <= resp.confidence_score <= 0.6
# After:
assert resp.recommendations[0].reasoning_tier == "pooled_prior"
assert 0.3 <= resp.recommendations[0].confidence_score <= 0.6
```

**Lines 68–69 — `test_tier_3_routing_at_14_days`:**
```python
# Before:
assert resp.reasoning_tier == "ml_forecast"
assert 0.6 <= resp.confidence_score <= 0.95
# After:
assert resp.recommendations[0].reasoning_tier == "ml_forecast"
assert 0.6 <= resp.recommendations[0].confidence_score <= 0.95
```

**Lines 82–83 — `test_tier_3_routing_at_30_days`:**
```python
# Before:
assert resp.reasoning_tier == "ml_forecast"
assert 0.6 <= resp.confidence_score <= 0.95
# After:
assert resp.recommendations[0].reasoning_tier == "ml_forecast"
assert 0.6 <= resp.recommendations[0].confidence_score <= 0.95
```

**Lines 99–103 — `test_confidence_bounds_per_tier`:**
```python
# Before:
assert engine.recommend("t1").confidence_score == 0.2
r2 = engine.recommend("t2")
assert 0.3 <= r2.confidence_score <= 0.6
r3 = engine.recommend("t3")
assert 0.6 <= r3.confidence_score <= 0.95
# After:
assert engine.recommend("t1").recommendations[0].confidence_score == 0.2
r2 = engine.recommend("t2")
assert 0.3 <= r2.recommendations[0].confidence_score <= 0.6
r3 = engine.recommend("t3")
assert 0.6 <= r3.recommendations[0].confidence_score <= 0.95
```

**Lines 122–123 — `test_response_contract_rec04`:**
```python
# Before:
assert resp.reasoning_tier is not None
assert resp.confidence_score is not None
# After:
assert resp.recommendations[0].reasoning_tier is not None
assert resp.recommendations[0].confidence_score is not None
```

---

### `tests/service/test_recommend.py` (test, request-response)

**Analog:** Self — per-line migration for existing assertions + two new test functions appended.

**Line 59 — `test_recommend_tier1`:**
```python
# Before:
assert body["reasoning_tier"] == "category_default"
# After:
assert body["recommendations"][0]["reasoning_tier"] == "category_default"
```

**Line 61 — `test_recommend_tier1`:**
```python
# Before:
assert "confidence_score" in body
# After:
assert "confidence_score" in body["recommendations"][0]
```

**Lines 74–75 — `test_recommend_tier2`:**
```python
# Before:
assert body["reasoning_tier"] == "pooled_prior"
assert 0.3 <= body["confidence_score"] <= 0.6
# After:
assert body["recommendations"][0]["reasoning_tier"] == "pooled_prior"
assert 0.3 <= body["recommendations"][0]["confidence_score"] <= 0.6
```

**Lines 84–85 — `test_recommend_tier3`:**
```python
# Before:
assert body["reasoning_tier"] == "ml_forecast"
assert 0.6 <= body["confidence_score"] <= 0.95
# After:
assert body["recommendations"][0]["reasoning_tier"] == "ml_forecast"
assert 0.6 <= body["recommendations"][0]["confidence_score"] <= 0.95
```

**Line 131 — `test_tier1_in_degraded_mode`:**
```python
# Before:
assert body["reasoning_tier"] == "category_default"
# After:
assert body["recommendations"][0]["reasoning_tier"] == "category_default"
```

**New `test_openapi_wire_contract` function** (append after existing tests):
```python
def test_openapi_wire_contract(app_client):
    """GET /openapi.json reflects new wire shape; legacy quantity absent (WIRE-06)."""
    resp = app_client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    pr_props = schema["components"]["schemas"]["ProductRecommendation"]["properties"]
    for field in ("predicted_demand", "demand_lower", "demand_upper",
                  "reasoning_tier", "confidence_score", "signals"):
        assert field in pr_props, f"OpenAPI missing field: {field}"
    assert "quantity" not in pr_props, "quantity must be absent from OpenAPI schema"
    # Response envelope must not have response-level tier/score
    rr_props = schema["components"]["schemas"]["RecommendationResponse"]["properties"]
    assert "reasoning_tier" not in rr_props
    assert "confidence_score" not in rr_props
```

**New `test_tier1_contract_key_set` function** (append after `test_openapi_wire_contract`):
```python
def test_tier1_contract_key_set(app_client, data_dir):
    """Full key-set + type contract test for Tier 1 response (WIRE-01 to WIRE-06)."""
    _seed_merchant(data_dir, "contract_t1", days=0)
    resp = app_client.post("/recommend", json={"merchant_id": "contract_t1"})
    assert resp.status_code == 200
    body = resp.json()

    # Response envelope
    assert set(body.keys()) >= {"merchant_id", "recommendations", "generated_at"}
    assert "reasoning_tier" not in body, "response-level reasoning_tier must be absent"
    assert "confidence_score" not in body, "response-level confidence_score must be absent"
    assert "quantity" not in body

    # Per-line fields
    assert len(body["recommendations"]) >= 1
    line = body["recommendations"][0]
    assert isinstance(line["product_id"], str)
    assert isinstance(line["unit"], str)
    assert isinstance(line["predicted_demand"], (int, float))
    assert isinstance(line["demand_lower"], (int, float))
    assert isinstance(line["demand_upper"], (int, float))
    assert line["reasoning_tier"] == "category_default"
    assert 0.0 <= line["confidence_score"] <= 1.0
    assert "quantity" not in line

    # Signals
    assert isinstance(line["signals"], list)
    assert len(line["signals"]) >= 1
    sig = line["signals"][0]
    assert isinstance(sig["name"], str)
    assert isinstance(sig["contribution"], (int, float))
    assert isinstance(sig["copy_key"], str)
    assert sig["copy_key"].startswith("signal.")
```

---

## Shared Patterns

### Pydantic v2 `model_validator(mode="after")`
**Source:** `src/meshek_ml/service/schemas.py` lines 96–99 (existing, verified)
**Apply to:** `ProductRecommendation.band_contains_estimate` in `schema.py`
```python
@model_validator(mode="after")
def exactly_one_of_items_or_text(self) -> "SalesRequest":
    if (self.items is None) == (self.text is None):
        raise ValueError("Exactly one of 'items' or 'text' must be provided")
    return self
```
The new validator follows the identical call signature and return type.

### `Field(ge=, le=)` bounds
**Source:** `src/meshek_ml/service/schemas.py` line 31 (existing `confidence_score` there in v1.1) and current `schema.py` line 31
**Apply to:** `ProductRecommendation.confidence_score` in `schema.py`
```python
confidence_score: float = Field(ge=0.0, le=1.0)
```

### `from __future__ import annotations` + Pydantic v2 import header
**Source:** `src/meshek_ml/recommendation/schema.py` lines 7–12 (current)
**Apply to:** All modified Python source files — convention is uniform across the project.
```python
from __future__ import annotations
from pydantic import BaseModel, Field, model_validator
```

### Test file `from __future__ import annotations` + pytest import header
**Source:** `tests/recommendation/test_schema.py` lines 1–7 (current)
**Apply to:** All test files — keep the header unchanged.
```python
from __future__ import annotations
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
```

### `RecommendationResponse` constructor (no response-level fields)
**Source:** `src/meshek_ml/recommendation/tiers.py` lines 45–50 (current, before rewrite)
**Apply to:** All three tier functions after rewrite — the response constructor loses `reasoning_tier` and `confidence_score`:
```python
return RecommendationResponse(
    merchant_id=merchant_id,
    recommendations=recs,
    generated_at=datetime.now(timezone.utc),
)
```

### HTTP test helper `_seed_merchant`
**Source:** `tests/service/test_recommend.py` lines 23–45 (unchanged — reuse as-is for new contract tests)
```python
def _seed_merchant(data_dir, merchant_id: str, days: int) -> None:
    with MerchantStore(merchant_id) as store:
        store.create_profile(MerchantProfile(merchant_id=merchant_id))
        if days <= 0:
            return
        ...
        store.write_sales(pd.DataFrame(rows))
```

---

## No Analog Found

All files in Phase 12 have close self-analogs or intra-project analogs. No files require falling back to RESEARCH.md patterns exclusively — the RESEARCH.md patterns were verified against the project's own venv and are reproduced above as code excerpts.

---

## Metadata

**Analog search scope:** `src/meshek_ml/recommendation/`, `src/meshek_ml/service/`, `tests/recommendation/`, `tests/service/`
**Files scanned:** 10 source/test files read in full
**Pattern extraction date:** 2026-05-04
