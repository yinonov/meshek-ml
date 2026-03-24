# meshek-ml

## What This Is

meshek-ml is a research codebase for forecasting demand and optimizing inventory for small produce merchants using synthetic and, increasingly, real sales data. The next product step is a team-usable Google Colab workflow that can train a LightGBM forecasting model end to end on synthetic data first and then on a strict-schema real daily sales table.

## Core Value

Make forecasting training reproducible and easy to run in Colab so the team can move from local research code to repeatable model experiments on both synthetic and real data.

## Requirements

### Validated

- ✓ Generate synthetic merchant-product demand datasets with seasonality and spoilage-aware patterns — existing simulation layer in `src/meshek_ml/simulation/`
- ✓ Persist and reload experiment datasets as parquet files — existing IO utilities in `src/meshek_ml/common/io.py`
- ✓ Build forecasting features from merchant/product time series data — existing feature engineering in `src/meshek_ml/forecasting/features.py`
- ✓ Evaluate forecasting outputs with project metrics utilities — existing evaluation helpers in `src/meshek_ml/forecasting/evaluation.py`
- ✓ Partition merchant-level datasets for federated experiments — existing data partitioning in `src/meshek_ml/federated/partitioning.py`

### Active

- [ ] Run a fresh Colab notebook setup successfully for the forecasting workflow
- [ ] Generate synthetic training data inside Colab and train one LightGBM forecasting model end to end
- [ ] Load real daily sales data with a strict required schema: `date`, `merchant_id`, `product`, `quantity`
- [ ] Reuse the same forecasting path for synthetic and real data with minimal notebook branching
- [ ] Report evaluation metrics clearly inside the notebook output for team review
- [ ] Document the required real-data schema and assumptions so the pipeline fails fast when inputs do not match

### Out of Scope

- Full federated learning training in Colab — not needed for the first forecasting training release
- PPO or inventory optimization training in Colab — separate workflow with different runtime and success criteria
- Flexible schema mapping for arbitrary source columns — deferred until the strict-schema pipeline is stable
- Transaction-level aggregation logic — deferred because v1 assumes a daily sales table is already prepared

## Context

- The repository is a brownfield Python ML workbench with implemented simulation, forecasting feature utilities, optimization components, and federated partitioning, but several top-level runnable pipelines are still placeholders.
- `scripts/run_forecast.py` and `src/meshek_ml/forecasting/pipeline.py` are not implemented yet, so there is no current end-to-end forecasting training command.
- There is an existing Colab-oriented notebook at `notebooks/colab_quickstart.ipynb`, but it does not currently provide the target forecasting training workflow.
- `data/raw/` and `data/processed/` do not yet contain a staged real dataset; real-data support will depend on loading a strict-schema daily sales table from Drive or another Colab-accessible source.
- The primary audience for this next stage is the internal team, not external users.

## Constraints

- **Execution environment**: Google Colab first — the training path must work in a fresh hosted notebook session
- **Model scope**: LightGBM first — keep the first supported training path narrow enough to finish end to end
- **Data contract**: Strict schema — fail fast unless real data exposes `date`, `merchant_id`, `product`, and `quantity`
- **Workflow shape**: Synthetic first, then real data — the synthetic path should prove the pipeline before real-data debugging starts
- **Codebase state**: Brownfield repo with partial orchestration — new work should reuse existing forecasting utilities instead of inventing a second path

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Start with forecasting in Colab, not optimization or federated training | Forecasting is the immediate goal and has the clearest path from existing code to usable training | — Pending |
| Support LightGBM as the first model path | It matches the existing forecasting direction and keeps the first implementation narrow | — Pending |
| Require a strict real-data schema | The team needs a reliable v1 path before adding schema-mapping flexibility | — Pending |
| Make synthetic and real data share one training path | Avoid duplicated notebook logic and keep evaluation comparable across sources | — Pending |

---
*Last updated: 2026-03-24 after initialization*