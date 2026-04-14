---
phase: 06-recommendation-engine
plan: 02
subsystem: recommendation
tags: [tier-1, tier-2, pooled-priors, shrinkage, filesystem-scan]
requires: [phase-06-01]
provides:
  - meshek_ml.recommendation.pooled_store:PooledStore
  - meshek_ml.recommendation.tiers:tier_1_category_defaults
  - meshek_ml.recommendation.tiers:tier_2_pooled_priors
affects: [tests/recommendation/]
tech_stack:
  added: []
  patterns: [filesystem-scan, pooled-shrinkage, pure-function-tiers]
key_files:
  created:
    - src/meshek_ml/recommendation/pooled_store.py
    - src/meshek_ml/recommendation/tiers.py
    - tests/recommendation/conftest.py
    - tests/recommendation/test_pooled_store.py
    - tests/recommendation/test_tier_1.py
    - tests/recommendation/test_tier_2.py
  modified: []
decisions: [D-03, D-04, D-05, D-06]
requirements: [REC-01, REC-02, REC-04]
metrics:
  duration: ~6m
  tasks: 2
  tests_added: 15
  tests_total_green: 21
  completed: 2026-04-14
---

# Phase 6 Plan 02: Wave 2 Tiers 1 and 2 plus PooledStore Summary

Tier 1 category defaults, Tier 2 pooled-prior shrinkage, and the
`PooledStore` cross-merchant aggregator landed as pure functions with no
model/lifespan coupling, ready for Plan 04 engine wiring.

## What Shipped

- **`PooledStore`** (`src/meshek_ml/recommendation/pooled_store.py`)
  - `MIN_HISTORY_DAYS_FOR_PRIOR = 14`
  - `list_merchant_ids()` uses `get_data_root().glob("*.sqlite")` with
    exact-suffix matching (T-6-04 / Pitfall 5) — WAL/SHM sidecars do
    not match. Each stem is re-validated via `_validate_merchant_id`
    wrapped in a safe helper so stray files never crash the scan.
  - `pooled_mean_by_product(exclude_merchant_id=...)` forces callers
    to explicitly name the merchant whose data must not appear in the
    aggregate (T-6-05). Skips merchants with `<14` distinct sale dates.
    Computes per-merchant product means, then averages across merchants.
- **`tier_1_category_defaults`** (`src/meshek_ml/recommendation/tiers.py`)
  - Emits `ProductRecommendation` rows from `CategoryDefaultsConfig`.
  - Fixed `confidence_score=0.2` (D-04) and `reasoning_tier="category_default"`.
- **`tier_2_pooled_priors`** (same module)
  - Shrinkage: `shrink = n_days / (n_days + 14)` (D-05).
  - Blend: `q = shrink * own_mean + (1 - shrink) * pooled_mean`, with
    own-mean falling back to pooled-mean for products the merchant
    has never sold.
  - Confidence: `0.3 + (0.6 - 0.3) * ((max(1, n_days) - 1) / 12)`,
    linear 0.3 → 0.6 across `n_days ∈ [1, 13]` (D-06).
- **Shared test fixtures** (`tests/recommendation/conftest.py`)
  - `data_root` monkeypatches `MESHEK_DATA_DIR` to a per-test tmp dir.
  - `merchant_store_factory` populates a real `MerchantStore` with
    `days × len(products)` rows using `pd.date_range(end="2026-04-13", …)`.
  - `category_defaults_cfg` loads the committed YAML fixture.

## Tests

- `tests/recommendation/test_pooled_store.py` (5): sidecar exclusion,
  empty root, exclude-self, skip-low-history, invalid-stem rejection.
- `tests/recommendation/test_tier_1.py` (4): tier literal, confidence
  0.2, YAML roundtrip, merchant_id propagation.
- `tests/recommendation/test_tier_2.py` (6): tier literal, confidence
  bounds at n=1/n=13, strict monotonic 1..13, shrinkage arithmetic at
  n=7, end-to-end filesystem scan, merchant_id propagation.
- Full run: `.venv/bin/python -m pytest tests/recommendation -q --no-cov`
  → **21 passed**. Storage regression untouched: `tests/storage -q` →
  **35 passed**.

## Verification

```
$ .venv/bin/python -m pytest tests/recommendation -q --no-cov
21 passed in 0.30s

$ .venv/bin/python -m pytest tests/storage -q --no-cov
35 passed in 0.39s
```

## Decisions Applied

- **D-03**: Tier 1 covers 0-day merchants using category defaults.
- **D-04**: Tier 1 confidence locked at `0.2`.
- **D-05**: Tier 2 shrinkage formula `n / (n + 14)`.
- **D-06**: Tier 2 confidence linear `0.3 → 0.6` over `1..13` own-history days.

## Deviations from Plan

**[Minor - process]** Plan 02 Task 1 and Task 2 were structured as
sequential TDD steps but `tier_2_pooled_priors` was written in the same
module edit as `tier_1_category_defaults` during Task 1 (same file,
single Write). Task 2 then only added the test file. Functionally
identical outcome; code coverage and acceptance criteria unchanged.

**[Acceptance grep caveat]** The plan includes `! grep -q '_data_root'
src/meshek_ml/recommendation/pooled_store.py` as an anti-pattern guard.
The module imports the public helper `get_data_root`, which contains
`_data_root` as a substring. The literal grep would therefore fire, but
the semantic intent (no reach into the private `_data_root` symbol) is
satisfied — only `get_data_root` is imported. This is a plan grep-spec
bug, not a code issue.

## Threat Model Follow-Up

- **T-6-04** (mitigate): `Path.glob("*.sqlite")` is exact-suffix and
  re-validated via `_validate_merchant_id_safely`. Enforced by
  `test_list_merchant_ids_excludes_sidecars` and
  `test_invalid_merchant_id_in_file`.
- **T-6-05** (mitigate): `exclude_merchant_id` is a required parameter
  on `pooled_mean_by_product`. Enforced by `test_excludes_self`.
- **T-6-06** (accept): Aggregate means across ≥1 other merchants with
  ≥14 days each; revisit when merchant count drops below 3.
- **T-6-07** (accept): Path.glob is O(n); acceptable for <100 merchants.

## Self-Check: PASSED

Files verified present:
- FOUND: src/meshek_ml/recommendation/pooled_store.py
- FOUND: src/meshek_ml/recommendation/tiers.py
- FOUND: tests/recommendation/conftest.py
- FOUND: tests/recommendation/test_pooled_store.py
- FOUND: tests/recommendation/test_tier_1.py
- FOUND: tests/recommendation/test_tier_2.py

Commits verified in git log:
- FOUND: feat(06-02): add PooledStore scan and tier_1_category_defaults
- FOUND: test(06-02): add tier_2_pooled_priors tests
