---
phase: 06-recommendation-engine
plan: 01
subsystem: recommendation
tags: [contracts, scaffolding, pydantic, service-extra]
requires: [phase-05-storage]
provides:
  - meshek_ml.recommendation.schema:RecommendationResponse
  - meshek_ml.recommendation.schema:ProductRecommendation
  - meshek_ml.recommendation.config:CategoryDefaultsConfig
  - meshek_ml.recommendation.config:load_category_defaults
  - meshek_ml.storage:get_data_root
  - meshek_ml.service.state:AppState
affects: [pyproject.toml, configs/recommendation/]
tech_stack:
  added: [fastapi, httpx, joblib, pyyaml]
  patterns: [pydantic-v2, yaml.safe_load, dataclass-app-state]
key_files:
  created:
    - configs/recommendation/category_defaults.yaml
    - src/meshek_ml/recommendation/__init__.py
    - src/meshek_ml/recommendation/schema.py
    - src/meshek_ml/recommendation/config.py
    - src/meshek_ml/service/__init__.py
    - src/meshek_ml/service/state.py
    - tests/recommendation/__init__.py
    - tests/recommendation/test_schema.py
    - tests/recommendation/test_config.py
  modified:
    - pyproject.toml
    - src/meshek_ml/storage/__init__.py
decisions: [D-13, D-14]
requirements: [REC-04]
requirements_completed:
  - REC-01
  - REC-02
  - REC-03
  - REC-04
  - INFRA-01
metrics:
  duration: ~5m
  tasks: 2
  tests_added: 6
  tests_total_green: 41
  completed: 2026-04-14
---

# Phase 6 Plan 01: Wave 1 Contracts and Scaffolding Summary

Locked the downstream-facing pydantic contracts (`RecommendationResponse`,
`ProductRecommendation`, `CategoryDefaultsConfig`), the `service.AppState`
dataclass, and the public `storage.get_data_root()` helper so Waves 2-4 can
import against stable names.

## What Shipped

- **`service` optional-extra** in `pyproject.toml` pinning
  `fastapi>=0.135,<0.136`, `httpx>=0.27`, `joblib>=1.3`, `pyyaml>=6.0`. Added
  to the `all` aggregate.
- **`configs/recommendation/category_defaults.yaml`** — Tier 1 fixture with
  tomato/cucumber/onion default quantities in kg. Parsed via `yaml.safe_load`
  (T-6-03 mitigation).
- **`meshek_ml.recommendation.schema`** — `ReasoningTier` literal plus the
  two pydantic models. `confidence_score` constrained to `[0.0, 1.0]` via
  `Field(ge=0.0, le=1.0)`. `reasoning_tier` rejects unknown values at
  construction time.
- **`meshek_ml.recommendation.config`** — `CategoryDefaultProduct`,
  `CategoryDefaultsConfig`, and `load_category_defaults(path)` loader that
  intentionally propagates `FileNotFoundError`.
- **`meshek_ml.service.state.AppState`** dataclass with `model`, `model_path`,
  `residual_std`, and `feature_cols` (default empty list) fields. Documents
  the contract with Plan 04's lifespan hook.
- **`meshek_ml.storage.get_data_root()`** — public wrapper around the
  previously private `_data_root`. Fixes the reach-in anti-pattern flagged in
  06-RESEARCH.md and unblocks a Phase 6 PooledStore without coupling it to
  private Phase 5 internals.

## Tests

- `tests/recommendation/test_schema.py` (4 tests): required fields, literal
  rejection, confidence bounds ({-0.1, 1.1} reject; {0.0, 0.2, 0.95, 1.0}
  accept), ProductRecommendation field requirements.
- `tests/recommendation/test_config.py` (2 tests): YAML roundtrip returns
  `CategoryDefaultsConfig` with ≥3 products; missing-file path raises
  `FileNotFoundError`.
- Full run: `pytest tests/recommendation tests/storage -q --no-cov` → **41
  passed**. Phase 5 storage regression untouched.

## Verification

```
$ .venv/bin/python -m pytest tests/recommendation tests/storage -q --no-cov
41 passed in 0.55s
```

`tomllib` parse of `pyproject.toml` confirms the `service` extra resolves to
`['fastapi>=0.135,<0.136', 'httpx>=0.27', 'joblib>=1.3', 'pyyaml>=6.0']`.
`yaml.safe_load` of the Tier 1 fixture returns the expected product list.
Smoke import of `get_data_root` + `AppState` succeeds.

## Decisions Made

- **D-13 locked**: `RecommendationResponse` shape frozen — merchant_id,
  recommendations, reasoning_tier, confidence_score, generated_at.
- **D-14 locked**: `ProductRecommendation` = {product_id, quantity, unit}.
- **New**: `get_data_root()` exposed publicly from `meshek_ml.storage`;
  downstream packages must not reach into `_data_root`.

## Deviations from Plan

None — plan executed exactly as written. The verify one-liner in the plan had
a minor bug (`tomllib.loads(... .decode())` passed bytes to a str-only API);
switched to `tomllib.load(open(..., 'rb'))` during verification. Not a code
change, so not tracked as a deviation against the repo.

## Threat Model Follow-Up

T-6-03 (yaml.safe_load) enforced in `config.py` and covered by the
acceptance-criteria grep pattern. T-6-01 / T-6-02 were accepted dispositions;
no code changes needed.

## Self-Check: PASSED

Files verified present:
- FOUND: configs/recommendation/category_defaults.yaml
- FOUND: src/meshek_ml/recommendation/schema.py
- FOUND: src/meshek_ml/recommendation/config.py
- FOUND: src/meshek_ml/service/state.py
- FOUND: src/meshek_ml/service/__init__.py
- FOUND: tests/recommendation/test_schema.py
- FOUND: tests/recommendation/test_config.py

Commits verified in git log:
- FOUND: 5ef05ef feat(06-01): add recommendation schemas, config loader, and service extra
- FOUND: e03b3ba feat(06-01): add public storage.get_data_root() and service.AppState
