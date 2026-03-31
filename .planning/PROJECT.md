# meshek-ml

## What This Is

meshek-ml is a research codebase for forecasting demand and optimizing inventory for small produce merchants (Israeli greengrocers), combining LightGBM demand forecasting with PPO-based inventory optimization in a reproducible Colab pipeline. The project validates its ML method choices against 8 academic papers on perishable goods management and uses a two-stage architecture: forecast demand first, then optimize ordering.

## Core Value

Deliver one reproducible Colab workflow that trains a LightGBM forecast and benchmarks a newsvendor/PPO optimization — grounded in academic evidence for each method choice.

## Requirements

### Validated

- ✓ Generate synthetic merchant-product demand datasets with seasonality and spoilage-aware patterns — v1.0
- ✓ Persist and reload experiment datasets as parquet files — v1.0
- ✓ Build forecasting features from merchant/product time series data — v1.0
- ✓ Evaluate forecasting outputs with project metrics utilities — v1.0
- ✓ Train PPO agent on perishable inventory Gymnasium environment — v1.0
- ✓ Compute newsvendor optimal order quantities — v1.0
- ✓ Partition merchant-level datasets for federated experiments — v1.0
- ✓ Document ML approach decisions citing 8 academic papers — v1.0
- ✓ Fresh Colab runtime installs dependencies and mounts Drive — v1.0
- ✓ One parameter cell controls entire pipeline workflow — v1.0
- ✓ LightGBM forecast end-to-end with time-based split — v1.0
- ✓ Strict schema validation with fail-fast errors — v1.0
- ✓ Same code path for synthetic and real data — v1.0
- ✓ MAE, RMSE, WMAPE, pinball loss reported in notebook — v1.0
- ✓ PPO vs newsvendor benchmarked with fill_rate, waste_rate, stockout_frequency — v1.0
- ✓ Forecast predictions feed into optimization parameters — v1.0

### Active

(None yet — next milestone will define new requirements)

### Out of Scope

- Dynamic pricing as action variable — all papers confirm coupling, but increases complexity; deferred with price recorded in schema
- E2E forecast-optimize with embedded newsvendor structure — Paper 5 (Liao et al.) shows E2E-PIL outperforms two-stage; deferred to v2
- Dual-agent architecture for pricing + inventory — Paper 3 (Zheng et al.) validates this; deferred until pricing enters scope
- Federated learning training — separate milestone after single-merchant pipeline is stable
- Real-time sensor data integration — irrelevant for small merchants
- Multi-echelon supply chain — single-store focus
- Flexible schema mapping — strict schema first
- Transaction-level aggregation — assumes daily sales table

## Context

- Shipped v1.0: 1,958 LOC Python source, 441 LOC tests, 33 tests passing.
- Tech stack: Python 3.10+, LightGBM, Stable-Baselines3 (PPO), Gymnasium, Pydantic, Hydra, Trackio.
- `src/meshek_ml/forecasting/pipeline.py` is fully implemented — chains validate → features → time-split → train → evaluate.
- `src/meshek_ml/forecasting/schema.py` provides canonical schema validation with SchemaValidationError.
- Notebook (`notebooks/colab_quickstart.ipynb`) has 28 cells covering the full two-stage pipeline.
- `academic/APPROACH.md` documents all method choices with 8 paper citations.
- Next focus: federated learning across merchants, or dynamic pricing integration.

## Constraints

- **Execution environment**: Google Colab first
- **Forecasting model**: LightGBM — confirmed by M5 competition and academic evidence
- **Optimization model**: PPO + newsvendor baseline — validated by multiple papers
- **Architecture**: Two-stage (forecast → optimize) — E2E deferred to v2
- **Data contract**: Strict schema — `date`, `merchant_id`, `product`, `quantity`
- **Academic grounding**: Every method choice cites supporting literature

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LightGBM for demand forecasting | M5 top-5, Paper 4 confirms, MARIOD TFT needs 8x A100s | ✓ Good — 13 tests pass, pipeline works |
| Two-stage pipeline, not E2E | Simpler to debug, matches codebase separation | ✓ Good — forecast feeds optimization via bridge |
| PPO for inventory optimization | Boute et al. 2022, Nomura et al. 2025 <10% gap | ✓ Good — trains in notebook, benchmarks vs newsvendor |
| Newsvendor as analytical baseline | All 8 papers reference it | ✓ Good — critical fractile formula works |
| Dynamic pricing deferred | Too complex for v1, all papers couple it | — Pending v2 |
| Federated learning separate milestone | Needs stable single-merchant pipeline first | — Pending |
| Simulation as training ground | Original brief + MARIOD confirm | ✓ Good — 8 products, Hebrew locale merchants |

---
*Last updated: 2026-03-31 after v1.0 milestone*
