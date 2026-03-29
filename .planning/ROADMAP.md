# Roadmap: meshek-ml

## Overview

This brownfield milestone turns the existing research codebase into a practical Google Colab-first forecasting workflow. The roadmap starts by making fresh-session notebook setup reliable, then establishes a controllable synthetic baseline, hardens one strict shared data contract for synthetic and real daily sales inputs, and finishes with a single LightGBM training and evaluation path that the team can run end to end.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Colab Bootstrap** - Make the forecasting workflow start cleanly in a fresh Colab session with storage access.
- [ ] **Phase 2: Controlled Synthetic Baseline** - Give the notebook one control surface and a reproducible synthetic data run path.
- [ ] **Phase 3: Shared Data Contract** - Normalize synthetic and strict-schema real data into one canonical forecasting table with fail-fast validation.
- [ ] **Phase 4: LightGBM Forecast Training** - Train and review one time-aware LightGBM forecast from the shared pipeline inside Colab.

## Phase Details

### Phase 1: Colab Bootstrap
**Goal**: Team members can open a fresh Google Colab runtime, install the required forecasting dependencies, and access Drive-backed inputs and outputs.
**Depends on**: Nothing (first phase)
**Requirements**: SETUP-01, SETUP-02
**Success Criteria** (what must be TRUE):
  1. Team member can run the notebook from a fresh Colab runtime and complete dependency installation without manual repo surgery.
  2. Team member can mount or otherwise access Google Drive from the notebook to read real-data inputs.
  3. Team member can write workflow outputs from the notebook to a Colab-accessible durable location.
**Plans**: TBD
**UI hint**: yes

### Phase 2: Controlled Synthetic Baseline
**Goal**: Team members can drive the notebook from one parameter cell and generate reproducible synthetic daily sales-style data for the forecasting workflow.
**Depends on**: Phase 1
**Requirements**: SETUP-03, DATA-01
**Success Criteria** (what must be TRUE):
  1. Team member can set source choice, input and output paths, date controls, and seed settings from one notebook parameter cell.
  2. Team member can generate a synthetic daily sales-style dataset entirely inside Colab without preparing external files.
  3. Re-running the synthetic workflow with the same control values produces the same staged synthetic dataset behavior.
**Plans**: TBD
**UI hint**: yes

### Phase 3: Shared Data Contract
**Goal**: Synthetic and real daily sales data flow through one package-first preparation path that enforces the strict v1 schema and exposes a pre-training audit.
**Depends on**: Phase 2
**Requirements**: DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, FORE-01
**Success Criteria** (what must be TRUE):
  1. User can load a real dataset only when it provides `date`, `merchant_id`, `product`, and `quantity` in a usable training form.
  2. Workflow stops before training with clear messages when required columns are missing, malformed, or otherwise invalid.
  3. Workflow shows a schema audit summary before training with row counts, date span, null checks, and merchant and product cardinality.
  4. Synthetic and real sources are normalized into one canonical forecasting table and proceed through the same package-level preparation path.
  5. Team members can find the strict real-data schema rules and assumptions directly in notebook or repository guidance.
**Plans**: TBD
**UI hint**: yes

### Phase 4: LightGBM Forecast Training
**Goal**: Team members can train one LightGBM forecasting model end to end in Colab using the shared pipeline and review time-aware validation metrics in notebook output.
**Depends on**: Phase 3
**Requirements**: FORE-02, FORE-03, FORE-04
**Success Criteria** (what must be TRUE):
  1. User can run one shared forecasting pipeline from the notebook through feature generation, split, training, and evaluation.
  2. Workflow uses a time-based train and validation split rather than a random split.
  3. User can train one LightGBM model end to end on the staged forecasting dataset from Colab.
  4. Notebook output reports evaluation metrics clearly enough for team review of model behavior.
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Colab Bootstrap | 0/TBD | Not started | - |
| 2. Controlled Synthetic Baseline | 0/TBD | Not started | - |
| 3. Shared Data Contract | 0/TBD | Not started | - |
| 4. LightGBM Forecast Training | 0/TBD | Not started | - |
