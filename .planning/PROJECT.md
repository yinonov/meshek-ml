# meshek-ml

## What This Is

meshek-ml is a research codebase for forecasting demand and optimizing inventory for small produce merchants (Israeli greengrocers), combining LightGBM demand forecasting with PPO-based inventory optimization. The project validates its ML method choices against academic literature on perishable goods management and trains entirely on synthetic data first before real sales data.

## Core Value

Deliver one reproducible Colab workflow that trains a LightGBM forecast and benchmarks a newsvendor/PPO optimization — grounded in academic evidence for each method choice.

## Requirements

### Validated

- ✓ Generate synthetic merchant-product demand datasets with seasonality and spoilage-aware patterns — `src/meshek_ml/simulation/`
- ✓ Persist and reload experiment datasets as parquet files — `src/meshek_ml/common/io.py`
- ✓ Build forecasting features from merchant/product time series data — `src/meshek_ml/forecasting/features.py`
- ✓ Evaluate forecasting outputs with project metrics utilities — `src/meshek_ml/forecasting/evaluation.py`
- ✓ Train PPO agent on perishable inventory Gymnasium environment — `src/meshek_ml/optimization/ppo_agent.py`
- ✓ Compute newsvendor optimal order quantities — `src/meshek_ml/optimization/newsvendor.py`
- ✓ Partition merchant-level datasets for federated experiments — `src/meshek_ml/federated/partitioning.py`

### Active

- [ ] Document ML approach decisions citing academic papers that support each method choice
- [ ] Run a fresh Colab notebook setup successfully for the full pipeline workflow
- [ ] Generate synthetic training data inside Colab and train one LightGBM forecasting model end to end
- [ ] Load real daily sales data with a strict required schema: `date`, `merchant_id`, `product`, `quantity`
- [ ] Reuse the same forecasting path for synthetic and real data with minimal notebook branching
- [ ] Report evaluation metrics clearly inside the notebook output for team review
- [ ] Train a PPO agent and run a newsvendor baseline from the Colab notebook
- [ ] Benchmark PPO vs newsvendor with fill rate, waste rate, and stockout metrics
- [ ] Connect forecast output to optimization input in one notebook flow

### Out of Scope

- Dynamic pricing as action variable — all papers confirm coupling, but increases complexity beyond v1; deferred to v2 with price recorded in schema for forward compatibility
- E2E forecast-optimize with embedded newsvendor structure — Paper 5 (Liao et al.) shows E2E-PIL outperforms two-stage, but two-stage is simpler to debug and matches current codebase separation
- Dual-agent architecture for pricing + inventory — Paper 3 (Zheng et al.) validates this, deferred until pricing enters scope
- Federated learning training — separate milestone after single-merchant pipeline is stable
- Real-time sensor data integration — MARIOD's IoT scope is irrelevant for small merchants
- Multi-echelon supply chain — single-store focus for boutique greengrocers
- Flexible schema mapping for arbitrary source columns — strict schema first
- Transaction-level aggregation — v1 assumes daily sales table is already prepared

## Context

- The repository is a brownfield Python ML workbench with functional simulation, forecasting feature utilities, optimization components (PPO + newsvendor), and federated partitioning.
- `src/meshek_ml/forecasting/pipeline.py` is a stub — the main implementation gap for forecasting.
- `scripts/run_forecast.py` and `scripts/run_optimization.py` are stubs.
- Existing Colab notebook (`notebooks/colab_quickstart.ipynb`) demonstrates simulation → PPO training → newsvendor benchmarking but needs restructuring for the evidence-based pipeline.
- 8 academic papers in `academic/` inform method choices across forecasting, optimization, and federated learning.
- The primary audience is the internal team and the ML course professor.

## Constraints

- **Execution environment**: Google Colab first — the training path must work in a fresh hosted notebook session
- **Forecasting model**: LightGBM first — M5 competition winner, confirmed by academic evidence
- **Optimization model**: PPO + newsvendor baseline — validated by Boute et al. 2022 roadmap and multiple papers
- **Architecture**: Two-stage (forecast → optimize) — simpler to debug, matches existing code separation; E2E deferred to v2
- **Data contract**: Strict schema — fail fast unless real data exposes `date`, `merchant_id`, `product`, `quantity`
- **Workflow shape**: Synthetic first, then real data — simulation as training ground, confirmed by all papers
- **Academic grounding**: Every method choice must cite supporting literature

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LightGBM for demand forecasting | M5 competition top-5 all used LightGBM; Paper 4 (Lee & Wong) confirms tree models outperform TS baselines; MARIOD's TFT needs 8x A100s | — Pending |
| Two-stage pipeline (forecast → optimize), not E2E | Paper 5 (Liao et al.) shows E2E-PIL is better, but two-stage is simpler to debug and matches codebase separation; E2E deferred to v2 | — Pending |
| PPO for inventory optimization | Boute et al. 2022 roadmap; Nomura et al. 2025 <10% gap vs exact DP; MARIOD uses hierarchical PPO variant | — Pending |
| Newsvendor as analytical baseline | All 8 papers reference it; Paper 5 embeds it as structural prior; natural bridge between forecast and order decision | — Pending |
| Dynamic pricing deferred, price recorded in schema | Every paper couples pricing with inventory; Zheng et al. prove joint profit not jointly concave; too complex for v1 | — Pending |
| Federated learning is a separate milestone | FL for perishable inventory across heterogeneous small merchants is the novel contribution; needs stable single-merchant pipeline first | — Pending |
| Simulation is the training ground | Original brief + MARIOD confirm; custom numpy/pandas approach appropriate for fixed-step daily simulation | — Pending |

---
*Last updated: 2026-03-30 after milestone revision with academic evidence*
