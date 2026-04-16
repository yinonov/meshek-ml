# Milestones

## v1.1 Merchant Order Advisor (Shipped: 2026-04-16)

**Phases completed:** 8 phases, 28 plans | **Timeline:** 4 days | **142 commits, 4,458 LOC Python**

**Key accomplishments:**

- Per-merchant SQLite data foundation with isolated storage, WAL journaling, migration ladder, and defense-in-depth path traversal security (21 parametrized fuzz cases)
- Three-tier recommendation engine: Tier 1 category defaults, Tier 2 cross-merchant pooled priors, Tier 3 LightGBM ML forecasting with confidence scoring
- Hebrew free-text sales parsing with canonical product mapping (singular/plural, misspellings) and quantity extraction
- Full FastAPI service with 4 endpoints (/health, /merchants, /sales, /recommend), degraded-start support, and Docker container
- Production Cloud Run deployment with dual GCS FUSE mounts (merchants + models), IAM-secured access, and copy-pasteable operator runbook
- Reproducible LightGBM model bundle pipeline with synthetic seed data, GCS publishing, and live Tier 3 E2E verification on Cloud Run

---

## v1.0 Evidence-Based Colab Pipeline (Shipped: 2026-03-31)

**Phases completed:** 4 phases, 4 plans, 9 tasks

**Key accomplishments:**

- ML approach document mapping LightGBM, PPO, newsvendor, and two-stage architecture to 8 academic papers with contrary evidence and deferral rationale
- Colab quickstart notebook with pip install from pyproject.toml extras, GPU detection with memory reporting, and Google Drive mount with local fallback
- Status:
- Status:
- Status:
- Status:

---
