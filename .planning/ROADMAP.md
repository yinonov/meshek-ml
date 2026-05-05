# Roadmap: meshek-ml

## Milestones

- ✅ **v1.0 Evidence-Based Colab Pipeline** — Phases 1-4 (shipped 2026-03-31)
- ✅ **v1.1 Merchant Order Advisor** — Phases 5-11 (shipped 2026-04-16)
- 🚧 **v1.2 Honest Demand Contract** — Phases 12-15 (active, started 2026-05-04)

## Phases

<details>
<summary>✅ v1.0 Evidence-Based Colab Pipeline (Phases 1-4) — SHIPPED 2026-03-31</summary>

- [x] Phase 1: Approach & Colab Bootstrap (2/2 plans) — completed 2026-03-31
- [x] Phase 2: Forecasting Pipeline (2/2 plans) — completed 2026-03-31
- [x] Phase 3: Optimization Baseline (1/1 plans) — completed 2026-03-31
- [x] Phase 4: Integration & Documentation (1/1 plans) — completed 2026-03-31

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.1 Merchant Order Advisor (Phases 5-11) — SHIPPED 2026-04-16</summary>

- [x] Phase 5: Data Foundation (2/2 plans) — per-merchant SQLite storage
- [x] Phase 6: Recommendation Engine (4/4 plans) — three-tier cold-start logic + LightGBM
- [x] Phase 7: Hebrew Input Parsing (5/5 plans) — dictionary-based Hebrew product/quantity parsing
- [x] Phase 8: API Surface & Deployment (6/6 plans) — FastAPI endpoints + Docker container
- [x] Phase 8.1: Cloud Run Deployment (5/5 plans) — GCS FUSE mounts + IAM security
- [x] Phase 9: Model Bundle Pipeline (4/4 plans) — reproducible training + GCS publishing
- [x] Phase 10: Fix Cloud Run Smoke Test (1/1 plans) — corrected test paths and assertions
- [x] Phase 11: Milestone Documentation Cleanup (1/1 plans) — checkboxes, frontmatter, env skew docs

Full details: `.planning/milestones/v1.1-ROADMAP.md`

</details>

### v1.2 Honest Demand Contract (Phases 12-15) — ACTIVE

- [ ] **Phase 12: `12-wire-contract`** — Freeze the new `/recommend` shape (predicted_demand + band + per-line tier + signals); cross-repo sync point with meshek v0.8.
- [ ] **Phase 13: `13-exogenous-features`** — Add Shabbat / Israeli holiday / Ramadan / Eid / weather columns to the feature pipeline.
- [ ] **Phase 14: `14-honest-tier-semantics`** — Make Tier 1/2/3 emit a uniform shape: confidence, demand band, signals.
- [ ] **Phase 15: `15-tier-horizon-extension`** — Re-tune Tier 2 shrinkage anchor so Tier 2 stays useful past ~14 days while Tier 3 sits dormant.

## Phase Details

### Phase 12: `12-wire-contract`

**Goal**: Land the new `/recommend` response contract — point estimate, demand band, per-line `reasoning_tier`, per-line `confidence_score`, and `signals[]` — and remove the order-quantity field. This phase is the cross-repo synchronization point with meshek v0.8: `@meshek/ml-client` types must update via a coordinated PR before merge.

**Depends on**: Nothing in v1.2. Foundation phase.

**Blocks**: Phases 13, 14, 15 (sequencing is soft — see notes below). Cross-repo: meshek v0.8 M-P2 and M-P3 are blocked until this phase merges.

**Requirements**: WIRE-01, WIRE-02, WIRE-03, WIRE-04, WIRE-05, WIRE-06, WIRE-07

**Success Criteria** (what must be TRUE):
  1. A `POST /recommend` response carries `predicted_demand`, `demand_lower`, `demand_upper`, per-line `reasoning_tier` (enum), per-line `confidence_score`, and a `signals[]` array on every recommendation line — verifiable from a live response and the OpenAPI schema.
  2. The legacy `quantity` field no longer appears in the public response or the OpenAPI schema; the newsvendor order-qty layer is either removed or fully internal.
  3. `signals[]` units (raw demand units vs normalized) are decided and documented in this phase, and `name` / `copy_key` are stable enums consumable by meshek for i18n.
  4. `@meshek/ml-client` TypeScript types in the meshek repo are updated via a coordinated PR that lands before MM-P1 is merged here — verified by the meshek repo consuming the new shape without runtime errors.
  5. Existing `/recommend` integration tests are updated and pass against the new shape; no test still asserts a top-level `quantity`.

**Plans**: 3 plans
  - [ ] 12-01-schema-and-tiers-PLAN.md — Rewrite Pydantic schema + all three tier constructors; remove newsvendor from response path; bump SERVICE_VERSION; migrate unit tests inline
  - [ ] 12-02-service-and-openapi-PLAN.md — Migrate HTTP integration tests; add OpenAPI contract test + Tier-1 full-key-set contract test; full pytest suite gate
  - [ ] 12-03-cross-repo-coordination-PLAN.md — Cross-repo handoff doc + manual gate for the meshek-side TypeScript PR pair (WIRE-07)

**Cross-phase notes**:
  - **Wire freeze**: This is the only phase in v1.2 that is on a hard sequencing constraint. It MUST land first because it freezes the contract that meshek v0.8 M-P2 and M-P3 consume.
  - **Cross-repo PR**: The `@meshek/ml-client` type update lives in the meshek repo. Coordinate landing order: open the meshek-side PR, merge it after the meshek-ml PR is approved, then merge meshek-ml. Document the commit/PR pair in the phase summary.
  - **Decisions LOCKED** (per handoff doc — do not re-litigate): no Tier 3 retraining, no real-data benchmark eval, no stock awareness, no per-line dot rendering (UI work owned by meshek).

### Phase 13: `13-exogenous-features`

**Goal**: Extend `forecasting/features.py` with the exogenous feature schema that future real merchant data will populate — Shabbat, Friday-pre-Shabbat, Israeli holiday name + proximity, Ramadan, Eid, and optional weather columns. Calendar-derivable features ship live; weather columns ship as nullable schema only.

**Depends on**: Phase 12 (wire contract). Soft dependency — work can be drafted in parallel, but merging requires the new contract to be in place.

**Requirements**: FEAT-01, FEAT-02, FEAT-03, FEAT-04, FEAT-05, FEAT-06, FEAT-07, FEAT-08

**Success Criteria** (what must be TRUE):
  1. `forecasting/features.py` emits all eight new feature columns: `is_shabbat`, `is_friday_pre_shabbat`, `israeli_holiday`, `israeli_holiday_proximity`, `is_ramadan`, `is_eid`, `temperature_c`, `precipitation_mm`.
  2. Israeli holiday features wire from the existing `simulation/calendar.py` — no second source of holiday truth is introduced.
  3. A Hijri-calendar dependency (one of `convertdate` / `pyluach` / `hijri-converter`) is selected, justified, installed, and pinned in `pyproject.toml`; the selection is documented in the phase summary.
  4. The feature pipeline tolerates null `temperature_c` / `precipitation_mm` end-to-end — synthetic data flows through without populating weather, and tests cover the null path.
  5. Tier 2 pooled priors consume the universal Shabbat day-of-week pattern (no per-merchant history required), verified by a Tier 2 unit/integration test.

**Plans**: TBD

**Cross-phase notes**:
  - **Parallelizable**: After Phase 12 lands, this phase has no hard inter-dependency with Phase 14 or Phase 15. It can run in parallel.
  - **No Tier 3 retraining**: Adding the columns is in scope; retraining the LightGBM bundle on these features is explicitly OUT of scope (locked decision — Tier 3 stays dormant pending real merchant data).
  - **File surface**: `forecasting/features.py`, `simulation/calendar.py` (read-only consumer), `pyproject.toml` (dep pin), feature schema tests.

### Phase 14: `14-honest-tier-semantics`

**Goal**: Make Tier 1 (`category_default`), Tier 2 (`pooled_prior`), and Tier 3 (`ml_forecast`) emit a uniform output shape — `confidence_score`, `demand_lower` / `demand_upper`, and `signals[]` — so meshek's UI can render the same surface regardless of which tier produced a line.

**Depends on**: Phase 12 (wire contract). Soft sequencing with Phase 15 — see notes.

**Requirements**: TIER-01, TIER-02, TIER-03, TIER-04, TIER-05

**Success Criteria** (what must be TRUE):
  1. Every recommendation line — regardless of tier — carries a numeric `confidence_score`, a `demand_lower` / `demand_upper` band, and at least one entry in `signals[]`. Verifiable from `/recommend` integration tests that exercise all three tiers.
  2. Tier 1 emits a fixed `confidence_score` of `0.2`; Tier 2 linearly interpolates `0.3 → 0.6` with merchant horizon (consistent with the shrinkage anchor work in Phase 15); Tier 3 derives confidence from residual std as today.
  3. Tier 1 / Tier 2 demand bands are derived from pooled-prior variance; Tier 3's band is derived from residual std. Bands are non-degenerate (`demand_lower < predicted_demand < demand_upper`) and tested.
  4. Every tier emits at minimum a tier-name signal `{ name: <tier_name>, contribution: 1.0, copy_key: "signal.tier_<n>_default" }` in `signals[]`, so the meshek UI shape is uniform.

**Plans**: TBD

**Cross-phase notes**:
  - **Parallelizable** with Phases 13 and 15 after Phase 12 lands.
  - **Conflict surface with Phase 15**: Both phases touch `recommendation/tiers.py`. Plan-phase scheduling should sequence them when their plans overlap on Tier 2 (TIER-02 here interlocks with HORIZON-01/HORIZON-02 in Phase 15). If both phases are in flight simultaneously, do Phase 15 first or rebase Phase 14 onto Phase 15 to avoid merge churn.
  - **Tier 3 is NOT retrained** here; only its output is wrapped in the uniform shape.

### Phase 15: `15-tier-horizon-extension`

**Goal**: Re-tune the Tier 2 shrinkage anchor (`n / (n + 14)`) upward so Tier 2 stays useful past ~14 days of merchant history, since Tier 3 sits dormant longer than the original design assumed. Add a graceful-degradation invariant so Tier 2 confidence approaches but never reaches Tier 3's range.

**Depends on**: Phase 12 (wire contract). Soft sequencing with Phase 14 — see notes.

**Requirements**: HORIZON-01, HORIZON-02, HORIZON-03

**Success Criteria** (what must be TRUE):
  1. The new shrinkage anchor is empirically chosen via simulation (not hand-picked); the simulation procedure and the resulting anchor value are recorded in the phase summary.
  2. The graceful-degradation invariant holds: Tier 2's `confidence_score` curve approaches but never exceeds Tier 3's confidence range — verified by a unit test that asserts the invariant across the full horizon.
  3. Existing Tier 2 shrinkage and confidence-curve tests pass with the new anchor (updated as needed); new tests cover the graceful-degradation invariant.
  4. The hardcoded anchor `14` is replaced by a single named constant in `recommendation/tiers.py` (or a config module), documented with the simulation rationale in a comment or docstring.

**Plans**: TBD

**Cross-phase notes**:
  - **Parallelizable** with Phases 13 and 14 after Phase 12 lands.
  - **Conflict surface with Phase 14**: Both phases touch `recommendation/tiers.py`, specifically Tier 2. HORIZON-01/HORIZON-02 (this phase) and TIER-02 (Phase 14) both shape the Tier 2 confidence curve. If both phases run concurrently, recommend doing Phase 15 first so Phase 14 can wire its TIER-02 confidence emission against the already-re-tuned anchor.
  - **Decisions LOCKED**: Tier 3 retraining and benchmark eval remain OUT of scope — this phase tunes Tier 2 only.

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Approach & Colab Bootstrap | v1.0 | 2/2 | Complete | 2026-03-31 |
| 2. Forecasting Pipeline | v1.0 | 2/2 | Complete | 2026-03-31 |
| 3. Optimization Baseline | v1.0 | 1/1 | Complete | 2026-03-31 |
| 4. Integration & Documentation | v1.0 | 1/1 | Complete | 2026-03-31 |
| 5. Data Foundation | v1.1 | 2/2 | Complete | 2026-04-13 |
| 6. Recommendation Engine | v1.1 | 4/4 | Complete | 2026-04-14 |
| 7. Hebrew Input Parsing | v1.1 | 5/5 | Complete | 2026-04-14 |
| 8. API Surface & Deployment | v1.1 | 6/6 | Complete | 2026-04-14 |
| 8.1. Cloud Run Deployment | v1.1 | 5/5 | Complete | 2026-04-15 |
| 9. Model Bundle Pipeline | v1.1 | 4/4 | Complete | 2026-04-15 |
| 10. Fix Cloud Run Smoke Test | v1.1 | 1/1 | Complete | 2026-04-16 |
| 11. Milestone Documentation Cleanup | v1.1 | 1/1 | Complete | 2026-04-16 |
| 12. Wire Contract | v1.2 | 0/3 | Planning | — |
| 13. Exogenous Features | v1.2 | 0/? | Not started | — |
| 14. Honest Tier Semantics | v1.2 | 0/? | Not started | — |
| 15. Tier Horizon Extension | v1.2 | 0/? | Not started | — |
