# Feature Landscape

**Domain:** Team-usable Google Colab forecasting training workflow for small ML teams
**Project:** meshek-ml
**Researched:** 2026-03-25
**Overall confidence:** MEDIUM

## Framing

This milestone is not a general forecasting platform. It is a brownfield Colab workflow that must prove one narrow path end to end:

1. Start from a fresh Colab session.
2. Generate synthetic daily demand data inside the notebook.
3. Train and evaluate one LightGBM forecasting model.
4. Switch to a strict-schema real daily sales table with the same training path.

Because the repo already has synthetic generation, feature engineering, evaluation helpers, and a LightGBM wrapper, table-stakes features should be the minimum needed to make that path reliable and repeatable for the internal team. Differentiators should improve team usability without widening scope into a platform rewrite.

## Table Stakes

Features users will expect from a usable v1. Missing any of these will make the Colab workflow feel unfinished or fragile.

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| Fresh-session Colab bootstrap | Colab is ephemeral. The notebook has to work from a clean runtime without hidden local setup. | Low | Colab runtime, project install path, Python deps | Include one setup section for installs, imports, Drive mounting or file access, and seed/config initialization. |
| Synthetic-first end-to-end run | The project requirement is to prove the forecasting path before debugging real data. | Medium | `src/meshek_ml/simulation/`, `src/meshek_ml/common/io.py` | This is the safest first validation path and should produce a train/eval artifact in one run. |
| Strict real-data schema validation | The active requirement explicitly calls for fail-fast validation on `date`, `merchant_id`, `product`, `quantity`. | Medium | Notebook loader, pandas validation step, shared preprocessing | Validation should check required columns, parseable dates, nulls in key fields, and non-negative numeric quantity assumptions if required by the pipeline. |
| One shared pipeline for synthetic and real data | The project explicitly wants minimal notebook branching. | Medium | Common normalization/preprocessing function, forecasting feature builder | Synthetic data will need to be reshaped into the same column contract as real data before feature generation. |
| Time-aware train/validation split | A forecasting workflow that leaks future data is not credible, even for internal use. | Medium | Forecast pipeline implementation, pandas sorting/grouping | Split by date, not random rows. This is table stakes for trustworthiness. |
| LightGBM training with validation metrics | The milestone is LightGBM-first. The notebook must show a real fit/evaluate loop, not only feature generation. | Medium | `lightgbm`, `src/meshek_ml/forecasting/tree_models.py`, eval helpers | LightGBM supports validation inputs, callbacks, and early stopping surfaces, so the workflow should expose them rather than fit blindly. |
| Clear notebook metrics output | Team review depends on seeing results inline without reading raw objects. | Low | `src/meshek_ml/forecasting/evaluation.py`, notebook display cells | Show a compact metrics table and a few prediction examples per merchant/product slice. |
| Persisted outputs to a Colab-accessible location | Team members need artifacts that survive the runtime. | Low | Google Drive mount or explicit download path, `common/io.py` | Save metrics, prepared dataset sample, and model artifact or serialized config summary. |
| Reproducible run controls | Internal ML collaboration breaks down quickly when seeds, date ranges, and params are implicit. | Low | Existing seed utilities, notebook parameter cell | A single parameter cell is enough for v1. No need for a full experiment UI. |
| Failure messages that point to the data contract | In a small team workflow, debugging time matters more than perfect abstraction. | Low | Schema validation step, notebook assertions/exceptions | Errors should state which required columns are missing or malformed and stop before model training. |

## Differentiators

These features are not required for the first usable workflow, but they create real leverage for a small ML team without pushing the milestone into platform territory.

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| Source toggle with the same notebook flow | Lets the team switch between synthetic and real data by changing one parameter rather than editing cells. | Medium | Shared loader interface, common schema normalization | This is the highest-value differentiator because it reinforces the milestone goal of one path for both sources. |
| Schema audit report before training | Gives reviewers immediate visibility into row counts, date span, merchant/product cardinality, nulls, and dropped rows. | Low | pandas profiling summary, validation layer | This is especially useful when onboarding real daily sales tables from different teammates. |
| Baseline comparison against a naive forecast | Makes LightGBM results easier to interpret and prevents accidental regressions hidden behind absolute metrics. | Medium | Forecast evaluation helpers, simple baseline implementation | A seasonal naive or last-value baseline is enough. Avoid a large model bake-off. |
| Feature summary cell | Shows which lag, rolling, and calendar features were created, making the notebook easier to review and debug. | Low | `src/meshek_ml/forecasting/features.py` | This is more valuable here than advanced explainability because the team is still stabilizing the pipeline contract. |
| Lightweight experiment manifest | Save params, data source, schema version, split dates, and metrics to a JSON or parquet sidecar in Drive. | Medium | Drive persistence, notebook metadata cell, `common/io.py` | This gives the team comparability across Colab runs without needing MLflow in v1. |
| Compact artifact export | Store trained model, metrics, and a small predictions sample in a predictable folder structure. | Medium | Serialization path, Drive mount | This improves handoff between teammates and reduces rerun pressure in ephemeral runtimes. |
| Review-ready notebook structure | Distinct sections for setup, data contract, feature build, train, evaluate, and export reduce onboarding friction. | Low | Notebook organization only | This is a UX differentiator, not a technical one, but it matters in small teams. |

## Anti-Features

Features to deliberately exclude from v1 because they add complexity faster than they add value for the immediate Colab milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Flexible schema mapping for arbitrary column names | It directly conflicts with the milestone's strict-schema requirement and will turn early debugging into ingestion debugging. | Require exactly `date`, `merchant_id`, `product`, and `quantity`, then add mapping later only after the contract is stable. |
| Multi-model training framework | Comparing LightGBM, XGBoost, Prophet, and Darts in the same notebook will delay the missing end-to-end pipeline and widen test gaps. | Ship one LightGBM path with one simple baseline. |
| Large hyperparameter sweep tooling | Colab is an ephemeral notebook environment, and the current codebase lacks a canonical forecast pipeline. Sweeps would amplify instability. | Expose a small parameter cell with a few safe overrides and optional early stopping. |
| Federated learning or inventory optimization in the same workflow | Both are explicitly out of scope for this milestone and already have incomplete orchestration in the repo. | Keep the notebook forecasting-only. |
| Transaction-level aggregation logic | The project requirement assumes a prepared daily sales table already exists. Adding aggregation introduces a second data-contract problem. | Accept only daily-grain input in v1. |
| Heavy interactive widget UI | Widgets look helpful but usually make notebooks harder to diff, review, and maintain in team settings. | Prefer plain parameter cells and explicit function calls. |
| External experiment tracking platform integration | MLflow, W&B, or custom dashboards are operationally heavier than the current problem requires. | Save a local manifest and artifacts to Drive first. |
| Advanced explainability stack as a milestone requirement | SHAP dashboards and deep error slicing are useful later, but they are not needed to prove the training path works. | Show feature importance and a few prediction slices only if cheap to add. |
| GPU-specific or distributed training requirements | The target model is LightGBM on daily sales data for a small team. Requiring special runtimes would make notebook adoption worse. | Keep CPU-first and let Colab acceleration remain optional. |

## Feature Dependencies

```text
Fresh-session bootstrap -> Synthetic-first run -> Shared pipeline -> LightGBM training -> Metrics output -> Artifact export
Strict schema validation -> Shared pipeline for real data -> Real-data training
Time-aware split -> Credible evaluation -> Baseline comparison
Schema audit report -> Faster real-data debugging
```

## MVP Recommendation

Prioritize:
1. Fresh-session Colab bootstrap with deterministic config cell.
2. Synthetic-first end-to-end training using the repo's existing simulation and forecasting utilities.
3. Strict-schema real-data load plus fail-fast validation.
4. One shared LightGBM training/evaluation path for both sources.
5. Clear metrics display and artifact export to Drive.

Defer:
- Flexible schema mapping: It fights the current contract and should wait until the strict path is stable.
- Multi-model experimentation: The repo does not yet have one canonical forecasting pipeline.
- Heavy experiment tracking: A lightweight manifest is enough for the immediate team workflow.
- Federated or optimization extensions: Separate milestone, separate runtime concerns.

## Recommendation For Roadmap Use

For this brownfield milestone, roadmap phases should be organized around workflow reliability rather than feature breadth:

1. Colab bootstrap and dependency setup.
2. Shared data contract and preprocessing path.
3. LightGBM forecast training and evaluation pipeline.
4. Real-data handoff and artifact persistence.
5. Small differentiators such as schema audit reporting and baseline comparison.

That order matches the repo's current gap: the codebase already has reusable building blocks, but it lacks the canonical forecasting orchestration layer that makes Colab team-usable.

## Sources

- Project context: `.planning/PROJECT.md`
- Codebase architecture: `.planning/codebase/ARCHITECTURE.md`
- Codebase risks and gaps: `.planning/codebase/CONCERNS.md`
- LightGBM Python API and scikit-learn wrapper docs: https://lightgbm.readthedocs.io/en/latest/Python-API.html
- LightGBM `LGBMRegressor` fit/validation surface: https://lightgbm.readthedocs.io/en/latest/pythonapi/lightgbm.LGBMRegressor.html
- Colab official product overview: https://developers.google.com/colab
- Colab external data access notebook: https://colab.research.google.com/notebooks/io.ipynb
