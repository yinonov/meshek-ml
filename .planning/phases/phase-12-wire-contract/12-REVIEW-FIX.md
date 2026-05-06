---
phase: phase-12-wire-contract
fixed_at: 2026-05-04T00:00:00Z
review_path: .planning/phases/phase-12-wire-contract/12-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 12: Code Review Fix Report

**Fixed at:** 2026-05-04T00:00:00Z
**Source review:** .planning/phases/phase-12-wire-contract/12-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6
- Fixed: 6
- Skipped: 0

## Fixed Issues

### CR-01: `tier_3_ml_forecast` crashes on negative model predictions

**Files modified:** `src/meshek_ml/recommendation/tiers.py`, `tests/recommendation/test_tier_3.py`
**Commits:** `d22cf61` (tiers.py clamp), `e061f24` (unit test)
**Applied fix:**
Added `mu_f = max(0.0, float(mean_demand))` on line 159 of `tiers.py` before building
the `ProductRecommendation` fields. This ensures a negative model output is clamped to 0.0
before `predicted_demand`, `demand_lower`, and `demand_upper` are computed, preventing the
`demand_lower <= predicted_demand` validator from firing. Also added
`test_negative_prediction_clamped_to_zero` in `test_tier_3.py`: builds a 30-day single-product
sales DataFrame, mocks `model.predict` to return `np.array([-1.0])`, and asserts
`rec.predicted_demand >= 0` and `rec.demand_lower <= rec.predicted_demand`.

---

### WR-01: `Signal.contribution` docstring contradicts all usage

**Files modified:** `src/meshek_ml/recommendation/schema.py`
**Commit:** `325cdf4`
**Applied fix:**
Rewrote the `Signal` class docstring to remove the incorrect "raw demand units (kg)" language.
The new text states `contribution` is "a relative weight (dimensionless, between 0 and 1) — not
a demand quantity in kg" and notes Phase 14 will enforce sum-to-1 across signals per
recommendation line.

---

### WR-02: `tier_2_pooled_priors` confidence formula has no clamp

**Files modified:** `src/meshek_ml/recommendation/tiers.py`
**Commit:** `d22cf61`
**Applied fix:**
Wrapped the tier-2 confidence formula with `min(0.6, ...)` so
`confidence = min(0.6, 0.3 + (0.6 - 0.3) * ((max(1, n_days) - 1) / 12))`. Direct calls with
`n_days > 13` now stay within the documented [0.3, 0.6] range instead of silently exceeding it.

---

### WR-03: `zip(strict=False)` silently masks model shape mismatches

**Files modified:** `src/meshek_ml/recommendation/tiers.py`
**Commit:** `d22cf61`
**Applied fix:**
Changed `zip(last_rows["product"], mu, strict=False)` to `zip(..., strict=True)` on line 158.
If `model.predict` ever returns a different number of rows than products, Python raises
`ValueError` immediately rather than silently truncating the shorter side.

---

### WR-04: Band-invariant test only covers `demand_lower > predicted`

**Files modified:** `tests/recommendation/test_schema.py`
**Commit:** `519653b`
**Applied fix:**
Added a second `pytest.raises(ValidationError)` block inside `test_product_recommendation_fields`
using `predicted_demand=10.0, demand_lower=7.0, demand_upper=9.0`. This exercises the orthogonal
violation direction where `lower` is valid but `demand_upper < predicted_demand`.

---

### WR-05: `test_response_contract_rec04` asserts `is not None` on required Pydantic fields

**Files modified:** `tests/recommendation/test_engine.py`
**Commit:** `5b3ba1c`
**Applied fix:**
Replaced the two tautological `is not None` assertions with:
```python
assert resp.recommendations[0].reasoning_tier in (
    "category_default", "pooled_prior", "ml_forecast"
)
assert 0.0 <= resp.recommendations[0].confidence_score <= 1.0
```
These validate actual wire contract properties that can meaningfully fail.

---

## Verification Results

**pytest:** `92 passed, 1 skipped` (docker smoke skipped — requires running container)
```
PYTHONPATH=/tmp/sv-12-reviewfix-jEtW7y/src pytest tests/recommendation/ tests/service/ -x --tb=short -q
92 passed, 1 skipped in 6.79s
```

**ruff (modified files only):** `All checks passed!`
```
ruff check src/meshek_ml/recommendation/tiers.py src/meshek_ml/recommendation/schema.py
All checks passed!
```
Note: Two pre-existing ruff warnings in `cli_train.py` (I001) and `engine.py` (UP035) are
unrelated to these changes and were present before Phase 12.

---

_Fixed: 2026-05-04T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
