# Architecture Research: Colab Forecasting Training Workflow

**Project:** meshek-ml
**Research focus:** Brownfield forecasting training architecture for Google Colab
**Analysis date:** 2026-03-25
**Confidence:** HIGH for repo fit, MEDIUM for final Colab UX details until implementation lands

## Recommendation

The Colab workflow should be a thin orchestration notebook over a package-first forecasting pipeline. The notebook should do only four things:

1. Install and import the repo in a fresh Colab runtime.
2. Choose a data source: synthetic or strict-schema real daily sales.
3. Call one package entry point that validates data, engineers features, trains LightGBM, and returns metrics plus artifacts.
4. Render metrics, sample predictions, and artifact locations for team review.

That structure fits the current codebase because the reusable pieces already exist in the package:
- Synthetic generation exists in `src/meshek_ml/simulation/generator.py`.
- File IO exists in `src/meshek_ml/common/io.py`.
- Feature engineering exists in `src/meshek_ml/forecasting/features.py`.
- LightGBM training exists in `src/meshek_ml/forecasting/tree_models.py`.
- Forecast metrics exist in `src/meshek_ml/forecasting/evaluation.py`.
- The missing piece is orchestration in `src/meshek_ml/forecasting/pipeline.py`, which is currently a stub.

The key architectural decision for this milestone is to normalize both synthetic and real inputs into one canonical training table before feature engineering starts. In this repo, that means converting the strict real schema `date`, `merchant_id`, `product`, `quantity` into the forecasting pipeline's expected target shape by materializing a canonical target column such as `realized_demand` from `quantity`. That avoids branching through the rest of the pipeline and lets the existing feature code remain the center of gravity.

## Target Workflow Shape

```text
Colab notebook
  -> runtime bootstrap
  -> choose source (synthetic | real strict-schema)
  -> package loader/validator
  -> canonical daily demand table
  -> feature builder
  -> train/validation split
  -> LightGBM trainer
  -> evaluator
  -> artifact writer
  -> notebook display cells
```

The notebook is the operator surface. The package remains the implementation surface.

## Recommended Component Boundaries

| Component | Location | Responsibility | Should Not Do |
|-----------|----------|----------------|---------------|
| Colab bootstrap notebook | `notebooks/` | Environment setup, parameter selection, Drive mounting, calling package APIs, rendering outputs | Contain business logic for validation, feature engineering, splitting, or model training |
| Data contract and normalization | `src/meshek_ml/forecasting/` | Validate strict real-data schema, coerce types, sort rows, fail fast on violations, rename or derive canonical target columns | Reach into notebook widgets or train models |
| Synthetic dataset loader | `src/meshek_ml/forecasting/` calling `src/meshek_ml/simulation/` | Generate or load synthetic demand data and convert to canonical training table | Duplicate simulation logic already in `simulation/generator.py` |
| Real dataset loader | `src/meshek_ml/forecasting/` calling `src/meshek_ml/common/io.py` | Load CSV or parquet from Colab-accessible storage and enforce the strict daily schema | Support arbitrary schema mapping in v1 |
| Feature builder | `src/meshek_ml/forecasting/features.py` plus a thin orchestrator | Add lag, rolling, and calendar features against the canonical table | Decide which source is synthetic vs real |
| Split builder | `src/meshek_ml/forecasting/pipeline.py` or adjacent helper | Create train/validation/test ranges with time ordering preserved | Randomly shuffle time series data |
| Model trainer | `src/meshek_ml/forecasting/tree_models.py` | Fit LightGBM with repo config defaults | Load raw files or parse notebook inputs |
| Evaluator | `src/meshek_ml/forecasting/evaluation.py` | Compute MAE, RMSE, WMAPE, pinball loss, and produce evaluation tables | Own feature engineering or raw data validation |
| Artifact persistence | `src/meshek_ml/common/io.py` plus pipeline helper | Save processed data snapshots, predictions, metrics, and model files to `outputs/` or `models/` | Decide notebook presentation layout |
| Thin CLI wrapper | `scripts/run_forecast.py` | Later expose the same package pipeline outside Colab | Reimplement pipeline logic |

## Canonical Table Contract

The repo currently has a mismatch:
- Synthetic data and feature code are centered on demand-style columns such as `realized_demand`.
- The milestone requires real data with strict schema columns `date`, `merchant_id`, `product`, `quantity`.

The cleanest fix is an early normalization step that emits one canonical forecasting table with these required columns:

| Column | Type | Rule |
|--------|------|------|
| `date` | datetime64[ns] | Required, normalized to daily resolution |
| `merchant_id` | string | Required, non-null |
| `product` | string | Required, non-null |
| `realized_demand` | numeric | Required canonical target; for real data this is copied from `quantity` |

Optional columns may be carried through when available, but the training path should depend only on the canonical set above in v1.

This design is specific to the current repo state: it preserves the existing default target convention in `src/meshek_ml/forecasting/features.py` and avoids a deeper refactor across multiple partial forecasting modules.

## Recommended Package Additions

The current forecasting package has feature functions, model wrappers, and metrics, but no usable end-to-end training architecture. The next milestone should add a small number of focused modules instead of growing the notebook.

### 1. Strict-schema validation module

**Recommended file:** `src/meshek_ml/forecasting/schema.py`

Responsibilities:
- Validate the presence of `date`, `merchant_id`, `product`, `quantity` for real data.
- Parse `date` safely and fail on invalid values.
- Reject null keys or non-numeric quantities.
- Enforce one row per merchant-product-date if that is the project assumption.
- Produce a canonical table with `realized_demand`.

Why here:
- The repo has limited runtime validation today.
- This milestone explicitly requires fail-fast schema checks.
- Keeping this in-package prevents the notebook from becoming the source of truth for data assumptions.

### 2. Dataset source adapter module

**Recommended file:** `src/meshek_ml/forecasting/datasets.py`

Responsibilities:
- `load_synthetic_training_data(...)`
- `load_real_training_data(path, format)`
- `to_canonical_forecasting_frame(df, source)`

Why here:
- Synthetic and real sources should converge before feature engineering.
- Source-specific loading is different, but downstream training should be the same.

### 3. Pipeline orchestrator

**Recommended file:** `src/meshek_ml/forecasting/pipeline.py`

Responsibilities:
- Accept source selection and pipeline parameters.
- Call validation and normalization.
- Build features using existing feature functions.
- Drop rows that are not yet feature-complete because of lags and rolling windows.
- Create a strict time-based split.
- Train LightGBM using `train_lightgbm()`.
- Score predictions using `compute_all_metrics()`.
- Return structured outputs for notebook display and artifact saving.

This should become the single authoritative training entry point for both Colab and the future CLI.

### 4. Optional artifact helper

**Recommended file:** `src/meshek_ml/forecasting/artifacts.py`

Responsibilities:
- Save metrics JSON or CSV.
- Save predictions parquet.
- Save feature matrix snapshot for debugging.
- Save model object if persistence is required in this milestone.

This is optional. If the implementation stays small, artifact writing can live in `pipeline.py` first and split out later.

## Notebook and Package Division of Responsibility

The notebook should be intentionally thin because Colab is a volatile environment and this repo is already package-oriented.

### Notebook responsibilities

Recommended cell groups:
1. Environment bootstrap.
2. Imports and runtime configuration.
3. Data source selection.
4. Synthetic or real path parameters.
5. One pipeline invocation.
6. Metrics display.
7. Sample prediction inspection.
8. Artifact summary and optional download links.

The notebook may contain convenience code for:
- `pip install -e` or equivalent Colab setup.
- Mounting Google Drive.
- Setting obvious parameters such as source type, date split, and horizon.
- Human-readable plots and tables.

### Package responsibilities

The package should own:
- Schema enforcement.
- Canonical table normalization.
- Data loading from file paths.
- Feature engineering orchestration.
- Train/validation split logic.
- Model fitting.
- Metric computation.
- Artifact persistence.
- Error messages that explain why strict-schema data failed.

### Boundary rule

If a piece of logic would also be needed by `scripts/run_forecast.py` or tests, it belongs in `src/meshek_ml/forecasting/`, not in the notebook.

## End-to-End Data Flow

### Synthetic path

1. Colab notebook selects `source = synthetic`.
2. Notebook calls a forecasting dataset adapter.
3. Adapter invokes `src/meshek_ml/simulation/generator.py` or loads a saved synthetic parquet through `src/meshek_ml/common/io.py`.
4. Adapter converts the synthetic frame to the canonical training table, ensuring `date`, `merchant_id`, `product`, and `realized_demand` are present and typed correctly.
5. Pipeline runs lag, rolling, and calendar features from `src/meshek_ml/forecasting/features.py`.
6. Pipeline drops warm-up rows created by lags and rolling windows.
7. Pipeline splits by time using a configurable cutoff date.
8. Pipeline trains LightGBM through `src/meshek_ml/forecasting/tree_models.py`.
9. Pipeline predicts on the holdout window.
10. Pipeline evaluates through `src/meshek_ml/forecasting/evaluation.py`.
11. Pipeline saves outputs to `outputs/forecasting/` and optionally `models/forecasting/`.
12. Notebook renders metrics and sample predictions.

### Real strict-schema path

1. Colab notebook mounts Drive or references an uploaded file.
2. Notebook calls the same forecasting dataset adapter with a real path.
3. Adapter loads CSV or parquet through `src/meshek_ml/common/io.py`.
4. Schema validation checks for exactly the required columns: `date`, `merchant_id`, `product`, `quantity`.
5. Validation coerces types, rejects bad rows, and creates `realized_demand = quantity`.
6. The frame now joins the same downstream path as synthetic data.
7. Feature engineering, time split, training, evaluation, and artifact writing are identical to the synthetic case.

### Architectural consequence

The only branch should be in source loading and early normalization. After that, the path should be shared.

## Major Interfaces

A practical interface for the brownfield repo is:

```python
result = run_forecast_pipeline(
    source="synthetic" | "real",
    data_path="/content/drive/MyDrive/.../sales.parquet" | None,
    train_end_date="2024-06-30",
    horizon=7,
    model_type="lightgbm",
    save_dir="outputs/forecasting/colab_run",
)
```

And a structured return payload should contain at least:

```python
{
    "metrics": {...},
    "predictions": predictions_df,
    "feature_columns": [...],
    "train_rows": int,
    "test_rows": int,
    "artifacts": {
        "metrics_path": str,
        "predictions_path": str,
        "model_path": str | None,
    },
}
```

This return shape is useful in Colab because it separates machine-readable results from notebook presentation.

## Time-Series Design Rules

The training workflow should enforce the following rules at the package level:
- Sort by `merchant_id`, `product`, `date` before feature generation.
- Never use random train/test splits.
- Drop rows with incomplete lag or rolling history after feature generation.
- Train one tabular model across all merchant-product series first; do not build per-series notebooks in v1.
- Treat missing required daily rows as a data-quality concern to surface explicitly, not something to silently fill in the notebook.

These rules are appropriate for this milestone because they keep the first Colab path narrow and compatible with the existing feature functions.

## What Not to Build Yet

To keep the milestone aligned with the current repo state, do not add the following in the first pass:
- Flexible column mapping for arbitrary real datasets.
- A second forecasting path that bypasses `src/meshek_ml/forecasting/pipeline.py`.
- Separate notebook-specific feature code.
- Federated forecasting orchestration in Colab.
- Inventory optimization logic in the forecasting notebook.
- Heavy experiment-management infrastructure beyond saving outputs and metrics.

## Build-Order Implications

The implementation order matters because the repo already has partial forecasting pieces and the notebook should not become the integration layer.

### Phase 1: Canonical data contract first

Build:
- `src/meshek_ml/forecasting/schema.py`
- `src/meshek_ml/forecasting/datasets.py`

Why first:
- The strict-schema real-data requirement is the highest-risk part of the milestone.
- It determines the exact handoff into feature engineering.
- Without this, synthetic and real paths will diverge immediately.

Expected outcome:
- One canonical forecasting frame shared by both sources.
- Fail-fast validation that can be tested independently from Colab.

### Phase 2: Pipeline orchestration second

Build:
- Real implementation in `src/meshek_ml/forecasting/pipeline.py`

Why second:
- The package needs one reusable entry point before notebook work starts.
- The current repo already has model and metric helpers waiting to be wired together.

Expected outcome:
- A callable training function that works from local Python, tests, and Colab.

### Phase 3: Artifact writing and readable outputs third

Build:
- Save metrics, predictions, and optionally the trained model.

Why third:
- Team review in Colab depends on visible outputs, not just in-memory objects.
- Persisted artifacts make debugging real-data issues much easier.

Expected outcome:
- Reproducible outputs under `outputs/` and `models/`.

### Phase 4: Colab notebook fourth

Build:
- A forecasting-specific notebook, ideally separate from the existing optimization-oriented `notebooks/colab_quickstart.ipynb`.

Why fourth:
- Once the package API is stable, the notebook becomes simple glue instead of hard-to-test logic.
- This avoids rework when validation or pipeline details change.

Expected outcome:
- A fresh Colab session can run synthetic first, then real data, through the same package entry point.

### Phase 5: Thin CLI wrapper last

Build:
- Upgrade `scripts/run_forecast.py` into a wrapper around `run_forecast_pipeline()`.

Why last:
- It should expose the same logic already proven in package tests and Colab.
- Building the CLI earlier would duplicate integration effort while the pipeline is still moving.

Expected outcome:
- One training path available in both local CLI and Colab.

## Build Order Summary

```text
schema + normalization
  -> dataset adapters
  -> forecasting pipeline
  -> artifact persistence
  -> Colab notebook
  -> thin CLI wrapper
```

## Repo-Specific Architecture Notes

- Reuse `src/meshek_ml/common/io.py` for file loading and saving rather than adding notebook-only file utilities.
- Keep forecasting logic under `src/meshek_ml/forecasting/`; do not create a new Colab-only package area.
- Preserve `scripts/run_forecast.py` as a wrapper, mirroring the existing project pattern where scripts are thin entry points.
- Prefer a new forecasting notebook over mutating the current `notebooks/colab_quickstart.ipynb`, because that notebook is explicitly oriented around optimization and PPO.
- Keep configuration initially simple and function-argument driven if Hydra wiring is not ready; the current forecasting script is still a placeholder, so full config plumbing can remain incremental.

## Architecture Risks

### Risk 1: Synthetic and real paths drift

If synthetic data goes straight into feature engineering while real data gets notebook-specific preprocessing, the team will end up maintaining two training workflows.

Mitigation:
- Force both sources through one normalization interface before feature engineering.

### Risk 2: Strict schema is validated too late

If schema checks happen after feature generation or model training starts, Colab failures will be noisy and expensive to debug.

Mitigation:
- Validate required columns and types immediately after load.

### Risk 3: Notebook absorbs package logic

If split logic, feature lists, or artifact naming live in notebook cells, the future CLI and tests will diverge from Colab.

Mitigation:
- Treat the notebook as a client of `run_forecast_pipeline()`, not as the pipeline itself.

### Risk 4: Existing target-column assumptions are ignored

The current feature code defaults to `realized_demand`. If the new workflow leaves the real dataset as `quantity` all the way through, either notebook branching or broader refactors will be required.

Mitigation:
- Normalize to `realized_demand` at the schema boundary.

## Recommended Final Architecture

For this milestone, the best architecture is:
- One forecasting-specific Colab notebook.
- One shared package pipeline in `src/meshek_ml/forecasting/pipeline.py`.
- One strict-schema normalization layer that converts real sales data into the repo's canonical target shape.
- Zero downstream branching between synthetic and real sources after normalization.
- Thin local CLI support added only after the package pipeline works in Colab.

That design is the smallest change that fits the current brownfield repo, reuses the code that already exists, and keeps the future local CLI and tests aligned with the Colab workflow.
