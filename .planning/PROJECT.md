# meshek-ml

## What This Is

meshek-ml is an ML inference service for forecasting demand and optimizing inventory for small produce merchants (Israeli greengrocers). It exposes a FastAPI backend with per-merchant SQLite storage, a three-tier cold-start recommendation engine (category defaults → pooled priors → LightGBM ML forecasting), Hebrew free-text sales parsing, and a reproducible model bundle pipeline. The service runs on Google Cloud Run with GCS FUSE persistence. It validates its ML method choices against 8 academic papers on perishable goods management.

## Core Value

Answer "how much should I order tomorrow?" for Israeli greengrocers — wrapping proven ML forecasting and optimization behind a zero-friction WhatsApp interface.

## Current State

**Shipped:** v1.1 Merchant Order Advisor (2026-04-16)

meshek-ml is a **backend ML service only**. The merchant-facing app (dashboard, WhatsApp integration, order management) lives in the meshek repo. meshek-ml exposes a FastAPI inference API, and meshek's Fastify backend calls it — same pattern as meshek's existing `llm-engine` service.

**Delivered in v1.1:**
- FastAPI service with 4 endpoints: `/health`, `/merchants`, `/sales`, `/recommend`
- Three-tier recommendation engine: category defaults → pooled priors → LightGBM ML forecasting
- Hebrew free-text sales parsing (dictionary-based, ~30 products)
- Per-merchant SQLite storage with GCS FUSE persistence on Cloud Run
- Reproducible LightGBM model bundle pipeline with GCS publishing
- Production deployment on Google Cloud Run in `meshek-prod` project

**Owned by meshek app (NOT in scope here):**
- WhatsApp Business API integration (already implemented in meshek)
- Proactive daily order recommendation delivery via WhatsApp
- Merchant dashboard display of recommendations
- Order management and catalog

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

- ✓ Per-merchant SQLite storage with filesystem isolation — v1.1
- ✓ Merchant profile CRUD with zero configuration — v1.1
- ✓ Three-tier recommendation engine (cold-start → pooled → ML) — v1.1
- ✓ Confidence score and reasoning tier in every recommendation — v1.1
- ✓ Hebrew product name mapping (singular/plural, misspellings) — v1.1
- ✓ Hebrew quantity extraction from free text — v1.1
- ✓ FastAPI endpoints: /health, /merchants, /sales, /recommend — v1.1
- ✓ Docker container deployment — v1.1
- ✓ Cloud Run deployment with GCS FUSE persistence — v1.1
- ✓ LightGBM model loads at startup via lifespan — v1.1
- ✓ Reproducible model bundle training + GCS publishing — v1.1

### Active

(No active requirements — define in next milestone via `/gsd-new-milestone`)

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

- Shipped v1.1: 4,458 LOC Python, 120 files, 142 commits across 8 phases in 4 days.
- Tech stack: Python 3.12/3.13, FastAPI, LightGBM, SQLite, Pydantic v2, Docker, Cloud Run, GCS FUSE.
- Service live on Cloud Run in `meshek-prod` project with dual GCS FUSE mounts (merchants + models).
- 17/17 requirements verified across 3 independent sources.
- `academic/APPROACH.md` documents all method choices with 8 paper citations.
- Target users: low-tech Israeli greengrocers (ירקנים) who order on gut feeling at 2-3 AM wholesale market runs.
- WhatsApp is their primary business tool; zero appetite for apps, dashboards, or configuration.
- Merchant waste is 10-25% of inventory; even 3-5% reduction = meaningful income improvement.
- No competing ML-based ordering tool exists for this segment (Afresh/RELEX target chains).

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
| Per-merchant SQLite (not shared DB) | Filesystem isolation simplifies multi-tenancy, matches GCS FUSE mount | ✓ Good — zero-config merchant onboarding |
| Three-tier cold-start | Category defaults → pooled priors → ML forecast | ✓ Good — graceful degradation for new merchants |
| Dictionary-based Hebrew parsing | Faster, cheaper, deterministic for ~30 products vs LLM | ✓ Good — 56 parser tests pass |
| FastAPI with degraded-start | Service boots even without model, /health returns 503 | ✓ Good — resilient deployment |
| Cloud Run + GCS FUSE | Native GCS integration, scale-to-zero, simple deploy | ✓ Good — live and serving |
| SQLite journal_mode=DELETE on FUSE | WAL incompatible with GCS FUSE | ✓ Good — avoids corruption |

---
## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-16 after v1.1 milestone complete*
