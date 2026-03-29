# Requirements: meshek-ml

**Defined:** 2026-03-24
**Core Value:** Make forecasting training reproducible and easy to run in Colab so the team can move from local research code to repeatable model experiments on both synthetic and real data.

## v1 Requirements

### Colab Setup

- [ ] **SETUP-01**: Team member can start from a fresh Google Colab runtime and install the forecasting workflow dependencies successfully
- [ ] **SETUP-02**: Team member can mount or access Google Drive from the notebook to read real data inputs and write workflow outputs
- [ ] **SETUP-03**: Team member can control the notebook run from one parameter cell that defines source selection, paths, dates, and seed settings

### Data Contract

- [ ] **DATA-01**: User can generate a synthetic daily sales-style dataset inside the Colab workflow for forecasting training
- [ ] **DATA-02**: User can load a real daily sales table only when it contains the required columns `date`, `merchant_id`, `product`, and `quantity`
- [ ] **DATA-03**: Workflow fails fast with clear messages when required columns are missing, malformed, or unusable for training
- [ ] **DATA-04**: Workflow shows a schema audit summary before training, including row counts, date span, null checks, and merchant/product cardinality
- [ ] **DATA-05**: Workflow normalizes synthetic and real data into one canonical forecasting table before feature engineering
- [ ] **DATA-06**: Workflow documents the required real-data schema and assumptions directly in the notebook or repository guidance

### Forecast Training

- [ ] **FORE-01**: User can run one shared forecasting pipeline for both synthetic and real data sources without maintaining separate notebook implementations
- [ ] **FORE-02**: Workflow applies a time-based train/validation split rather than a random split
- [ ] **FORE-03**: User can train one LightGBM forecasting model end to end from the Colab workflow
- [ ] **FORE-04**: Workflow reports forecasting evaluation metrics clearly in notebook output for team review

## v2 Requirements

### Forecast Workflow Extensions

- **FLOW-01**: Workflow can save a reusable trained model artifact to a durable output location
- **FLOW-02**: Workflow can export a sample of predictions for offline inspection
- **FLOW-03**: Workflow can save a lightweight run manifest with parameters, split details, and metrics
- **FLOW-04**: Workflow can compare LightGBM against a naive baseline forecast
- **FLOW-05**: Workflow can support additional forecasting models beyond LightGBM

### Data Flexibility

- **FLEX-01**: Workflow can map arbitrary source column names into the canonical schema
- **FLEX-02**: Workflow can aggregate transaction-level data into daily merchant-product demand

## Out of Scope

| Feature | Reason |
|---------|--------|
| Federated learning training in Colab | Separate milestone and not required for the first forecasting workflow |
| Inventory optimization or PPO training in this notebook | Different runtime, model loop, and success criteria |
| Flexible schema mapping in v1 | Conflicts with the strict-schema requirement and would slow first delivery |
| Transaction-level aggregation in v1 | Assumes a prepared daily sales table already exists |
| Multi-model experimentation framework | Would widen scope before one canonical forecasting path exists |
| Heavy widget-based notebook UI | Adds maintenance complexity without helping the core workflow |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SETUP-01 | Phase 1 | Pending |
| SETUP-02 | Phase 1 | Pending |
| SETUP-03 | Phase 2 | Pending |
| DATA-01 | Phase 2 | Pending |
| DATA-02 | Phase 3 | Pending |
| DATA-03 | Phase 3 | Pending |
| DATA-04 | Phase 3 | Pending |
| DATA-05 | Phase 3 | Pending |
| DATA-06 | Phase 3 | Pending |
| FORE-01 | Phase 3 | Pending |
| FORE-02 | Phase 4 | Pending |
| FORE-03 | Phase 4 | Pending |
| FORE-04 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-03-29 after roadmap creation*
