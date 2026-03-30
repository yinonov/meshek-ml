# Phase 2: Forecasting Pipeline - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Implement the missing `pipeline.py` orchestrator that chains existing feature engineering, LightGBM training, and evaluation utilities into one callable pipeline, with strict schema validation and parameter controls.

Deliverables:
1. `src/meshek_ml/forecasting/pipeline.py` — implemented (currently a stub raising NotImplementedError)
2. Schema validation for real data with strict `date`, `merchant_id`, `product`, `quantity` columns
3. Parameter cell in notebook controlling source, paths, dates, seed
4. Forecasting section in `notebooks/colab_quickstart.ipynb` exercising the pipeline

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key constraints from ROADMAP success criteria:
- pipeline.py must orchestrate: load → validate schema → feature engineer → time-based split → train LightGBM → evaluate
- One parameter cell controls source choice, input/output paths, date range, and seed
- Notebook must output MAE, RMSE, WMAPE, and pinball loss after training
- Real data with wrong schema must trigger clear fail-fast error before training starts
- Synthetic and real data flow through the same pipeline code path after schema validation

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/meshek_ml/forecasting/features.py` — add_lag_features(), add_rolling_features(), add_calendar_features() — FULLY FUNCTIONAL
- `src/meshek_ml/forecasting/tree_models.py` — train_lightgbm(), train_xgboost() — FULLY FUNCTIONAL
- `src/meshek_ml/forecasting/evaluation.py` — mae(), rmse(), wmape(), pinball_loss(), compute_all_metrics() — FULLY FUNCTIONAL
- `src/meshek_ml/simulation/generator.py` — run_simulation() — generates synthetic data
- `src/meshek_ml/common/io.py` — file I/O utilities
- `src/meshek_ml/common/seed.py` — global seed setting for reproducibility
- `src/meshek_ml/forecasting/pipeline.py` — STUB: raises NotImplementedError, signature defined
- `src/meshek_ml/forecasting/schema.py` — may exist, check before creating
- `src/meshek_ml/forecasting/datasets.py` — may exist, check before creating

### Established Patterns
- Pydantic dataclasses for schemas (src/meshek_ml/common/schemas.py)
- Hydra for configuration
- Trackio for experiment tracking
- pyproject.toml with modular extras

### Integration Points
- Pipeline called from notebook cells
- Parameter cell at top of notebook
- Existing simulation section generates data that feeds into forecasting

</code_context>

<specifics>
## Specific Ideas

- The pipeline should work as both an importable function and from the notebook
- Schema validation should use Pydantic or pandas-based validation consistent with existing patterns
- Time-based split: train on earlier dates, validate on later dates (not random)
- Feature engineering reuses existing features.py functions — no new features needed for v1

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
