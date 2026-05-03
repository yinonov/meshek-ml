---
phase: 06
slug: recommendation-engine
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-14
---

# Phase 06 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Sourced from `06-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.4+ with `pytest-cov`, markers `slow` and `integration` |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` + existing `tests/conftest.py` |
| **Quick run command** | `pytest tests/recommendation tests/service -q --no-cov` |
| **Full suite command** | `pytest -q --no-cov` |
| **Estimated runtime** | ~5 s quick / ~15 s full (69 tests green post-Phase 5) |

---

## Sampling Rate

- **After every task commit:** `pytest tests/recommendation tests/service -q --no-cov`
- **After every plan wave:** `pytest -q --no-cov` (full regression — keep Phase 5 green)
- **Before `/gsd-verify-work`:** Full suite green + `test_engine_e2e` passes covering all three tiers
- **Max feedback latency:** < 5 s quick, < 15 s full

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | REC-04 | RecommendationResponse rejects unknown literals | unit | `pytest tests/recommendation/test_schema.py -q --no-cov` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | REC-04 | CategoryDefaultsConfig YAML round-trip | unit | `pytest tests/recommendation/test_config.py -q --no-cov` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 2 | REC-01 | Tier 1 returns `category_default` + `confidence_score == 0.2` | unit | `pytest tests/recommendation/test_tier_1.py -q --no-cov` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 2 | REC-02 | Tier 2 returns `pooled_prior` + `confidence_score` in [0.3, 0.6] | unit | `pytest tests/recommendation/test_tier_2.py -q --no-cov` | ❌ W0 | ⬜ pending |
| 06-02-03 | 02 | 2 | REC-02 | PooledStore excludes self + WAL sidecars | unit | `pytest tests/recommendation/test_pooled_store.py -q --no-cov` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 3 | REC-03 | `train_and_save` writes joblib bundle w/ residual std | unit+int | `pytest tests/recommendation/test_training.py -q --no-cov` | ❌ W0 | ⬜ pending |
| 06-03-02 | 03 | 3 | REC-03, INFRA-01 | `model_io.load_model` path-traversal safe; loaded model predicts finite | unit+int | `pytest tests/recommendation/test_model_io.py tests/recommendation/test_tier_3.py -q --no-cov -m "not slow"` | ❌ W0 | ⬜ pending |
| 06-04-01 | 04 | 4 | REC-01..04 | Engine routes 0 / 7 / 30 day merchants to correct tier end-to-end | integration | `pytest tests/recommendation/test_engine.py tests/recommendation/test_engine_e2e.py -q --no-cov` | ❌ W0 | ⬜ pending |
| 06-04-02 | 04 | 4 | INFRA-01 | Lifespan loads model exactly once; raises on missing file | integration | `pytest tests/service/test_lifespan.py -q --no-cov` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Sampling Rate (Nyquist Validation)

The five ROADMAP success criteria collapse to **3 observable axes** — tier routing, response contract, and startup loading. Each axis needs ≥2 independent samples (one positive, one boundary/negative) to pass Nyquist.

### Axis A — Tier routing (ROADMAP success 1, 2, 3)
Sample at `n_days` ∈ {0, 13, 14, 30}. Four samples cover both the Tier-1/2 and Tier-2/3 boundaries plus interior of Tier 1 and Tier 3. This is the minimum sampling that detects an off-by-one in tier selection.

Tests: `test_tier_1.py`, `test_tier_2.py`, `test_tier_3.py`, `test_engine.py::test_tier_boundary_13_days`, `test_engine.py::test_tier_boundary_14_days`, `test_engine_e2e.py`.

### Axis B — Response contract (ROADMAP success 4, REC-04)
Every tier test asserts the full `RecommendationResponse` pydantic model round-trips and contains `reasoning_tier` + `confidence_score` in the documented range. Sampled in all three tier unit tests plus `test_engine.py::test_confidence_bounds` (≥4 positive samples, plus pydantic validator rejects unknowns).

### Axis C — Lifespan startup (ROADMAP success 5, INFRA-01)
Three samples:
1. **Happy path** — file exists, loads, `app.state.ml` non-null (`test_loads_on_startup`)
2. **Fail-fast** — file missing, raises at startup (`test_missing_model_file`)
3. **Isolation** — subsequent `recommend()` calls do NOT reopen the file; `joblib.load` called exactly once across N requests (`test_model_not_reloaded` / `test_loader_called_once`)

---

## Wave 0 Requirements

- [ ] `tests/recommendation/__init__.py` — package marker
- [ ] `tests/recommendation/conftest.py` — shared fixtures: `trained_lightgbm_model` (session-scoped), `merchant_store_factory`, `populated_data_root`
- [ ] `tests/recommendation/test_schema.py`
- [ ] `tests/recommendation/test_config.py`
- [ ] `tests/recommendation/test_tier_1.py`
- [ ] `tests/recommendation/test_tier_2.py`
- [ ] `tests/recommendation/test_tier_3.py` (marked `integration`)
- [ ] `tests/recommendation/test_pooled_store.py`
- [ ] `tests/recommendation/test_training.py`
- [ ] `tests/recommendation/test_model_io.py`
- [ ] `tests/recommendation/test_engine.py`
- [ ] `tests/recommendation/test_engine_e2e.py` (marked `integration`)
- [ ] `tests/service/__init__.py`
- [ ] `tests/service/conftest.py` — `model_path` fixture (joblib-dumped trained model)
- [ ] `tests/service/test_lifespan.py`
- [ ] `configs/recommendation/category_defaults.yaml`
- [ ] `pyproject.toml` — add `service` optional-extra (`fastapi>=0.135,<0.136`, `httpx>=0.27`, `joblib>=1.3`)

---

## Manual-Only Verifications

*None — all Phase 6 behaviors have automated verification.*

HTTP surface and Docker container (INFRA-02) are explicitly deferred to Phase 8 per ROADMAP.md and therefore out of scope for Phase 6 validation.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15 s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending execution
