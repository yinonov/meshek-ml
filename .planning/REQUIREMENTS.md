# Requirements: meshek-ml — Milestone v1.2 Honest Demand Contract

**Defined:** 2026-05-04
**Core Value:** Answer "how much should I order tomorrow?" for Israeli greengrocers — wrapping proven ML forecasting and optimization behind a zero-friction WhatsApp interface.

**Milestone goal:** Reframe the `/recommend` response to honestly reflect what the system knows (drop order qty, expose demand band + per-line tier + signals), and prepare the feature pipeline so future real merchant data — Israeli holidays, Ramadan, weather, Shabbat — can flow through.

## v1.2 Requirements

Requirements for this milestone. Each maps to exactly one roadmap phase.

### Wire Contract (MM-P1)

- [x] **WIRE-01**: `/recommend` response replaces top-level `recommendations[].quantity` with `predicted_demand`, `demand_lower`, and `demand_upper` (point estimate + band) per line.
- [x] **WIRE-02**: Each recommendation line carries `reasoning_tier` as a stable enum: `"category_default"` | `"pooled_prior"` | `"ml_forecast"` (per-line, not response-level).
- [x] **WIRE-03**: Each recommendation line carries `confidence_score` in `[0, 1]` (per-line, not response-level).
- [x] **WIRE-04**: Each recommendation line carries `signals[]` — array of `{ name: string, contribution: number, copy_key: string }` where `name` is a stable enum, `contribution` is signed (units decided in MM-P1: demand units OR normalized), and `copy_key` is a stable i18n key owned by meshek.
- [x] **WIRE-05**: The newsvendor order-qty layer is removed from the public response. If retained anywhere, it is an internal computation no longer exposed.
- [x] **WIRE-06**: `service/schemas.py` `RecommendationResponse` Pydantic model and OpenAPI documentation reflect the new shape; legacy `quantity` field is gone.
- [ ] **WIRE-07**: `@meshek/ml-client` TypeScript types in the meshek repo are updated via a coordinated PR before MM-P1 is merged here (cross-repo wire freeze).

### Exogenous Feature Schema (MM-P2)

- [ ] **FEAT-01**: `is_shabbat` boolean feature wired into `forecasting/features.py` (day-of-week derivable, universal).
- [ ] **FEAT-02**: `is_friday_pre_shabbat` boolean feature (day-of-week derivable, universal).
- [ ] **FEAT-03**: `israeli_holiday` categorical feature (holiday name or `"none"`) wired from `simulation/calendar.py`.
- [ ] **FEAT-04**: `israeli_holiday_proximity` signed-int feature (days to nearest holiday).
- [ ] **FEAT-05**: `is_ramadan` boolean feature backed by a Hijri-calendar dependency (`convertdate` / `pyluach` / `hijri-converter` — choice locked in this phase).
- [ ] **FEAT-06**: `is_eid` boolean feature backed by the same Hijri-calendar dependency.
- [ ] **FEAT-07**: `temperature_c` and `precipitation_mm` optional float columns added to the feature schema; pipeline tolerates nulls so weather can stay empty until real data arrives.
- [ ] **FEAT-08**: Tier 2 pooled priors use the universal Shabbat day-of-week pattern (no per-merchant history required).

### Honest Tier Semantics (MM-P3)

- [ ] **TIER-01**: Tier 1 (`category_default`) emits a fixed `confidence_score` of `0.2` per recommendation line.
- [ ] **TIER-02**: Tier 2 (`pooled_prior`) emits `confidence_score` that linearly interpolates `0.3 → 0.6` with merchant horizon (consistent with the existing shrinkage anchor in MM-P4 work).
- [ ] **TIER-03**: Tier 3 (`ml_forecast`) emits a residual-std-derived `confidence_score` per line.
- [ ] **TIER-04**: All three tiers emit `demand_lower` / `demand_upper` bands — Tier 1/2 derive the band from pooled-prior variance; Tier 3 derives it from residual std.
- [ ] **TIER-05**: All three tiers emit `signals[]` with at minimum a tier-name signal `{ name: <tier_name>, contribution: 1.0, copy_key: "signal.tier_<n>_default" }` so meshek's UI surface is uniform across tiers.

### Tier 1/2 Horizon Extension (MM-P4)

- [ ] **HORIZON-01**: Increase the Tier 2 shrinkage anchor beyond `n / (n + 14)` so Tier 2 stays useful for longer than ~14 days of merchant history; new value is re-tuned via simulation.
- [ ] **HORIZON-02**: Add a graceful degradation path so Tier 2 confidence approaches but never reaches Tier 3's range (Tier 2 stays subordinate by construction).
- [ ] **HORIZON-03**: Update Tier 2 tests (existing shrinkage and confidence-curve tests) to cover the re-tuned anchor and the graceful-degradation invariant.

## Future Requirements

Deferred to v1.3+; tracked but not in this milestone's roadmap.

### Modeling

- **MODEL-01**: Adopt a real-data benchmark dataset (M5, Favorita, or Rossmann) for Tier 3 evaluation.
- **MODEL-02**: Tier 3 retraining loop driven by `recommendation_feedback` writes.
- **MODEL-03**: Eval Tier 3 against published baselines on the chosen dataset.

### Stock Awareness

- **STOCK-01**: Optional on-hand-inventory input for `/recommend` to bias demand → order-qty translation when merchant data exists.

## Out of Scope

Explicitly excluded for v1.2. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real-dataset adoption (M5 / Favorita / Rossmann) | Decision locked in handoff: no modeling overhaul this milestone; Tier 3 stays dormant pending real merchant data from pilot outreach. |
| Tier 3 retraining loop driven by `recommendation_feedback` | Same — no Tier 3 retraining work this milestone. |
| Evaluating Tier 3 against published baselines | Same — no benchmark eval this milestone. |
| Per-line `reasoning_tier` rendered as separate dots in dashboard | meshek-side concern; the wire change in MM-P1 enables it but UI work happens in meshek v0.8 M-P2/M-P3. |
| Stock awareness / on-hand inventory in the `/recommend` request | Demand band sidesteps the need for it; merchants have no reliable stock signal yet. |
| Dynamic pricing as action variable | Already deferred (PROJECT.md Out of Scope); coupling validated by literature but increases complexity. |
| Better-trained Tier 3 model (real-data training pipeline) | Tier 3 is dormant until pilot data exists — pursued as a parallel non-engineering workstream, not in scope here. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| WIRE-01 | Phase 12 | Complete |
| WIRE-02 | Phase 12 | Complete |
| WIRE-03 | Phase 12 | Complete |
| WIRE-04 | Phase 12 | Complete |
| WIRE-05 | Phase 12 | Complete |
| WIRE-06 | Phase 12 | Complete |
| WIRE-07 | Phase 12 | Pending |
| FEAT-01 | Phase 13 | Pending |
| FEAT-02 | Phase 13 | Pending |
| FEAT-03 | Phase 13 | Pending |
| FEAT-04 | Phase 13 | Pending |
| FEAT-05 | Phase 13 | Pending |
| FEAT-06 | Phase 13 | Pending |
| FEAT-07 | Phase 13 | Pending |
| FEAT-08 | Phase 13 | Pending |
| TIER-01 | Phase 14 | Pending |
| TIER-02 | Phase 14 | Pending |
| TIER-03 | Phase 14 | Pending |
| TIER-04 | Phase 14 | Pending |
| TIER-05 | Phase 14 | Pending |
| HORIZON-01 | Phase 15 | Pending |
| HORIZON-02 | Phase 15 | Pending |
| HORIZON-03 | Phase 15 | Pending |

**Coverage:**
- v1.2 requirements: 23 total
- Mapped to phases: 23 ✓
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-04*
*Last updated: 2026-05-04 — traceability filled by `gsd-roadmapper` (all 23 REQ-IDs mapped to phases 12–15)*
