# Project Research Summary

**Project:** meshek-ml
**Domain:** Brownfield Colab forecasting workflow for daily sales and synthetic demand data
**Researched:** 2026-03-25
**Confidence:** HIGH

## Executive Summary

This milestone is not a general forecasting platform. It is a narrow Google Colab training workflow for the existing meshek-ml codebase: start from a fresh Colab session, generate synthetic daily data, train one LightGBM model end to end, then run the same path on strict-schema real daily sales data. The recommended approach is package-first and CPU-first: keep orchestration in a single notebook, but move all reusable logic into the forecasting package so Colab remains a thin client over validation, normalization, feature engineering, training, evaluation, and artifact export.

The core implementation choice is to normalize both sources into one canonical forecasting table before feature engineering. In practice that means validating real inputs against `date`, `merchant_id`, `product`, `quantity`, then deriving the package target column `realized_demand` from `quantity` so the existing feature code can stay central. The main delivery risk is not model quality, but workflow drift: if schema handling, panel cleanup, split logic, or model fitting live in notebook cells, the repo will end up with a second untested pipeline. The roadmap should therefore prioritize bootstrap, canonical data contract, real-data panel validation, temporal training, and only then notebook hardening.

## Key Findings

### Recommended Stack

Use one Google Colab CPU notebook backed by the existing `meshek_ml` package, with pandas and pyarrow for tabular IO, LightGBM 4.x as the only supported model, and Google Drive for real-data ingress plus durable artifact storage. Work on a staged parquet dataset in `/content` during runtime, then write models, metrics, config snapshots, and prediction samples back to Drive.

**Core technologies:**
- Google Colab CPU runtime: execution surface for the internal team and the target operating environment.
- `meshek_ml` package installed with forecasting extras: reuse existing simulation, forecasting, evaluation, and IO code instead of rebuilding logic in notebooks.
- `pandas` + `pyarrow`: canonical data-frame and parquet path for schema-safe staging.
- `lightgbm>=4`: single supported training model and baseline tabular forecaster.
- `scikit-learn`: time-aware split helpers and notebook-friendly model utilities.

### Expected Features

The workflow needs a fresh-session bootstrap, a synthetic-first end-to-end run, strict real-data schema validation, one shared pipeline for synthetic and real data, a time-aware train/validation split, clear inline metrics, and persisted artifacts. The highest-value usability additions are a source toggle, a schema audit summary, and a lightweight run manifest. Anything that widens scope, especially flexible schema mapping, multi-model experiments, transaction aggregation, or external tracking, should stay out of v1.

**Must have (table stakes):**
- Fresh-session Colab bootstrap and dependency validation.
- Synthetic-first end-to-end LightGBM training.
- Strict validation for `date`, `merchant_id`, `product`, `quantity`.
- One shared forecast path for synthetic and real sources.
- Time-based validation split with clear notebook metrics and artifact export.

**Should have (competitive):**
- Single source toggle in the notebook.
- Schema audit report before training.
- Naive baseline comparison and compact run manifest.

**Defer (v2+):**
- Flexible schema mapping.
- Multi-model or sweep framework.
- Transaction-level aggregation and heavy notebook UI.
- External experiment tracking and advanced explainability requirements.

### Architecture Approach

The notebook should only handle environment setup, Drive access, parameter selection, one pipeline call, and result display. The package should own schema enforcement, source loading, canonical normalization, feature generation, temporal splitting, LightGBM training, evaluation, and artifact writing.

**Major components:**
1. Notebook bootstrap: install dependencies, mount Drive, set parameters, and render outputs.
2. Dataset contract layer: load synthetic or real data and normalize both into `date`, `merchant_id`, `product`, `realized_demand`.
3. Forecast pipeline: build lag, rolling, and calendar features; split by time; train LightGBM; evaluate; persist artifacts.

### Critical Pitfalls

1. **Divergent synthetic and real paths**: avoid per-source notebook branches by normalizing both inputs into one canonical forecasting table before features.
2. **Temporal leakage from sort and split mistakes**: sort inside the shared pipeline by merchant, product, and date, and never use random splits.
3. **Broken panel assumptions on real data**: validate duplicate daily keys and missing-day gaps before lag and rolling features are computed.
4. **Sales vs demand semantic drift**: label the first real-data model honestly as sales forecasting unless stockout or availability signals are added.
5. **Implementing the workflow in Colab instead of the package**: keep notebook cells thin and put reusable logic in `src/meshek_ml/forecasting/` so tests and future CLI entrypoints use the same path.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Colab Bootstrap and Dependency Validation
**Rationale:** The workflow must succeed in a fresh hosted session before any modeling work is credible.
**Delivers:** One setup notebook, minimal install path, Drive mount flow, version checks, and deterministic runtime config.
**Addresses:** Fresh-session bootstrap and reproducible run controls.
**Avoids:** Dependency drift and oversized optional installs.

### Phase 2: Canonical Forecasting Dataset Contract
**Rationale:** Synthetic and real sources cannot share one pipeline until target semantics and schema normalization are fixed.
**Delivers:** Strict schema validation, source adapters, and canonical normalization to `realized_demand`.
**Addresses:** Shared pipeline, strict schema validation, fail-fast data contract messaging.
**Avoids:** Divergent target naming and notebook-only schema fixes.

### Phase 3: Real Daily Sales Ingestion and Panel Validation
**Rationale:** Real data introduces duplicates, missing days, and semantic issues that synthetic data does not expose.
**Delivers:** Real-data loader, duplicate-key checks, missing-day analysis, optional daily aggregation policy, and schema audit reporting.
**Addresses:** Reliable real-data handoff and faster debugging.
**Avoids:** Corrupted lag meaning and hidden panel sparsity issues.

### Phase 4: Temporal LightGBM Train and Evaluation Pipeline
**Rationale:** Once the data contract is stable, the package needs the missing orchestration layer that actually trains and scores forecasts.
**Delivers:** Pipeline entry point, feature generation orchestration, date-based holdout split, validation-aware LightGBM fit with early stopping, metrics, and artifact export.
**Addresses:** Time-aware split, LightGBM training, metrics output, and persisted outputs.
**Avoids:** Temporal leakage, fixed-estimator overtraining, and result inconsistency across runs.

### Phase 5: Notebook Hardening and Regression Tests
**Rationale:** The final step is to prove the notebook is a thin client over tested package logic rather than a separate implementation.
**Delivers:** Stable notebook structure, package-level integration tests, and regression coverage for sorting, schema errors, and synthetic end-to-end runs.
**Addresses:** Team usability and brownfield reliability.
**Avoids:** Drift between Colab and the repo’s runnable path.

### Phase Ordering Rationale

- Bootstrap first because every later phase depends on a repeatable Colab runtime.
- Canonical contract before model work because source convergence is the key architectural decision.
- Real-data validation before training hardening because panel integrity problems will invalidate downstream metrics.
- Notebook hardening last because the notebook should wrap the package pipeline, not define it.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3:** Real-data panel handling policy if the team’s daily sales exports contain duplicates or sparse calendars.
- **Phase 4:** LightGBM validation-window and categorical handling details if real cardinality is materially higher than synthetic tests.

Phases with standard patterns (skip research-phase):
- **Phase 1:** Standard Colab bootstrap, Drive mounting, and dependency validation.
- **Phase 2:** Straightforward schema enforcement and source normalization using existing package conventions.
- **Phase 5:** Standard regression-test and notebook-thin-client patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Strong repo fit and aligned with standard Colab + LightGBM usage. |
| Features | MEDIUM | Product expectations are clear, but some usability additions remain team-preference driven. |
| Architecture | HIGH | The package-first pattern is directly supported by the current repo structure and gaps. |
| Pitfalls | MEDIUM | Risks are credible and repo-specific, but real-data quality is still unknown until ingestion lands. |

**Overall confidence:** HIGH

### Gaps to Address

- Real-data cleanliness: validate whether merchant-product-day keys are unique and whether missing dates represent zero sales or missing observations.
- Real target semantics: confirm whether `quantity` should be treated as sales only in v1 or whether additional availability signals exist.
- Colab install recipe: confirm the minimum dependency set needed for LightGBM without pulling unnecessary forecasting extras.

## Sources

### Primary (HIGH confidence)
- `.planning/PROJECT.md` — milestone scope, constraints, and active requirements.
- `.planning/research/STACK.md` — recommended runtime, libraries, and artifact strategy.
- `.planning/research/ARCHITECTURE.md` — package-first workflow and component boundaries.

### Secondary (MEDIUM confidence)
- `.planning/research/FEATURES.md` — table-stakes feature set and deliberate anti-features.
- `.planning/research/PITFALLS.md` — brownfield failure modes and sequencing risks.

---
*Research completed: 2026-03-25*
*Ready for roadmap: yes*
