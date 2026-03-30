# Roadmap: meshek-ml

## Overview

This milestone turns the existing research codebase into a reproducible Google Colab pipeline grounded in academic evidence. It starts by documenting ML method choices with paper citations, then builds a LightGBM forecasting pipeline on top of existing utilities, wires the already-functional PPO and newsvendor optimization into the notebook, and finishes by connecting forecast output to optimization input in one end-to-end flow.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Approach & Colab Bootstrap** - Document ML approach decisions from academic evidence and set up the Colab environment.
- [ ] **Phase 2: Forecasting Pipeline** - Implement pipeline.py orchestrator with strict schema validation and wire into Colab.
- [ ] **Phase 3: Optimization Baseline** - Wire existing PPO and newsvendor into the notebook with benchmarking.
- [ ] **Phase 4: Integration & Documentation** - Connect forecast to optimization and document the full pipeline.

## Phase Details

### Phase 1: Approach & Colab Bootstrap
**Goal**: Document which ML methods were chosen and why (citing 8 academic papers), and set up a fresh Colab environment with dependencies and Drive access.
**Depends on**: Nothing (first phase)
**Requirements**: APPR-01, APPR-02, SETUP-01, SETUP-02
**Success Criteria** (what must be TRUE):
  1. An APPROACH.md document exists citing each of the 8 academic papers and mapping them to method decisions (LightGBM, PPO, newsvendor, two-stage architecture, deferred items).
  2. Team member can run the notebook from a fresh Colab runtime and complete dependency installation without manual repo surgery.
  3. Team member can mount or otherwise access Google Drive from the notebook.
**Plans**: 2 plans
Plans:
- [ ] 01-01-PLAN.md — Write APPROACH.md with academic paper citations and method rationale
- [ ] 01-02-PLAN.md — Update Colab notebook with bootstrap cells for dependencies and Drive access
**UI hint**: yes

### Phase 2: Forecasting Pipeline
**Goal**: Implement the missing `pipeline.py` orchestrator that chains existing feature engineering, LightGBM training, and evaluation utilities into one callable pipeline, with strict schema validation and parameter controls.
**Depends on**: Phase 1
**Requirements**: SETUP-03, FORE-01, FORE-02, FORE-03, FORE-04, FORE-05
**Success Criteria** (what must be TRUE):
  1. `pipeline.py` orchestrates: load → validate schema → feature engineer → time-based split → train LightGBM → evaluate.
  2. One parameter cell in the notebook controls source choice, input/output paths, date range, and seed.
  3. Notebook outputs MAE, RMSE, WMAPE, and pinball loss after training.
  4. Real data with wrong schema triggers a clear fail-fast error before training starts.
  5. Synthetic and real data flow through the same pipeline code path after schema validation.
**Plans**: 2 plans
Plans:
- [ ] 02-01-PLAN.md — Schema validation module + pipeline.py orchestrator implementation with tests
- [ ] 02-02-PLAN.md — Notebook parameter cell and forecasting section integration
**UI hint**: yes

### Phase 3: Optimization Baseline
**Goal**: Wire the already-functional PPO agent and newsvendor baseline into the Colab notebook with side-by-side benchmarking metrics.
**Depends on**: Phase 2
**Requirements**: OPT-01, OPT-02, OPT-03
**Success Criteria** (what must be TRUE):
  1. Notebook trains a PPO agent on the PerishableInventoryEnv.
  2. Notebook computes newsvendor baseline orders using the critical fractile formula.
  3. Notebook displays a comparison table: fill_rate, waste_rate, stockout_frequency for PPO vs newsvendor.
**Plans**: TBD
**UI hint**: yes

### Phase 4: Integration & Documentation
**Goal**: Connect LightGBM forecast output as demand input to the optimization layer, and document the full two-stage pipeline with academic justification for team use.
**Depends on**: Phase 3
**Requirements**: Cross-cutting integration
**Success Criteria** (what must be TRUE):
  1. Forecast predictions from LightGBM feed into newsvendor/PPO optimization decisions in one notebook flow.
  2. Team member can run the complete pipeline (forecast → optimize) end-to-end from a fresh Colab session.
  3. Notebook or repository documentation explains the two-stage architecture and why each method was chosen, citing the papers.
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Approach & Colab Bootstrap | 0/2 | Not started | - |
| 2. Forecasting Pipeline | 0/2 | Not started | - |
| 3. Optimization Baseline | 0/TBD | Not started | - |
| 4. Integration & Documentation | 0/TBD | Not started | - |
