# Phase 12: wire-contract — Research

**Researched:** 2026-05-04
**Domain:** Pydantic v2 schema evolution, FastAPI OpenAPI generation, cross-repo TypeScript type coordination
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Ship the new wire shape with **minimal defaults** for Tier 1/2 — `demand_lower = demand_upper = predicted_demand` and a single tier-name signal per line. Phase 14 replaces these with pooled-prior-variance bands and richer signals.
- Tier 3: expose `predicted_demand` as the LightGBM forecast `mu`; derive `demand_lower` / `demand_upper` from `±1σ residual_std`. Newsvendor's `optimal_order_normal` stays as an internal utility but is no longer called from the response path.
- Retain per-line `unit` (kg / unit) — meshek expects it.
- Drop response-level `reasoning_tier` and `confidence_score` entirely — per-line is the new truth.
- `signals[].contribution` units: raw demand units (same scale as `predicted_demand`, e.g., kg).
- `signals[].name` type: open `str` in Phase 12; tightened to `Literal[...]` in Phase 14.
- `copy_key` format: `signal.<snake_case_name>` — e.g., `signal.tier_1_default`.
- Minimum signals per line: exactly one tier-name signal.
- New types live in `recommendation/schema.py`.
- Remove `ProductRecommendation.quantity`. Replace with `predicted_demand`, `demand_lower`, `demand_upper`, plus per-line `reasoning_tier`, `confidence_score`, `signals[]`.
- Bump `SERVICE_VERSION` in `service/schemas.py` from `"1.1.0"` to `"1.2.0"`.
- Add a test that hits `GET /openapi.json` and asserts new line-level fields are present and legacy `quantity` is absent.
- Open `@meshek/ml-client` PR as draft first. Merge order: meshek PR first, then meshek-ml.
- Update existing tests **inline** — no parallel test files.
- Migrate `body["reasoning_tier"]` / `body["confidence_score"]` assertions to `body["recommendations"][0]["reasoning_tier"]` etc.
- Add one Tier-1 contract test pinning the full key set + types.

### Claude's Discretion

- Internal naming for the new fields' Pydantic descriptions, validators.
- Whether the contract test is in `tests/service/test_recommend.py` or a sibling `test_recommend_contract.py` (Claude picks based on file size).
- Exact assertion style for the OpenAPI test (key-presence vs full schema diff).

### Deferred Ideas (OUT OF SCOPE)

- Honest pooled-prior-variance demand bands for Tier 1/2 — Phase 14.
- Richer `signals[]` — Phase 14 and Phase 13.
- `signals.name` enum lockdown to `Literal[...]` — Phase 14.
- Tier 2 shrinkage anchor re-tuning — Phase 15.
- Calendar-derived feature columns — Phase 13.
- Tier 3 retraining, real-data benchmark eval, stock awareness, dynamic pricing — out of scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WIRE-01 | `/recommend` response replaces `recommendations[].quantity` with `predicted_demand`, `demand_lower`, `demand_upper` per line | `ProductRecommendation` model rewrite; Pydantic v2 `Field` patterns confirmed |
| WIRE-02 | Each line carries `reasoning_tier` as stable enum per-line, not response-level | `ReasoningTier = Literal[...]` already in schema.py; move from `RecommendationResponse` to `ProductRecommendation` |
| WIRE-03 | Each line carries `confidence_score` in `[0, 1]` per-line, not response-level | `Field(ge=0.0, le=1.0)` pattern already established in service/schemas.py |
| WIRE-04 | Each line carries `signals[]` — name/contribution/copy_key | New `Signal` model + `list[Signal] = Field(min_length=1)` confirmed in venv |
| WIRE-05 | Newsvendor order-qty layer removed from public response | `optimal_order_normal` call and `quantity=` construction removed from `tier_3_ml_forecast` in tiers.py |
| WIRE-06 | `RecommendationResponse` Pydantic model and OpenAPI documentation reflect new shape; legacy `quantity` field gone | `response_model=RecommendationResponse` auto-generates OpenAPI from model; GET /openapi.json confirmed via test |
| WIRE-07 | `@meshek/ml-client` TypeScript types updated via coordinated PR before MM-P1 merges | `packages/types/src/recommendation.ts` + `packages/ml-client/src/guards.ts` identified as the two files needing updates |
</phase_requirements>

---

## Summary

Phase 12 is a pure schema-evolution task with no new algorithms. All three tier functions return the same `RecommendationResponse` class; the class's shape changes around them. The main mechanical work is: (1) rewrite `ProductRecommendation` in `recommendation/schema.py` to drop `quantity` and add the five new per-line fields plus the `Signal` sub-model; (2) rewrite the three tier constructors in `tiers.py` to produce the new shape; (3) surgically remove the newsvendor call from `tier_3_ml_forecast`; (4) migrate all tests that currently read `body["reasoning_tier"]` or `resp.reasoning_tier` to their per-line equivalents.

The Pydantic v2 patterns required — `model_validator(mode="after")` for band ordering, `Field(min_length=1)` for signals, `ge/le` bounds on `confidence_score` — have all been confirmed to work correctly in the project's venv (pydantic 2.13.0). FastAPI's `response_model=RecommendationResponse` automatically emits the full nested schema in `/openapi.json`, including the `Signal` sub-model; testing via `TestClient.get("/openapi.json")` is the correct approach and has been verified.

The cross-repo surface is larger than it looks: `packages/types/src/recommendation.ts` defines the TypeScript interfaces and `packages/ml-client/src/guards.ts` contains a hand-rolled runtime shape-guard that checks `l.quantity`, `r.reasoning_tier`, and `r.confidence_score` at the response level. Both files plus their companion tests must be updated in the meshek-side PR.

**Primary recommendation:** Execute the schema change in a single wave — schema.py first (new types), then tiers.py (constructors), then tests (inline migration), then the OpenAPI assertion test. The meshek-side PR can be opened as a draft from the types alone before the Python side is merged.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Wire contract definition | API / Backend (`recommendation/schema.py`) | — | Pydantic models are the single source of truth; FastAPI serializes from them |
| OpenAPI generation | API / Backend (FastAPI) | — | `response_model=RecommendationResponse` drives the schema automatically |
| TypeScript client types | Frontend consumer (`@meshek/types`, `@meshek/ml-client`) | — | meshek owns the TS surface; meshek-ml owns the Python surface |
| Tier routing logic | API / Backend (`recommendation/engine.py`) | — | Untouched this phase |
| Newsvendor utility | API / Backend (`optimization/newsvendor.py`) | — | Remains as internal utility; removed from response path only |

---

## Standard Stack

### Core (no new dependencies required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.13.0 [VERIFIED: venv] | Schema definition, validation, OpenAPI emission | Already installed; v2 `model_validator` and `Field(min_length=1)` confirmed working |
| fastapi | 0.135.2 [VERIFIED: venv] | HTTP layer + automatic OpenAPI | Already installed; `response_model=` auto-generates nested schema |
| starlette TestClient | (bundled with fastapi) | HTTP test assertions including `GET /openapi.json` | Already used by all service tests |

No new Python dependencies are introduced in this phase. [VERIFIED: codebase inspection]

---

## Architecture Patterns

### Confirmed Pattern: Pydantic v2 `model_validator(mode="after")` for cross-field constraint

`mode="after"` runs after all field validators have populated the model instance, so `self.demand_lower`, `self.predicted_demand`, and `self.demand_upper` are all typed floats by the time the validator runs. The placeholder case `lower == upper == predicted` satisfies `lower <= predicted <= upper` trivially — no special-casing needed.

[VERIFIED: executed in project venv]

```python
# Source: verified in .venv/bin/python
@model_validator(mode="after")
def band_contains_estimate(self) -> "ProductRecommendation":
    if not (self.demand_lower <= self.predicted_demand <= self.demand_upper):
        raise ValueError(
            "demand_lower <= predicted_demand <= demand_upper required"
        )
    return self
```

### Confirmed Pattern: `Field(min_length=1)` on `list[Signal]`

Pydantic v2 applies `min_length` to collection fields. Empty-list case raises `ValidationError` as expected. [VERIFIED: executed in project venv]

```python
signals: list[Signal] = Field(min_length=1)
```

### Confirmed Pattern: FastAPI OpenAPI via `response_model=`

`@router.post("/recommend", response_model=RecommendationResponse)` already exists in `service/routes/recommend.py`. When `RecommendationResponse` is updated, the OpenAPI schema updates automatically. No route-layer changes needed. [VERIFIED: executed in project venv]

### Confirmed Pattern: Testing OpenAPI via `TestClient.get("/openapi.json")`

```python
# Pattern verified in project venv
def test_openapi_new_wire_shape(app_client):
    resp = app_client.get("/openapi.json")
    assert resp.status_code == 200
    props = resp.json()["components"]["schemas"]["ProductRecommendation"]["properties"]
    for field in ["predicted_demand", "demand_lower", "demand_upper",
                  "reasoning_tier", "confidence_score", "signals"]:
        assert field in props, f"missing field: {field}"
    assert "quantity" not in props
```

`app_client` fixture is already session-scoped model-loaded — use it directly. [VERIFIED: conftest.py inspection]

### Recommended Project Structure (no changes)

All new types go in the existing module `src/meshek_ml/recommendation/schema.py`. No new files needed for Phase 12. [CITED: CONTEXT.md Schema Location decision]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Band containment check | Custom pre-validation wrapper | `model_validator(mode="after")` | Pydantic v2 native; confirmed working |
| List minimum length | Custom `@validator` | `Field(min_length=1)` | Pydantic v2 native; confirmed working |
| OpenAPI schema assertion | Manual schema construction | Walk `GET /openapi.json` JSON | FastAPI emits it automatically; no reconstruction needed |
| TypeScript type sync | Code generation | Hand-edit `recommendation.ts` and `guards.ts` | Both files are small and hand-maintained by convention (see guards.ts comment) |

---

## Newsvendor Decoupling — Exact Lines Changing in `tiers.py`

**Current `tier_3_ml_forecast` (lines 130–160 in tiers.py):**

Lines that are REMOVED or REPLACED:

| Line(s) | Current content | Action |
|---------|----------------|--------|
| 23 (top import) | `from meshek_ml.optimization.newsvendor import optimal_order_normal` | REMOVE (no longer called in response path) |
| 134–139 | `q = optimal_order_normal(mean_demand=..., std_demand=..., ...)` | REMOVE |
| 141–145 | `ProductRecommendation(product_id=..., quantity=round(float(q), 2), unit="kg")` | REPLACE with new constructor |

Lines that STAY unchanged:

- All feature-engineering lines (add_lag_features, add_rolling_features, add_calendar_features)
- `last_rows` construction logic
- NaN imputation (`x.fillna`)
- `mu = model.predict(x)` — `mu` is now exposed directly as `predicted_demand`
- Confidence computation (`y_mean`, `raw`, `max(0.6, min(0.95, raw))`)

**New inner loop body:**

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

Note: `confidence` must be computed before the loop (it uses the whole sales frame), so loop ordering is unchanged.

**`tier_1_category_defaults` — new constructor:**

```python
ProductRecommendation(
    product_id=p.product_id,
    unit=p.unit,
    predicted_demand=p.default_quantity,
    demand_lower=p.default_quantity,   # placeholder
    demand_upper=p.default_quantity,   # placeholder
    reasoning_tier="category_default",
    confidence_score=0.2,
    signals=[Signal(
        name="category_default",
        contribution=1.0,
        copy_key="signal.tier_1_default",
    )],
)
```

**`tier_2_pooled_priors` — rename `q` → `predicted_demand` and new constructor:**

```python
q = shrink * own_mean + (1 - shrink) * pooled_mean  # stays as q locally
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
```

---

## Re-export Surface Analysis

Current `recommendation/__init__.py` re-exports:
- `RecommendationEngine` (from engine.py)
- `ProductRecommendation` (from schema.py)
- `RecommendationResponse` (from schema.py)

The new `Signal` class: used only inside `tiers.py` constructors and tested via `ProductRecommendation.signals`. No external consumer currently imports `Signal` directly (confirmed by grep of src/). Decision: **do NOT add `Signal` to `__init__.py` re-exports in Phase 12.** Phase 14 may expose it when the Literal enum is locked, but for now it stays import-local to `tiers.py` and schema tests.

[VERIFIED: grep of all src/ imports]

---

## Cross-Repo Coordination — TypeScript Files Requiring Update

Two files in the meshek repo require changes in the coordinated PR:

### 1. `packages/types/src/recommendation.ts`

Current shape (OLD):
```typescript
export interface RecommendationLine {
  product_id: string;
  quantity: number;
  unit: string;
}

export interface RecommendationResponse {
  merchant_id: string;
  recommendations: RecommendationLine[];
  reasoning_tier: ReasoningTier;
  confidence_score: number;
  generated_at: string;
}
```

New shape (required):
```typescript
export interface Signal {
  name: string;          // open string in v1.2; tightened to union in v1.3
  contribution: number;  // signed, in demand units (kg)
  copy_key: string;      // format: "signal.<snake_case_name>"
}

export interface RecommendationLine {
  product_id: string;
  unit: string;
  predicted_demand: number;
  demand_lower: number;
  demand_upper: number;
  reasoning_tier: ReasoningTier;
  confidence_score: number;
  signals: Signal[];
}

export interface RecommendationResponse {
  merchant_id: string;
  recommendations: RecommendationLine[];
  generated_at: string;
  // NOTE: reasoning_tier and confidence_score removed from response level
}
```

### 2. `packages/ml-client/src/guards.ts` — `assertRecommendationResponse`

The guard currently checks:
- `r.reasoning_tier` at response level — REMOVE
- `r.confidence_score` at response level — REMOVE
- `l.quantity` per line — REPLACE with per-line field checks

New per-line checks to add inside the recommendations loop:
- `typeof l.predicted_demand !== "number"` → shape error
- `typeof l.demand_lower !== "number"` → shape error
- `typeof l.demand_upper !== "number"` → shape error
- `typeof l.reasoning_tier !== "string" || !REASONING_TIERS.has(l.reasoning_tier)` → shape error
- `typeof l.confidence_score !== "number" || l.confidence_score < 0 || l.confidence_score > 1` → shape error
- `!Array.isArray(l.signals) || l.signals.length < 1` → shape error

### 3. `packages/ml-client/src/guards.test.ts`

The `valid` fixture uses `quantity` in `recommendations[0]` and asserts response-level `reasoning_tier`/`confidence_score`. Update to use new shape. Missing-field and wrong-type tests for each new line-level field must be added.

**Merge sequence:** meshek PR first (types + guards + guard tests), then meshek-ml PR. Both PRs should reference each other in their descriptions. [CITED: CONTEXT.md Cross-Repo Coordination]

---

## Common Pitfalls

### Pitfall 1: Forgetting `Signal` import in tiers.py

**What goes wrong:** After adding `Signal` to schema.py, `tiers.py` must import it alongside `ProductRecommendation` and `RecommendationResponse`. The import block is at line 26-29 of tiers.py.

**How to avoid:** The import line becomes:
```python
from meshek_ml.recommendation.schema import (
    ProductRecommendation,
    RecommendationResponse,
    Signal,
)
```

### Pitfall 2: Leaving the `optimal_order_normal` import at the top of tiers.py

**What goes wrong:** After removing the call, the orphaned import triggers ruff `F401` (unused import). The `ruff` pre-commit hook will fail.

**How to avoid:** Remove the entire `from meshek_ml.optimization.newsvendor import optimal_order_normal` line at line 23 of tiers.py. The function still exists in `newsvendor.py` — just not called from the response path.

### Pitfall 3: Test assertions on response-level `reasoning_tier` / `confidence_score`

These are the exact locations in the test files that must migrate to per-line:

| File | Line(s) | Current assertion | New assertion |
|------|---------|-------------------|---------------|
| `tests/service/test_recommend.py` | 59 | `body["reasoning_tier"] == "category_default"` | `body["recommendations"][0]["reasoning_tier"] == "category_default"` |
| `tests/service/test_recommend.py` | 61 | `"confidence_score" in body` | `"confidence_score" in body["recommendations"][0]` |
| `tests/service/test_recommend.py` | 74 | `body["reasoning_tier"] == "pooled_prior"` | `body["recommendations"][0]["reasoning_tier"] == "pooled_prior"` |
| `tests/service/test_recommend.py` | 75 | `0.3 <= body["confidence_score"] <= 0.6` | `0.3 <= body["recommendations"][0]["confidence_score"] <= 0.6` |
| `tests/service/test_recommend.py` | 84 | `body["reasoning_tier"] == "ml_forecast"` | `body["recommendations"][0]["reasoning_tier"] == "ml_forecast"` |
| `tests/service/test_recommend.py` | 85 | `0.6 <= body["confidence_score"] <= 0.95` | `0.6 <= body["recommendations"][0]["confidence_score"] <= 0.95` |
| `tests/service/test_recommend.py` | 131 | `body["reasoning_tier"] == "category_default"` | `body["recommendations"][0]["reasoning_tier"] == "category_default"` |
| `tests/recommendation/test_engine.py` | 28-29, 42-43, 54-55, 68-69, 82-83, 99-103, 122-123 | `resp.reasoning_tier`, `resp.confidence_score` | `resp.recommendations[0].reasoning_tier`, `resp.recommendations[0].confidence_score` |
| `tests/recommendation/test_tier_1.py` | 9 | `resp.reasoning_tier == "category_default"` | `resp.recommendations[0].reasoning_tier == "category_default"` |
| `tests/recommendation/test_tier_1.py` | 14 | `resp.confidence_score == 0.2` | `resp.recommendations[0].confidence_score == 0.2` |
| `tests/recommendation/test_tier_1.py` | 22 | `rec.quantity == p.default_quantity` | `rec.predicted_demand == p.default_quantity` |
| `tests/recommendation/test_tier_2.py` | 39 | `resp.reasoning_tier == "pooled_prior"` | `resp.recommendations[0].reasoning_tier == "pooled_prior"` |
| `tests/recommendation/test_tier_2.py` | 47-48 | `r1.confidence_score`, `r13.confidence_score` | `r1.recommendations[0].confidence_score`, etc. |
| `tests/recommendation/test_tier_2.py` | 55 | `.confidence_score` on tier_2 resp | `.recommendations[0].confidence_score` |
| `tests/recommendation/test_tier_2.py` | 69 | `rec.quantity == pytest.approx(...)` | `rec.predicted_demand == pytest.approx(...)` |
| `tests/recommendation/test_tier_2.py` | 89 | `resp.recommendations[0].quantity` | `resp.recommendations[0].predicted_demand` |
| `tests/recommendation/test_tier_3.py` | 24 | `resp.reasoning_tier == "ml_forecast"` | `resp.recommendations[0].reasoning_tier == "ml_forecast"` |
| `tests/recommendation/test_tier_3.py` | 40 | `resp.confidence_score` | `resp.recommendations[0].confidence_score` |
| `tests/recommendation/test_tier_3.py` | 56 | `rec.quantity >= 0` | `rec.predicted_demand >= 0` |
| `tests/recommendation/test_tier_3.py` | 99 | `resp.reasoning_tier == "ml_forecast"` | `resp.recommendations[0].reasoning_tier == "ml_forecast"` |
| `tests/recommendation/test_schema.py` | All | `reasoning_tier` on response, `quantity` on ProductRecommendation | Full rewrite of `_valid_response_kwargs` and test functions |

[VERIFIED: grep of all test files]

### Pitfall 4: `_valid_response_kwargs` helper in test_schema.py must be fully rewritten

The current helper constructs `ProductRecommendation(product_id="tomato", quantity=8.0, unit="kg")` and a response with `reasoning_tier`/`confidence_score` at the top level. After the schema change, both of these signatures break. The helper and all four test functions in `test_schema.py` need full rewrites — they cannot be lightly patched.

### Pitfall 5: test_tier_2.py `test_shrinkage_weights` uses `rec.quantity`

`test_shrinkage_weights` asserts `rec.quantity == pytest.approx(round(40 / 3, 2))`. This must become `rec.predicted_demand`. The expected value does not change — only the field name.

### Pitfall 6: `test_quantities_non_negative` in test_tier_3.py

The test name refers to quantities — rename to `test_predicted_demand_non_negative` and update the field access to `rec.predicted_demand`.

### Pitfall 7: `test_required_fields` in test_schema.py pops `reasoning_tier`

The test pops a response-level field that no longer exists. After the schema change, the test must pop `reasoning_tier` from `ProductRecommendation` kwargs (it is now required per-line), or test a different required field on `RecommendationResponse`.

### Pitfall 8: Confidence computed after loop in Tier 3 — loop order matters

In `tier_3_ml_forecast`, `confidence` is derived from `y_mean` (the overall sales mean), which must be computed before the `for product, mean_demand in zip(...)` loop. The current code computes confidence outside the loop. Keep it that way — the new code must not move confidence computation inside the per-product loop. [VERIFIED: tiers.py inspection, lines 149-152]

---

## Code Examples

### New `recommendation/schema.py` skeleton

```python
# Source: verified Pydantic v2 patterns in project venv
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

ReasoningTier = Literal["category_default", "pooled_prior", "ml_forecast"]


class Signal(BaseModel):
    """A single explanation signal for a recommendation line (WIRE-04)."""

    name: str
    """Stable signal name. Open str in v1.2; tightened to Literal in Phase 14.
    Documented stable values: "category_default", "pooled_prior", "ml_forecast"."""

    contribution: float
    """Signed contribution in demand units (kg). Raw demand scale, not normalized."""

    copy_key: str
    """Stable i18n key for meshek-side translation. Format: "signal.<snake_case_name>"."""


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


class RecommendationResponse(BaseModel):
    """Full response envelope for one merchant recommendation (WIRE-06)."""

    merchant_id: str
    recommendations: list[ProductRecommendation]
    generated_at: datetime
    # NOTE: reasoning_tier and confidence_score removed from response level (WIRE-02/WIRE-03).
```

### Tier 1 contract test (Tier-1 simplest path)

```python
# Recommended location: tests/service/test_recommend.py (inline, not a separate file)
# Given test_recommend.py is ~154 lines, adding a contract test section is appropriate.

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

### OpenAPI assertion test

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

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8+ (detected in venv: `pytest>=7.4` pinned; current 8.x) |
| Config file | `pyproject.toml` → `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/recommendation/ tests/service/test_recommend.py -v --tb=short` |
| Full suite command | `pytest tests/ -v --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WIRE-01 | `quantity` replaced by `predicted_demand`/`demand_lower`/`demand_upper` per line | unit | `pytest tests/recommendation/test_schema.py tests/recommendation/test_tier_1.py tests/recommendation/test_tier_2.py tests/recommendation/test_tier_3.py -x` | Existing — update inline |
| WIRE-02 | `reasoning_tier` is per-line, not response-level | unit + integration | `pytest tests/recommendation/test_engine.py tests/service/test_recommend.py -x` | Existing — update inline |
| WIRE-03 | `confidence_score` is per-line, not response-level | unit + integration | `pytest tests/recommendation/test_engine.py tests/service/test_recommend.py -x` | Existing — update inline |
| WIRE-04 | `signals[]` with at least one entry; Signal has name/contribution/copy_key | unit | `pytest tests/recommendation/test_schema.py -x` | Existing — update inline |
| WIRE-05 | Newsvendor not called in response path | unit (monkeypatch) | `pytest tests/recommendation/test_tier_3.py::test_inference_never_reads_disk -x` (extend to also assert newsvendor not called) | Existing — extend inline |
| WIRE-06 | OpenAPI reflects new shape; `quantity` absent | schema | `pytest tests/service/test_recommend.py::test_openapi_wire_contract -x` | NEW — add in test_recommend.py |
| WIRE-07 | `@meshek/ml-client` types updated | cross-repo (manual gate) | Manual: confirm meshek PR merged before meshek-ml merge | External — document in phase summary |

### Sampling Rate

- **Per task commit:** `pytest tests/recommendation/ tests/service/test_recommend.py -v --tb=short`
- **Per wave merge:** `pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `test_openapi_wire_contract` — new test function to add in `tests/service/test_recommend.py`
- [ ] `test_tier1_contract_key_set` — new contract test function to add in `tests/service/test_recommend.py`
- [ ] All `body["reasoning_tier"]` / `resp.reasoning_tier` occurrences (enumerated in Pitfall 3 table) — inline migration across 6 test files

---

## Security Domain

This phase changes no authentication, session, access control, or cryptographic behaviour. It is a pure wire-shape change on an existing authenticated route. No new ASVS categories are introduced.

**ASVS V5 (Input Validation):** The new `ProductRecommendation` model adds `model_validator` for band ordering and `Field(min_length=1)` for signals — both tighten output validation, not relaxing it. No new inputs are accepted.

---

## Environment Availability

Step 2.6: No new external dependencies introduced in this phase (no new CLI tools, services, or runtimes). Python venv already contains all required packages.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pydantic | Schema models | ✓ | 2.13.0 | — |
| fastapi | HTTP + OpenAPI | ✓ | 0.135.2 | — |
| pytest | Test suite | ✓ | 8.x | — |

---

## Assumptions Log

> No claims in this research required `[ASSUMED]` tags. All findings were verified by direct inspection of the project venv, codebase, and test files.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | — | — | — |

**All claims in this research were verified or cited — no user confirmation needed.**

---

## Open Questions

None. All design decisions are locked in CONTEXT.md, and all technical patterns were verified against the running venv and codebase.

---

## Sources

### Primary (HIGH confidence)

- Pydantic v2 `model_validator`, `Field(min_length=1)`, `Field(ge=, le=)` — [VERIFIED: executed in .venv/bin/python, pydantic 2.13.0]
- FastAPI `response_model=` → OpenAPI generation — [VERIFIED: executed in .venv/bin/python, fastapi 0.135.2]
- `TestClient.get("/openapi.json")` pattern — [VERIFIED: executed in .venv/bin/python]
- All test file assertion locations — [VERIFIED: grep of tests/ directory]
- `tiers.py` current newsvendor call location (lines 134-145) — [VERIFIED: file inspection]
- `recommendation/__init__.py` re-export surface — [VERIFIED: file inspection]
- meshek `packages/types/src/recommendation.ts` current shape — [VERIFIED: file inspection]
- meshek `packages/ml-client/src/guards.ts` current guard logic — [VERIFIED: file inspection]

### Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all existing packages verified in venv
- Architecture: HIGH — all patterns executed, all files inspected
- Pitfalls: HIGH — all assertion locations enumerated by grep

**Research date:** 2026-05-04
**Valid until:** 2026-06-04 (stable Python/Pydantic ecosystem)

---

## RESEARCH COMPLETE
