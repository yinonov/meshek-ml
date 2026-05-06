---
phase: phase-12-wire-contract
reviewed: 2026-05-04T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - src/meshek_ml/recommendation/schema.py
  - src/meshek_ml/recommendation/tiers.py
  - src/meshek_ml/service/schemas.py
  - tests/recommendation/test_schema.py
  - tests/recommendation/test_tier_1.py
  - tests/recommendation/test_tier_2.py
  - tests/recommendation/test_tier_3.py
  - tests/recommendation/test_engine.py
  - tests/service/test_recommend.py
  - tests/service/test_health.py
findings:
  critical: 1
  warning: 5
  info: 0
  total: 6
status: issues_found
---

# Phase 12: Code Review Report

**Reviewed:** 2026-05-04T00:00:00Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Reviewed the Phase 12 wire-contract changes: Pydantic v2 schema rewrite (`schema.py`), tier
constructor rewrites with newsvendor decoupling (`tiers.py`), `SERVICE_VERSION` bump to `1.2.0`
(`service/schemas.py`), and the accompanying test migrations.

The schema design, shrinkage arithmetic, and confidence formula for Tier 1/2 are correct. The
service version constant is consistent with the test assertion. The Pydantic band-invariant
validator in `ProductRecommendation` is sound.

One blocker: a latent crash in `tier_3_ml_forecast` when the LightGBM model emits a negative
prediction. The `demand_lower` floor is correctly clamped to `0.0`, but `predicted_demand` is
not, breaking the `demand_lower <= predicted_demand` invariant enforced by the model_validator
and crashing the entire recommend call with an unhandled `ValidationError`. The existing Tier 3
tests never trigger this because synthetic training data keeps predictions positive.

Five warnings follow, covering a misleading field docstring, an unclamped formula that is safe
only by an implicit engine precondition, a redundant `strict=False` that silently swallows
model shape mismatches, and two test quality gaps.

---

## Critical Issues

### CR-01: `tier_3_ml_forecast` crashes on negative model predictions

**File:** `src/meshek_ml/recommendation/tiers.py:163-165`

**Issue:** `demand_lower` is floored at `0.0` via `max(0.0, mu_f - residual_std)`, but
`predicted_demand` is set directly to `round(mu_f, 4)` without any floor. When a LightGBM model
emits a negative `mu_f` (possible during warmup, feature drift, or with sparse training data),
the resulting field values satisfy `demand_lower=0.0 > predicted_demand=mu_f`, which violates
the `demand_lower <= predicted_demand <= demand_upper` invariant enforced by
`ProductRecommendation.band_contains_estimate`. Pydantic raises `ValidationError` inside
`tier_3_ml_forecast`; it propagates uncaught through `RecommendationEngine.recommend()` and
reaches the FastAPI handler as an unhandled 500.

The existing `test_predicted_demand_non_negative` integration test (test_tier_3.py:44) does not
catch this because the synthetic training distribution never produces negative predictions.

**Fix:**
```python
# tiers.py lines 159-165 — clamp mu_f before building the fields
mu_f = max(0.0, float(mean_demand))   # clamp negative model output
recs.append(
    ProductRecommendation(
        product_id=str(product),
        unit="kg",
        predicted_demand=round(mu_f, 4),
        demand_lower=round(max(0.0, mu_f - float(residual_std)), 4),
        demand_upper=round(mu_f + float(residual_std), 4),
        ...
    )
)
```

Add a unit test that passes a mock model returning `[-1.0]` and asserts
`rec.predicted_demand >= 0` and `rec.demand_lower <= rec.predicted_demand`.

---

## Warnings

### WR-01: `Signal.contribution` docstring contradicts all usage

**File:** `src/meshek_ml/recommendation/schema.py:29`

**Issue:** The field docstring states: _"contribution is signed and in raw demand units (kg) —
same scale as predicted_demand"_. Every tier hardcodes `contribution=1.0`, which is a
dimensionless weight, not a demand quantity. The meshek companion app and any future consumer
reading the OpenAPI description will interpret `contribution` as a kg value (e.g. "this signal
contributed 1 kg") which is semantically wrong. The docstring and actual contract are
inconsistent.

**Fix:** Correct the docstring to reflect the actual usage (dimensionless weight or fraction
summing to 1.0), or change the field name/type to make the intent unambiguous before Phase 14
locks the Literal:
```python
contribution: float
"""Relative weight of this signal (dimensionless, between 0 and 1).
Phase 14 will enforce sum-to-1 across a recommendation line's signals."""
```

---

### WR-02: `tier_2_pooled_priors` confidence formula has no clamp — safe only by engine invariant

**File:** `src/meshek_ml/recommendation/tiers.py:78`

**Issue:** The docstring specifies confidence interpolates _"linearly from 0.3 at n=1 to 0.6 at
n=13 days"_. The formula `0.3 + (0.6 - 0.3) * ((max(1, n_days) - 1) / 12)` produces values
above `0.6` when `n_days > 13` (e.g. `n_days=20` yields `0.775`). The engine never calls
`tier_2_pooled_priors` with `n_days >= 14`, so the production path is safe, but a direct call
from a test or a future refactored router would silently exceed the documented range without any
error. This also means `test_confidence_bounds` (test_tier_2.py:42-48) only validates the
boundary endpoints because it never probes values outside `[1, 13]`.

**Fix:** Add an explicit clamp after the formula:
```python
confidence = min(0.6, 0.3 + (0.6 - 0.3) * ((max(1, n_days) - 1) / 12))
```

---

### WR-03: `zip(strict=False)` in `tier_3_ml_forecast` silently masks model shape mismatches

**File:** `src/meshek_ml/recommendation/tiers.py:157`

**Issue:** `strict=False` is the Python default — the keyword argument is redundant. More
importantly, its presence is misleading: it signals an intentional decision to tolerate length
mismatches between `last_rows["product"]` and `mu`. If `model.predict(x)` ever returns a
different number of rows than `x` (a real possibility with some model serialization bugs or
wrapper APIs), the zip silently truncates the shorter side. The result would be a
`RecommendationResponse` with fewer `ProductRecommendation` entries than products, surfacing as
a silent data loss rather than a crash.

**Fix:** Use `strict=True` to make a length mismatch an immediate `ValueError`:
```python
for product, mean_demand in zip(last_rows["product"], mu, strict=True):
```

---

### WR-04: Band-invariant test only covers `demand_lower > predicted`; misses `demand_upper < predicted`

**File:** `tests/recommendation/test_schema.py:87-88`

**Issue:** `test_product_recommendation_fields` tests the band invariant by passing
`demand_lower=9.0, demand_upper=8.0` against `predicted_demand=8.0`. This exercises the case
where `lower > predicted` (and simultaneously `upper < lower`). It does not separately test the
case where `lower` is valid but `demand_upper < predicted_demand` (e.g.,
`predicted=10, lower=8, upper=9`). Full coverage requires both violation directions to be tested
independently. The missing case is exactly the scenario that CR-01's negative-prediction bug
would produce after a partial fix.

**Fix:**
```python
# Existing test (lower > predicted):
with pytest.raises(ValidationError):
    ProductRecommendation(**_valid_product_rec_kwargs(demand_lower=9.0, demand_upper=8.0))

# Add: upper < predicted (lower valid):
with pytest.raises(ValidationError):
    ProductRecommendation(**_valid_product_rec_kwargs(
        predicted_demand=10.0, demand_lower=7.0, demand_upper=9.0
    ))
```

---

### WR-05: `test_response_contract_rec04` asserts `is not None` on required Pydantic fields

**File:** `tests/recommendation/test_engine.py:122-123`

**Issue:**
```python
assert resp.recommendations[0].reasoning_tier is not None
assert resp.recommendations[0].confidence_score is not None
```
`reasoning_tier` is typed `ReasoningTier` (a `Literal`) and `confidence_score` has `ge=0.0` —
both are required fields with no `Optional` annotation. Pydantic v2 raises `ValidationError`
during construction if either is absent or `None`, so these assertions are tautologically true:
the object cannot exist in a state where they are `None`. The test provides zero coverage value
and gives false confidence that the wire contract is being checked.

**Fix:** Replace with assertions that actually validate contract properties:
```python
assert resp.recommendations[0].reasoning_tier in ("category_default", "pooled_prior", "ml_forecast")
assert 0.0 <= resp.recommendations[0].confidence_score <= 1.0
```

---

_Reviewed: 2026-05-04T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
