# Domain Pitfalls

**Domain:** First Google Colab LightGBM forecasting workflow on an existing ML research codebase
**Project:** meshek-ml
**Researched:** 2026-03-25
**Confidence:** MEDIUM-HIGH

## Recommended Future Phases

Use these phase names consistently when turning the risks below into milestone work:

1. **Phase 1 - Colab bootstrap and dependency validation**
2. **Phase 2 - Canonical forecasting dataset contract**
3. **Phase 3 - Real daily sales ingestion and panel validation**
4. **Phase 4 - Temporal LightGBM train/validation pipeline**
5. **Phase 5 - Notebook hardening and regression tests**

## Critical Pitfalls

### Pitfall 1: Treating strict-schema real sales as a drop-in replacement for simulation output

**What goes wrong:**
The current forecasting helpers are written around simulation-shaped data. `src/meshek_ml/forecasting/features.py` defaults to `target_col="realized_demand"`, while the planned real-data contract only guarantees `date`, `merchant_id`, `product`, and `quantity`. If the notebook mixes these concepts informally, synthetic runs will work and real-data runs will fail late, or worse, both paths will keep separate branches.

**Why it is likely in this repo:**
The simulation path already emits `realized_demand`, but there is no implemented shared forecasting pipeline yet in `src/meshek_ml/forecasting/pipeline.py` or `scripts/run_forecast.py`.

**Warning signs:**
- Notebook cells contain `if synthetic` / `if real_data` branches just to rename columns.
- Feature functions are called with different target column names in different cells.
- Metrics code works on synthetic data but breaks only after loading the real table.
- The notebook introduces one-off renames instead of a single canonical normalization function.

**Prevention strategy:**
- Normalize both synthetic and real inputs into one canonical forecasting DataFrame before any feature engineering.
- Make that contract explicit: `date`, `merchant_id`, `product`, `target`, plus any optional engineered columns.
- Map simulation `realized_demand -> target` and real `quantity -> target` in one loader function.
- Fail fast on missing required columns and on unexpected extras that shadow required names.
- Keep the notebook thin: it should call the same normalization function for both sources.

**Future phase:** Phase 2 - Canonical forecasting dataset contract

### Pitfall 2: Silent temporal leakage from unsorted data and split logic that ignores panel boundaries

**What goes wrong:**
`add_lag_features()` and `add_rolling_features()` assume input is already sorted by date, but they do not enforce sorting. On real daily sales data, unsorted imports, mixed merchant-product ordering, or feature generation before the train/validation split can leak future values into training features.

**Why it is likely in this repo:**
The placeholder pipeline currently exposes a single `train_end_date` argument but no implemented split policy. The feature helpers are simple and readable, but they trust caller discipline.

**Warning signs:**
- Validation metrics look suspiciously strong on the first real-data attempt.
- Re-running the same notebook after a sort change materially changes model quality.
- Lag columns for a merchant-product pair do not line up with the immediately preceding calendar day.
- Train and validation row counts change when only sort order changes.

**Prevention strategy:**
- Sort by `merchant_id`, `product`, `date` inside the shared pipeline, not in notebook cells.
- Apply all temporal splits before fitting any validation-aware model selection logic.
- Add explicit assertions that each merchant-product group is monotonic in date.
- Add a regression test that shuffles rows before pipeline entry and verifies identical outputs after the internal sort.
- Keep train, validation, and test windows date-based and global so merchants are compared on the same horizon.

**Future phase:** Phase 4 - Temporal LightGBM train/validation pipeline

### Pitfall 3: Assuming each row is a valid daily panel observation when the real table may have duplicates or missing days

**What goes wrong:**
Grouped shifts and rolling windows operate on row order, not on an implied complete calendar. If the real table has duplicate `(date, merchant_id, product)` rows or missing days for some series, lag and rolling features stop meaning "1 day ago" and become "previous row". That breaks the core forecasting assumption without throwing an error.

**Why it is likely in this repo:**
The milestone explicitly moves from synthetic data, which is generated as a clean complete daily panel, to real sales data, which usually is not. The existing tests validate synthetic outputs, not messy ingestion.

**Warning signs:**
- Some merchant-product groups have more than one row for the same date.
- A 7-day lag appears non-null even when the series has fewer than 7 actual calendar days of history.
- Real-data row counts vary unpredictably after feature engineering.
- Rolling statistics exist for sparse series that should not yet have enough history.

**Prevention strategy:**
- Validate uniqueness of `(date, merchant_id, product)` before feature generation.
- If duplicates exist, define one allowed aggregation rule early, ideally sum `quantity` per daily key before any model code.
- Reindex each merchant-product series to a complete daily date range and fill missing target days with an explicit policy.
- Record whether filled days are true zero-sales days or unknown missing observations; do not conflate the two.
- Add a panel-integrity report cell in Colab that prints duplicate counts, missing-date counts, and short-history series counts before training.

**Future phase:** Phase 3 - Real daily sales ingestion and panel validation

### Pitfall 4: Forecasting observed sales as if they were true demand

**What goes wrong:**
The synthetic generator models `realized_demand`, but the real-data contract only gives `quantity`. In real operations, `quantity` is often sales, not latent demand. Stockouts, closures, missing SKUs, and manual data corrections can all depress quantity without meaning demand fell. If the notebook presents the output as demand forecasting, the team will over-trust the model.

**Why it is likely in this repo:**
The project language already centers demand forecasting, while the first real schema is intentionally narrow. That mismatch makes semantic drift likely.

**Warning signs:**
- Documentation and notebook text switch between "sales" and "demand" without distinction.
- Low-quantity days cluster around known stock issues or operational anomalies.
- Product series appear to collapse to zero and later recover sharply without seasonal explanation.
- Stakeholders ask why the model predicts lower demand after suspected stockout periods.

**Prevention strategy:**
- Define the first real-data model honestly as a sales forecast unless additional stockout or availability signals are introduced.
- Document this assumption next to the schema contract, not only in prose at the top of the notebook.
- Keep synthetic experiments labeled separately so `realized_demand` is not treated as equivalent to real `quantity`.
- Reserve true demand estimation for a later phase that adds inventory or stockout context.

**Future phase:** Phase 2 - Canonical forecasting dataset contract

### Pitfall 5: Building the forecasting workflow inside Colab instead of in the package

**What goes wrong:**
Because `src/meshek_ml/forecasting/pipeline.py` and `scripts/run_forecast.py` are placeholders, the fastest path is to implement everything in notebook cells. That creates a second orchestration layer which will drift from the repo, bypass tests, and make future automation harder.

**Why it is likely in this repo:**
The brownfield codebase already has implemented modules plus missing runnable entrypoints. That is exactly the situation where notebook glue tends to become the de facto production path.

**Warning signs:**
- The notebook contains more business logic than the package.
- Data validation, feature assembly, and model training are defined in cells instead of `src/meshek_ml/forecasting/`.
- A bug fix is applied in the notebook but not in the Python package.
- Running locally and in Colab produces different results because the notebook path diverged.

**Prevention strategy:**
- Put all reusable logic in package modules first, then call those functions from Colab.
- Limit the notebook to environment setup, path configuration, parameter selection, and result display.
- Treat the notebook as a client of the library, not the implementation site.
- Add at least one package-level integration test that exercises the same path the notebook uses.

**Future phase:** Phase 5 - Notebook hardening and regression tests

## Moderate Pitfalls

### Pitfall 6: Colab environment drift from optional-dependency installs and heavy extras

**What goes wrong:**
The repo currently exposes forecasting dependencies through extras in `pyproject.toml`, including `u8darts[all]`, `lightgbm`, and `xgboost`. For the first LightGBM workflow, pulling large optional stacks into a fresh Colab runtime increases install time, binary compatibility risk, and debugging noise unrelated to the milestone goal.

**Why it is likely in this repo:**
The codebase is research-oriented and multi-pillar. Colab will magnify every unnecessary dependency decision.

**Warning signs:**
- The first notebook cell spends most of its time installing packages.
- Different Colab sessions produce different import failures.
- The notebook needs repeated restart instructions before LightGBM import succeeds.
- Forecasting work is blocked by Darts, Prophet, or XGBoost imports that v1 does not need.

**Prevention strategy:**
- Create a minimal Colab install path for the first milestone: package editable install plus only the LightGBM-specific dependencies needed for the chosen pipeline.
- Add one environment-check cell that imports the exact runtime dependencies and prints versions before loading data.
- Keep Darts, Prophet, and other optional forecasting integrations out of the first Colab path.
- Pin the runtime recipe in the notebook and mirror it in project docs.

**Future phase:** Phase 1 - Colab bootstrap and dependency validation

### Pitfall 7: Training LightGBM with fixed high estimator counts and no validation-based stopping

**What goes wrong:**
The current `train_lightgbm()` wrapper trains `LGBMRegressor` with `n_estimators=500` and no `eval_set`, callbacks, or early stopping. In Colab, that can waste runtime, hide overfitting, and make synthetic-to-real comparisons unstable.

**Why it is likely in this repo:**
The tree wrapper exists, but it is a thin convenience layer, not yet a forecasting training loop.

**Warning signs:**
- Real-data training time is much longer than synthetic with little metric gain.
- Validation performance worsens while training still consumes all estimators.
- The notebook cannot report best iteration or learning curves.
- Different horizons or merchant mixes require ad hoc parameter changes in cells.

**Prevention strategy:**
- Introduce a dedicated validation window and pass it to `LGBMRegressor.fit(eval_set=..., callbacks=...)`.
- Use early stopping and capture `best_iteration_` and `evals_result_` for notebook reporting.
- Surface a small, explicit v1 parameter set through the shared pipeline rather than editing model params inline in Colab.
- Track runtime and metric outputs together so performance regressions are visible.

**Future phase:** Phase 4 - Temporal LightGBM train/validation pipeline

### Pitfall 8: Reusing synthetic calendar assumptions on real data without re-validating them

**What goes wrong:**
The simulation layer includes approximate Israeli holiday logic and strong synthetic seasonal structure. Those assumptions are acceptable for generated data, but if they leak into the real-data path as trusted features or expectations, the first notebook can learn artifacts of the simulator rather than patterns in real sales.

**Why it is likely in this repo:**
Simulation is the most mature part of the codebase. Teams naturally reuse the most complete existing logic.

**Warning signs:**
- Synthetic and real features are identical even though the real schema is much narrower.
- Holiday features appear important immediately without validation against known business events.
- Real-data errors are explained away by claiming the simulator had similar behavior.
- The notebook evaluates success mostly by synthetic parity rather than real-data plausibility.

**Prevention strategy:**
- Keep v1 shared features conservative: calendar basics, lag features, and rolling windows.
- Treat simulation-only fields such as `base_demand`, `seasonal_factor`, `holiday_factor`, and `adjusted_demand` as non-portable.
- If holiday modeling is added for real data, use a real calendar source and validate its effect separately.
- Compare synthetic and real feature availability explicitly in the notebook setup section.

**Future phase:** Phase 3 - Real daily sales ingestion and panel validation

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Colab setup | Installing the full research stack for a narrow LightGBM workflow | Use a minimal pinned dependency path and an environment-check cell |
| Shared dataset contract | Letting `realized_demand` and `quantity` remain two separate target semantics | Normalize both to one canonical `target` column before features |
| Real-data ingestion | Duplicate or sparse daily panel keys silently corrupt lag meaning | Validate uniqueness and reindex to a complete daily panel |
| Model training | Feature leakage from unsorted rows or post-split feature generation | Sort inside pipeline and enforce date-based splits |
| Evaluation | Reporting synthetic and real metrics as if they measure the same target meaning | Label synthetic as demand, real as sales unless more signals are added |
| Notebook delivery | Colab becomes the only runnable orchestration path | Move logic into package code and keep notebook as a thin client |
| Regression safety | No tests cover the new forecasting path | Add deterministic package-level tests with synthetic data and import-gated real-data validation checks |

## Sources

### Repo evidence
- `.planning/PROJECT.md`
- `.planning/codebase/CONCERNS.md`
- `.planning/codebase/TESTING.md`
- `src/meshek_ml/forecasting/features.py`
- `src/meshek_ml/forecasting/tree_models.py`
- `src/meshek_ml/forecasting/pipeline.py`
- `src/meshek_ml/simulation/generator.py`
- `pyproject.toml`

### External references
- LightGBM Python API: `https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.LGBMRegressor.html`
  - Used for current `fit()` support around `eval_set`, `callbacks`, `categorical_feature`, and best-iteration reporting.
- pandas `to_datetime`: `https://pandas.pydata.org/docs/reference/api/pandas.to_datetime.html`
  - Used for strict parsing, `errors='raise'`, and mixed-timezone parsing cautions.
- pandas `DataFrame.merge`: `https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.merge.html`
  - Used for `validate=` and `indicator=` guidance to catch bad joins in ingestion and feature enrichment.
