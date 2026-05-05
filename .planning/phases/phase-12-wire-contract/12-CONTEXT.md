# Phase 12: 12-wire-contract - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Land the new `/recommend` response contract — point estimate, demand band, per-line `reasoning_tier`, per-line `confidence_score`, and `signals[]` — and remove the order-quantity field. This is the cross-repo synchronization point with meshek v0.8: `@meshek/ml-client` TypeScript types must update via a coordinated PR before meshek-ml merges.

In scope: the wire shape only. Tier 1/2 emit minimal placeholder values for the new fields; Phase 14 (`14-honest-tier-semantics`) replaces those placeholders with honest pooled-prior-variance bands and richer signals. Tier 3 newsvendor logic moves out of the public response (kept as internal utility, no longer called by the response path).

Out of scope: better Tier 3 training, real-data benchmark eval, stock awareness, per-line dot UI rendering (meshek owns), Tier 2 shrinkage anchor re-tuning (Phase 15 owns).

</domain>

<decisions>
## Implementation Decisions

### Phase Scoping (MM-P1 vs MM-P3 split)
- Ship the new wire shape with **minimal defaults** for Tier 1/2 — `demand_lower = demand_upper = predicted_demand` and a single tier-name signal per line. Phase 14 (TIER-04/05) replaces these with pooled-prior-variance bands and richer signals.
- Tier 3: expose `predicted_demand` as the LightGBM forecast `mu`; derive `demand_lower` / `demand_upper` from `±1σ residual_std` (already used today for confidence). Newsvendor's `optimal_order_normal` stays as an internal utility but is no longer called from the response path.
- Retain per-line `unit` (kg / unit) — meshek expects it.
- Drop response-level `reasoning_tier` and `confidence_score` entirely — per-line is the new truth. The cross-repo PR is coordinated, so a clean break is acceptable.

### signals[] Semantics
- `signals[].contribution` units: **raw demand units** (same scale as `predicted_demand`, e.g., kg). meshek can render `contribution` directly without normalization context.
- `signals[].name` type: **open `str`** in Phase 12, with documented stable values in the Pydantic field's docstring. Phase 14 tightens to `Literal[…]` once the full enum is locked.
- `copy_key` format convention: **`signal.<snake_case_name>`** — e.g., `signal.tier_1_default`, `signal.shabbat_uplift`. meshek owns translation; meshek-ml owns the stable, predictable key shape.
- Minimum signals per line in Phase 12: **exactly one** tier-name signal — `{name: "<tier_name>", contribution: 1.0, copy_key: "signal.tier_<n>_default"}`. Mirrors REQ TIER-05 baseline.

### Schema Location & Migration
- New types live in `recommendation/schema.py` (existing module; already imported by `service/routes/recommend.py`, `engine.py`, and `tiers.py`). Do NOT move to `service/schemas.py`.
- Remove `ProductRecommendation.quantity`. Replace with `predicted_demand`, `demand_lower`, `demand_upper`, plus per-line `reasoning_tier`, `confidence_score`, `signals[]`. WIRE-01 + WIRE-05 mandate.
- Bump `SERVICE_VERSION` in `service/schemas.py` from `"1.1.0"` to `"1.2.0"` to mark the wire-contract change.
- Add a test that hits `GET /openapi.json` and asserts the new line-level fields are present and the legacy top-level `quantity` is absent. SC#1 explicitly says "verifiable from OpenAPI schema".

### Cross-Repo Coordination & Test Surface
- Open the `@meshek/ml-client` PR in the meshek repo as **draft first**. Finish meshek-ml's PR; get both reviewed. Merge order: meshek PR first, then meshek-ml. Halt this phase's PR before merge with a "BLOCKED until meshek PR @ <url> merges" note in the phase summary.
- Update existing tests **inline** — `tests/recommendation/test_engine.py`, `tests/recommendation/test_tier_1.py`, `tests/recommendation/test_tier_2.py`, `tests/recommendation/test_tier_3.py`, `tests/recommendation/test_schema.py`, `tests/service/test_recommend.py`. Delete obsolete `quantity` assertions; add new wire-shape assertions in the same files.
- Tests that currently assert response-level `reasoning_tier` / `confidence_score` (e.g., `test_recommend.py::test_recommend_tier1` checks `body["reasoning_tier"]`) migrate to per-line assertions: `body["recommendations"][0]["reasoning_tier"]`. Same surface, new location.
- Add **one contract test** asserting the full key set + types of `/recommend` for at least Tier 1 (simplest path). Plus the OpenAPI assertion test from Schema area. Together with inline test updates these cover SC#1 and SC#5.

### Claude's Discretion
- Internal naming for the new fields' Pydantic descriptions, validators (e.g., `demand_lower <= predicted_demand <= demand_upper`).
- Whether the contract test is in `tests/service/test_recommend.py` or a sibling `test_recommend_contract.py` (Claude picks based on file size).
- Exact assertion style for the OpenAPI test (key-presence vs full schema diff).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `recommendation/schema.py` — current `RecommendationResponse` and `ProductRecommendation` Pydantic v2 models with `ReasoningTier = Literal["category_default", "pooled_prior", "ml_forecast"]`. The literal stays; structure changes.
- `recommendation/tiers.py` — three tier functions returning `RecommendationResponse`. All three need updating to emit the new shape; Tier 3 also drops the newsvendor call from its return path.
- `recommendation/engine.py` — façade routing logic untouched at structural level; the engine still routes by `n_days` thresholds.
- `service/schemas.py` — request schemas (`RecommendRequest`) untouched. Holds `SERVICE_VERSION` constant — bump to `1.2.0` here.
- `service/routes/recommend.py` — handler imports `RecommendationResponse` from `recommendation/schema.py` and returns engine output unchanged. No structural change.
- `optimization/newsvendor.py` — `optimal_order_normal` stays as an internal utility (used by simulation/PPO benchmarks); just not called from the response path anymore.

### Established Patterns
- Pydantic v2 with `from __future__ import annotations` and `Field(...)` constraints for bounds/validators.
- `Literal[...]` for stable enums when values are fixed (`ReasoningTier`); for partially-locked enums (Phase 12 `signals.name`) use plain `str` and document stable values in the field description.
- Tests live alongside source under `tests/<package>/test_<module>.py`. Service-layer tests use the `app_client` fixture and exercise actual HTTP routes via TestClient.
- Pytest tests use `data_dir` fixture (patches `MESHEK_DATA_DIR`) and `_seed_merchant` helper for tier-routing scenarios.

### Integration Points
- `recommendation/__init__.py` re-exports `RecommendationResponse` and `ProductRecommendation`. Update re-exports if names change.
- `service/routes/recommend.py` declares the FastAPI endpoint with `response_model=RecommendationResponse` — automatic OpenAPI generation from the Pydantic class.
- `service/app.py` lifespan injects engine into `app.state.engine`. Untouched.
- Test fixtures in `tests/recommendation/conftest.py` and `tests/service/conftest.py` write SQLite stores and instantiate the test client. Untouched.
- Cross-repo: `@meshek/ml-client` types live in the meshek repo. Update via a coordinated PR; document the PR URL pair in the phase summary.

</code_context>

<specifics>
## Specific Ideas

The new wire shape (locked):

```python
class Signal(BaseModel):
    name: str  # stable enum (open str in P12; tightened to Literal in P14)
    contribution: float  # signed, in raw demand units (e.g., kg)
    copy_key: str  # format: "signal.<snake_case_name>"

class ProductRecommendation(BaseModel):
    product_id: str
    unit: str
    predicted_demand: float
    demand_lower: float
    demand_upper: float
    reasoning_tier: ReasoningTier  # per-line, was response-level
    confidence_score: float = Field(ge=0.0, le=1.0)  # per-line, was response-level
    signals: list[Signal]  # at least 1 entry

class RecommendationResponse(BaseModel):
    merchant_id: str
    recommendations: list[ProductRecommendation]
    generated_at: datetime
    # NOTE: reasoning_tier and confidence_score removed from response level.
```

Tier 1 (`category_default`) defaults in Phase 12:
- `predicted_demand = default_quantity` (from CategoryDefaultsConfig)
- `demand_lower = demand_upper = predicted_demand` (placeholder; Phase 14 fills with pooled-prior variance)
- `reasoning_tier = "category_default"`, `confidence_score = 0.2`
- `signals = [{name: "category_default", contribution: 1.0, copy_key: "signal.tier_1_default"}]`

Tier 2 (`pooled_prior`) defaults in Phase 12:
- `predicted_demand = shrinkage * own_mean + (1 - shrinkage) * pooled_mean` (the existing Tier 2 quantity is renamed)
- `demand_lower = demand_upper = predicted_demand` (placeholder; Phase 14 derives from pooled-prior variance)
- `reasoning_tier = "pooled_prior"`, `confidence_score` unchanged (linear `0.3 → 0.6`)
- `signals = [{name: "pooled_prior", contribution: 1.0, copy_key: "signal.tier_2_default"}]`

Tier 3 (`ml_forecast`) in Phase 12:
- `predicted_demand = float(mu)` — the LightGBM forecast value (not the newsvendor-derived quantity)
- `demand_lower = max(0.0, predicted_demand - residual_std)`
- `demand_upper = predicted_demand + residual_std`
- `reasoning_tier = "ml_forecast"`, `confidence_score` unchanged (residual-std-derived)
- `signals = [{name: "ml_forecast", contribution: 1.0, copy_key: "signal.tier_3_default"}]`

Cross-repo PR pair:
- meshek-ml PR: this branch's PR (the wire-contract change).
- meshek PR: `@meshek/ml-client` TypeScript type update mirroring the new shape.
- Sequence: open meshek PR as draft, finish meshek-ml work, review both, merge meshek first, merge meshek-ml after. Document both URLs in the phase summary.

</specifics>

<deferred>
## Deferred Ideas

- Honest pooled-prior-variance demand bands for Tier 1/2 — owned by Phase 14 (`14-honest-tier-semantics`, REQ TIER-04).
- Richer `signals[]` (multiple signals per line, holiday/Shabbat-driven contributions) — owned by Phase 14 (`14-honest-tier-semantics`, REQ TIER-05) and Phase 13 (which adds the underlying features).
- `signals.name` enum lockdown to `Literal[...]` — owned by Phase 14 once the full enum is known.
- Tier 2 shrinkage anchor re-tuning (`n / (n + 14)` → higher value) and graceful-degradation invariant — owned by Phase 15 (`15-tier-horizon-extension`).
- Calendar-derived feature columns (`is_shabbat`, holidays, etc.) — owned by Phase 13 (`13-exogenous-features`).
- Tier 3 retraining, real-data benchmark eval, stock awareness, dynamic pricing — out of scope per LOCKED decisions in v1.2 handoff doc.

</deferred>
