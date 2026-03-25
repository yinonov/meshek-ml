# Technology Stack: Colab-Friendly LightGBM Forecast Training

**Project:** meshek-ml
**Milestone Context:** Subsequent brownfield milestone focused on a first end-to-end forecasting training workflow
**Researched:** 2026-03-25
**Overall confidence:** HIGH

## Recommendation Summary

For this milestone, the standard 2026 stack is a **single Google Colab notebook running a CPU runtime**, backed by the existing `meshek_ml` package, using **pandas + pyarrow parquet** for tabular interchange and **LightGBM 4.x** as the only supported forecasting model. Real data should be loaded from **Google Drive** with a strict four-column contract, while synthetic data should be generated inside the same notebook and normalized into the same training schema before feature engineering.

This recommendation is specific to the current repo state. The repository already has usable building blocks for synthetic demand generation, parquet IO, lag/rolling/calendar features, and core forecast metrics. What is missing is not a broader forecasting platform; it is a narrow, repeatable orchestration layer that runs cleanly in a fresh Colab session. That means v1 should optimize for **reliability and low branching**, not for model breadth or notebook cleverness.

The design center should be: **copy repo to Drive or clone into runtime, mount Drive, install the package with forecasting extras, stage one parquet working dataset locally in `/content`, train one LightGBM regressor, save artifacts back to Drive, and render metrics in notebook output**.

## Recommended Stack

### Runtime and Execution

| Layer | Recommendation | Why for this project |
|---|---|---|
| Notebook host | Google Colab managed notebook | The milestone explicitly targets team-usable Colab execution with minimal setup. |
| Runtime type | Standard CPU runtime | Daily retail demand on lag/rolling/calendar features is classic tabular training. CPU is enough for v1, avoids GPU variability, and fits Colab guidance to avoid unused accelerators. |
| Python target | Python 3.10+ package compatibility, tolerate current Colab default runtime version | The repo requires `>=3.10`. Do not overfit the milestone to one transient Colab patch version. |
| Package install | `%pip install -e .[simulation,forecasting]` from repo checkout or Drive copy | Reuses existing package layout and avoids notebook-local duplication of feature logic. |
| Notebook shape | One setup notebook, not a multi-notebook workflow | The missing piece is orchestration. Splitting v1 into multiple notebooks would create avoidable drift. |

### Core Libraries

| Library | Version band | Role in workflow | Why |
|---|---|---|---|
| `pandas` | `>=2.0` already in repo | Main table contract | Existing code is already DataFrame-first across simulation, forecasting, and IO. |
| `pyarrow` | `>=14.0` already in repo | Parquet engine and schema-safe persistence | Best fit for Colab + pandas parquet round-trips and already implied by repo IO/tests. |
| `lightgbm` | `>=4.0` already in repo optional deps | Primary training model | Matches existing wrapper, strong tabular baseline, easy CPU training in Colab. |
| `numpy` | existing repo dependency | Array math and target handling | Already central across feature engineering and metrics. |
| `scikit-learn` | add for v1 notebook/runtime support | Time-based split utilities and optional preprocessing helpers | LightGBM uses a scikit-learn API, and explicit `TimeSeriesSplit` / train-validation utilities are standard for a clean notebook training loop. |
| `matplotlib` | existing repo dependency | Basic residual / feature importance plots | Already present; enough for v1 diagnostics without adding plotting complexity. |

### Data Access and Persistence

| Concern | Recommendation | Why |
|---|---|---|
| Real data ingress | Google Drive mounted via `drive.mount()` | This is the required real-data source for the milestone. |
| Working data format | Parquet for staged training data | Faster and more stable than repeated CSV reads in Colab; aligns with current IO helpers. |
| Raw external real-data allowance | CSV or parquet accepted at notebook boundary, then normalize to parquet immediately | Lets the team load common Drive exports while standardizing the internal path. |
| Local staging during run | Copy working dataset from Drive mount into `/content/...` before feature generation/training | Colab warns Drive mounts are slow and unreliable for many small I/O operations; local staging reduces mount friction. |
| Artifact persistence | Save trained model, metrics JSON, feature list JSON, and run metadata CSV/JSON back to Drive | Colab runtimes are ephemeral; Drive is the durable store for team review. |

## Prescriptive v1 Workflow

### 1. Notebook Setup

The notebook should start with a deterministic setup block:

1. Mount Google Drive.
2. Clone or access the repo.
3. Install the package with `simulation` and `forecasting` extras.
4. Set a seed.
5. Create local working directories under `/content/meshek_ml_runs/...`.

Recommended install pattern:

```bash
%pip install -U pip
%pip install -e .[simulation,forecasting]
```

If the team keeps the repo as a Drive folder instead of cloning inside the runtime, that is acceptable for source code, but the **active training dataset and artifacts should still be copied between Drive and local runtime directories intentionally**, rather than training directly against the mounted path.

### 2. Unified Input Contract

The notebook should support exactly two data entry paths:

| Source | Input expectation | Normalization step |
|---|---|---|
| Synthetic | Generated by existing simulation code | Map or derive training target column into the forecasting path and save staged parquet |
| Real | Daily sales table from Drive with strict schema: `date`, `merchant_id`, `product`, `quantity` | Validate schema, cast dtypes, sort rows, rename `quantity` to the internal target column, save staged parquet |

The important implementation decision is to normalize both branches into **one canonical training frame** before feature engineering. For this repo, that means producing a DataFrame with:

- `date`
- `merchant_id`
- `product`
- one target column used by feature builders and model training

Because `src/meshek_ml/forecasting/features.py` currently defaults to `realized_demand`, the cleanest v1 choice is:

- Synthetic path: keep or derive `realized_demand`
- Real path: rename `quantity` to `realized_demand` after schema validation

That keeps notebook branching low and avoids invasive refactors in the first milestone.

### 3. Schema Validation

Use **strict fail-fast validation** before any feature work.

Recommended validation library choice for v1:

| Option | Recommendation | Why |
|---|---|---|
| `pydantic` | Use for row-agnostic config and schema-contract validation helpers if needed | Already declared in the repo and suitable for clear error messages. |
| Plain pandas checks | Required regardless | Cheapest path for column presence, dtype coercion, null checks, duplicates, and sort validation. |

Minimum real-data validation rules:

- Required columns are exactly present: `date`, `merchant_id`, `product`, `quantity`
- `date` parses cleanly to datetime
- `merchant_id` and `product` are non-null strings or castable identifiers
- `quantity` is numeric and non-negative
- No duplicate rows for the same `date` + `merchant_id` + `product` in v1 unless the notebook explicitly aggregates before validation
- Data is sorted by `merchant_id`, `product`, `date` before lag generation

Do not implement flexible column mapping in v1. The milestone explicitly says strict schema first.

### 4. Feature Engineering

For v1, keep feature generation inside the existing project contract:

| Feature family | Source in repo | Keep for v1? | Notes |
|---|---|---|---|
| Lag features | `forecasting/features.py` | Yes | Core tabular baseline for daily demand |
| Rolling mean/std | `forecasting/features.py` | Yes | Strong baseline signal for retail demand |
| Calendar features | `forecasting/features.py` | Yes | Useful with no extra dependency burden |
| Rich holiday libraries | No | No for v1 | Add later only if baseline underperforms and locale-specific effects matter materially |

The v1 feature policy should be conservative:

- Use lag windows already aligned to daily forecasting: `1, 7, 14, 28`
- Use rolling windows already aligned to weekly/monthly cadence: `7, 14, 28`
- Keep `merchant_id` and `product` as categorical inputs for LightGBM if encoded carefully

For category handling, the practical v1 path is to cast `merchant_id` and `product` to pandas categorical dtype and pass those columns into LightGBM through the DataFrame path. LightGBM’s current docs support categorical features directly and note that categorical inputs should be integer-like under the hood; pandas categoricals are the least disruptive way to make this consistent without one-hot encoding.

### 5. Train/Validation Strategy

This is the most important modeling discipline for the milestone.

Use a **time-based holdout**, not a random split.

Recommended v1 strategy:

- Train on the earlier segment of each merchant-product history
- Validate on the most recent contiguous horizon
- If enough history exists, optionally use `TimeSeriesSplit` for notebook experiments, but keep the primary reported result as one simple holdout window

Why this fits the repo:

- The existing features are time-derived
- Random splits would leak future information through lag/rolling structure
- Team review in Colab is easier when there is one explicit final holdout period

For daily retail demand, the milestone should report at least:

- `mae`
- `rmse`
- `wmape`
- `pinball_loss` if quantile work is kept active

Those already map to `src/meshek_ml/forecasting/evaluation.py`.

### 6. LightGBM Training Configuration

Use **`lightgbm.LGBMRegressor` as the default notebook API** because the repo already wraps it and it is easier to integrate into a notebook-driven training function than dropping immediately to native `lgb.train()`.

Recommended v1 defaults:

| Parameter | Value | Rationale |
|---|---|---|
| `objective` | `regression` | Matches current wrapper and daily quantity prediction baseline |
| `metric` | `mae` | Stable and already used in repo defaults |
| `n_estimators` | start around `500` with early stopping | Already close to current wrapper; final tree count should be selected by validation |
| `learning_rate` | `0.03` to `0.05` | Reasonable CPU-friendly baseline |
| `num_leaves` | `31` to start | Standard baseline for tabular regression |
| `subsample` | `0.8` | Matches current repo wrapper |
| `colsample_bytree` | `0.8` | Matches current repo wrapper |
| `random_state` | explicit fixed seed | Reproducibility in Colab |
| early stopping | required | Officially supported and important for ephemeral notebook runs |

Specific training guidance:

- Add a validation set and use early stopping.
- Persist the best iteration.
- Save the fitted booster with its native model-save method.
- Record feature order used for training so prediction notebooks cannot silently drift.

For artifact format, prefer:

| Artifact | Format | Why |
|---|---|---|
| Model | LightGBM text model via booster `save_model()` | Native, stable, easy to reload, no pickling fragility across notebook sessions |
| Metrics | JSON | Human-readable and easy to diff |
| Training config | JSON or YAML snapshot | Makes notebook runs reproducible |
| Feature list | JSON | Prevents silent train/predict schema mismatch |
| Predictions sample | Parquet | Easy inspection and reuse |

Do not make pickle or joblib the primary artifact format in v1. Native LightGBM model export is safer across changing Colab environments.

### 7. Drive and Artifact Layout

Recommended Drive layout for this repo:

```text
MyDrive/meshek-ml/
  data/
    real/
    synthetic/
    staged/
  artifacts/
    forecasting/
      runs/
        YYYYMMDD_HHMMSS/
          model.txt
          metrics.json
          config.json
          feature_columns.json
          validation_predictions.parquet
  notebooks/
```

This layout is intentionally boring. That is correct for v1. The repo currently has no experiment registry or durable service layer; a timestamped Drive directory is the right operational level.

## Concrete Additions for This Repo

### Add or standardize

| Item | Recommendation |
|---|---|
| Notebook | Add one dedicated Colab forecasting training notebook rather than expanding the placeholder forecasting notebook with many alternate flows |
| Forecast pipeline module | Implement a narrow orchestration function in `src/meshek_ml/forecasting/pipeline.py` that the notebook calls |
| Input validation helper | Add a small utility that validates and normalizes real/synthetic inputs into one canonical DataFrame |
| Config surface | Use one small forecasting config object or YAML snapshot for notebook runs, but do not build full Hydra orchestration yet |
| Optional dependency | Add `scikit-learn` to forecasting extras if time-split utilities are used directly |

### Reuse exactly as-is where possible

| Existing code | Reuse decision |
|---|---|
| `src/meshek_ml/common/io.py` | Keep parquet/csv persistence helpers and extend only if needed for artifact saving |
| `src/meshek_ml/forecasting/features.py` | Keep as the baseline feature builder contract |
| `src/meshek_ml/forecasting/tree_models.py` | Keep LightGBM wrapper shape, but extend with validation-aware fit and seed support |
| `src/meshek_ml/forecasting/evaluation.py` | Keep as the notebook metrics layer |
| `src/meshek_ml/simulation/` | Use as the synthetic source of truth |

## What Not To Use for v1

These exclusions matter as much as the positive recommendation.

| Do not use | Why not for this milestone |
|---|---|
| Darts as the primary training abstraction | The repo declares it, but v1 needs one narrow tabular baseline and Darts would add orchestration and dependency surface without solving the current gap. |
| Prophet | Useful for some series, but it is a different modeling path and does not fit the shared synthetic/real tabular workflow goal. |
| XGBoost as a parallel baseline in the same milestone | The repo already has an adapter, but supporting two tree stacks doubles notebook branching and artifact logic before the first path is stable. |
| GPU runtime | LightGBM demand forecasting here is tabular CPU work; GPU adds runtime variability and wastes Colab quota if not clearly needed. |
| Direct training against mounted Drive files | Colab docs warn Drive I/O can be slow and error-prone for many operations. Stage locally in `/content` first. |
| Flexible schema mapping UI | Out of scope by milestone definition. Strict schema is the right v1 discipline. |
| MLflow / Weights & Biases / external tracking service | Overkill for the current repo maturity; timestamped Drive artifacts are enough for the first team-usable workflow. |
| Pickle-first model persistence | More fragile across Colab sessions and package changes than native LightGBM save/load. |
| Full Hydra notebook orchestration | The repo has config pieces but not a working runtime. Building full Hydra support now would be architecture work, not milestone-focused workflow delivery. |
| Federated or optimization hooks in the training notebook | Explicitly out of scope and would contaminate the clean forecasting path. |

## Confidence and Rationale

| Area | Confidence | Notes |
|---|---|---|
| Colab notebook + Drive workflow | HIGH | Based on current Colab docs and the milestone requirement itself. |
| pandas + pyarrow parquet as canonical data path | HIGH | Strong fit with existing repo IO plus current pandas parquet guidance. |
| LightGBM 4.x as primary model | HIGH | Already present in repo optional deps and supported by current official docs. |
| CPU-only runtime recommendation | HIGH | Consistent with Colab guidance and the workload shape. |
| `scikit-learn` addition for split utilities | MEDIUM | Standard and pragmatic, but this part is a recommendation derived from workflow needs rather than an existing repo dependency. |
| Native LightGBM artifact save over pickle/joblib | HIGH | Directly supported by official LightGBM docs and safer in ephemeral notebook environments. |

## Sources

- Google Colab FAQ: https://research.google.com/colaboratory/faq.html
- LightGBM Python API: https://lightgbm.readthedocs.io/en/stable/Python-API.html
- LightGBM Python package intro: https://lightgbm.readthedocs.io/en/stable/Python-Intro.html
- LightGBM early stopping callback: https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.early_stopping.html
- LightGBM Booster save/load docs: https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.Booster.html
- pandas parquet write docs: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_parquet.html
- pandas parquet read docs: https://pandas.pydata.org/docs/reference/api/pandas.read_parquet.html
