---
phase: 12-wire-contract
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/meshek_ml/recommendation/schema.py
  - src/meshek_ml/recommendation/tiers.py
  - src/meshek_ml/service/schemas.py
  - tests/recommendation/test_schema.py
  - tests/recommendation/test_tier_1.py
  - tests/recommendation/test_tier_2.py
  - tests/recommendation/test_tier_3.py
  - tests/recommendation/test_engine.py
autonomous: true
requirements: [WIRE-01, WIRE-02, WIRE-03, WIRE-04, WIRE-05, WIRE-06]
tags: [pydantic, schema, tier-constructors]

must_haves:
  truths:
    - "Pydantic ProductRecommendation has predicted_demand, demand_lower, demand_upper, reasoning_tier, confidence_score, signals — and NO quantity field."
    - "Pydantic Signal model has name (str), contribution (float), copy_key (str)."
    - "RecommendationResponse has merchant_id, recommendations, generated_at — and NO response-level reasoning_tier or confidence_score."
    - "All three tier constructors (tier_1_category_defaults, tier_2_pooled_priors, tier_3_ml_forecast) emit the new ProductRecommendation shape with exactly one tier-name signal per line."
    - "tier_3_ml_forecast does NOT call optimal_order_normal anywhere (newsvendor decoupled from response path)."
    - "tiers.py imports Signal alongside ProductRecommendation and RecommendationResponse, and does NOT import optimal_order_normal."
    - "SERVICE_VERSION in service/schemas.py is the literal string '1.2.0'."
    - "Unit tests in tests/recommendation/{test_schema, test_tier_1, test_tier_2, test_tier_3, test_engine}.py pass with no `quantity` references and per-line reasoning_tier/confidence_score assertions."
  artifacts:
    - path: "src/meshek_ml/recommendation/schema.py"
      provides: "Signal, ProductRecommendation (new shape), RecommendationResponse (no response-level tier/score)"
      contains: "class Signal"
    - path: "src/meshek_ml/recommendation/tiers.py"
      provides: "All three tier constructors emitting new shape; Signal imported; newsvendor import removed"
      contains: "Signal("
    - path: "src/meshek_ml/service/schemas.py"
      provides: "SERVICE_VERSION bumped to 1.2.0"
      contains: 'SERVICE_VERSION = "1.2.0"'
    - path: "tests/recommendation/test_schema.py"
      provides: "Rewritten helper + 4 test functions exercising new Pydantic shape"
      contains: "_valid_product_rec_kwargs"
  key_links:
    - from: "tier_1_category_defaults / tier_2_pooled_priors / tier_3_ml_forecast"
      to: "ProductRecommendation(...)"
      via: "constructor with new fields + signals=[Signal(...)]"
      pattern: "predicted_demand="
    - from: "tier_3_ml_forecast"
      to: "(no longer) optimal_order_normal"
      via: "newsvendor call removed; mu used directly as predicted_demand"
      pattern: "absence of optimal_order_normal"
---

<objective>
Rewrite the public Pydantic contract in `recommendation/schema.py` and update all three tier constructors in `recommendation/tiers.py` to emit the new wire shape: `predicted_demand`, `demand_lower`, `demand_upper`, per-line `reasoning_tier`, per-line `confidence_score`, and `signals[]` (with at least one tier-name `Signal` per line). Remove the `quantity` field, drop response-level `reasoning_tier` / `confidence_score`, and decouple `optimal_order_normal` from Tier 3's response path. Migrate all unit tests inline. Bump `SERVICE_VERSION` to `1.2.0`.

Purpose: This is the wire-freeze foundation for v1.2. The Pydantic models drive FastAPI's OpenAPI generation (verified in 12-RESEARCH.md), so updating them automatically updates the public contract that meshek's TypeScript client consumes. Tier constructors must follow because the engine returns whatever they construct.

Output: New shape live in the schema module; all unit-level tier and schema tests green against the new shape; `SERVICE_VERSION` bumped to mark the breaking change.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/phase-12-wire-contract/12-CONTEXT.md
@.planning/phases/phase-12-wire-contract/12-RESEARCH.md
@.planning/phases/phase-12-wire-contract/12-PATTERNS.md
@.planning/phases/phase-12-wire-contract/12-VALIDATION.md
@.planning/codebase/CONVENTIONS.md
@src/meshek_ml/recommendation/schema.py
@src/meshek_ml/recommendation/tiers.py
@src/meshek_ml/service/schemas.py

<interfaces>
<!-- Key types extracted from the codebase. Use these directly — no exploration needed. -->

Current `src/meshek_ml/recommendation/schema.py` (the file being rewritten):
```python
# Lines 1-12 (imports — keep, add model_validator):
from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field   # ADD: , model_validator

# Line 14 (keep unchanged):
ReasoningTier = Literal["category_default", "pooled_prior", "ml_forecast"]

# Lines 17-22 (ProductRecommendation — REPLACE entirely, see action).
# Lines 25-32 (RecommendationResponse — REPLACE entirely, see action).
```

Current `src/meshek_ml/recommendation/tiers.py` import block (lines 11-29):
```python
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import pandas as pd
from meshek_ml.forecasting.features import (
    add_calendar_features, add_lag_features, add_rolling_features,
)
from meshek_ml.optimization.newsvendor import optimal_order_normal   # REMOVE
from meshek_ml.recommendation.config import CategoryDefaultsConfig
from meshek_ml.recommendation.pooled_store import PooledStore
from meshek_ml.recommendation.schema import (
    ProductRecommendation,
    RecommendationResponse,
    # ADD: Signal,
)
```

Pattern reference from `src/meshek_ml/service/schemas.py` lines 96-100 — `model_validator(mode="after")` already in this project:
```python
@model_validator(mode="after")
def exactly_one_of_items_or_text(self) -> "SalesRequest":
    if (self.items is None) == (self.text is None):
        raise ValueError("Exactly one of 'items' or 'text' must be provided")
    return self
```

Pattern reference from current `recommendation/schema.py` line 31 — `Field(ge=, le=)`:
```python
confidence_score: float = Field(ge=0.0, le=1.0)
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Rewrite recommendation/schema.py with Signal, new ProductRecommendation, slim RecommendationResponse — and rewrite tests/recommendation/test_schema.py inline</name>

  <files>src/meshek_ml/recommendation/schema.py, tests/recommendation/test_schema.py</files>

  <read_first>
    - .planning/phases/phase-12-wire-contract/12-RESEARCH.md (Pitfall 3, 4, 7; Code Examples → "New `recommendation/schema.py` skeleton")
    - .planning/phases/phase-12-wire-contract/12-PATTERNS.md (sections "src/meshek_ml/recommendation/schema.py" and "tests/recommendation/test_schema.py")
    - src/meshek_ml/recommendation/schema.py (current 33-line file — replacing all of it)
    - tests/recommendation/test_schema.py (current 69-line file — full rewrite of helper and 4 test functions)
    - src/meshek_ml/service/schemas.py lines 96-100 (existing `model_validator(mode="after")` pattern to mirror)
  </read_first>

  <behavior>
    - test_required_fields: popping `reasoning_tier` from ProductRecommendation kwargs raises ValidationError
    - test_reasoning_tier_literal: invalid tier string raises; each of the three valid tiers constructs successfully on ProductRecommendation
    - test_confidence_bounds: confidence_score < 0.0 or > 1.0 raises; values at 0.0, 0.2, 0.95, 1.0 succeed
    - test_product_recommendation_fields: ProductRecommendation with valid kwargs exposes all new fields including signals; band invariant (lower=9, upper=8) raises; empty signals=[] raises; `quantity` is absent from model_dump(); RecommendationResponse.model_dump() does NOT contain `reasoning_tier` or `confidence_score` keys at the top level
  </behavior>

  <action>
    Per WIRE-01, WIRE-02, WIRE-03, WIRE-04, WIRE-06 — rewrite both files exactly as specified below. Do NOT add Signal to `recommendation/__init__.py` re-exports (D-LOCKED in CONTEXT.md, confirmed by RESEARCH.md "Re-export Surface Analysis" — no external consumer imports Signal).

    **A. Replace the entire contents of `src/meshek_ml/recommendation/schema.py` with:**

    ```python
    """Pydantic schemas for the recommendation service (Phase 12 wire contract).

    The locked v1.2 response contract: per-line ``reasoning_tier``,
    per-line ``confidence_score``, demand point estimate + band, and
    ``signals[]`` for explanation. ``quantity`` removed (WIRE-01/WIRE-05).
    Phase 14 will tighten ``Signal.name`` to a Literal once the enum locks.
    """
    from __future__ import annotations

    from datetime import datetime
    from typing import Literal

    from pydantic import BaseModel, Field, model_validator

    ReasoningTier = Literal["category_default", "pooled_prior", "ml_forecast"]


    class Signal(BaseModel):
        """A single explanation signal for a recommendation line (WIRE-04).

        ``name`` is an open string in v1.2; Phase 14 tightens it to a Literal.
        Documented stable values today: ``"category_default"``, ``"pooled_prior"``,
        ``"ml_forecast"``. ``contribution`` is signed and in raw demand units
        (kg) — same scale as ``predicted_demand``. ``copy_key`` follows the
        ``"signal.<snake_case_name>"`` convention; meshek owns translation.
        """

        name: str
        contribution: float
        copy_key: str


    class ProductRecommendation(BaseModel):
        """A single per-product recommendation line (WIRE-01..WIRE-04).

        ``demand_lower <= predicted_demand <= demand_upper`` is enforced via
        ``model_validator(mode="after")``. The placeholder case lower==upper==
        predicted satisfies the invariant trivially (Phase 14 fills variance).
        """

        product_id: str
        unit: str
        predicted_demand: float
        demand_lower: float
        demand_upper: float
        reasoning_tier: ReasoningTier
        confidence_score: float = Field(ge=0.0, le=1.0)
        signals: list[Signal] = Field(min_length=1)

        @model_validator(mode="after")
        def band_contains_estimate(self) -> "ProductRecommendation":
            """Ensure demand_lower <= predicted_demand <= demand_upper (WIRE-01)."""
            if not (self.demand_lower <= self.predicted_demand <= self.demand_upper):
                raise ValueError(
                    "demand_lower <= predicted_demand <= demand_upper required"
                )
            return self


    class RecommendationResponse(BaseModel):
        """Full response envelope for one merchant recommendation (WIRE-06).

        Note: response-level ``reasoning_tier`` and ``confidence_score`` are
        intentionally absent — they are now per-line on
        ``ProductRecommendation`` (WIRE-02/WIRE-03).
        """

        merchant_id: str
        recommendations: list[ProductRecommendation]
        generated_at: datetime
    ```

    **B. Replace the entire contents of `tests/recommendation/test_schema.py` with the rewrite from `12-PATTERNS.md` § "tests/recommendation/test_schema.py".** Specifically:

    1. Use the new imports block (adds `Signal` import).
    2. Define `_valid_product_rec_kwargs(**overrides)` returning kwargs for a valid `ProductRecommendation` (product_id="tomato", unit="kg", predicted_demand=8.0, demand_lower=8.0, demand_upper=8.0, reasoning_tier="category_default", confidence_score=0.2, signals=[Signal(name="category_default", contribution=1.0, copy_key="signal.tier_1_default")]).
    3. Define `_valid_response_kwargs(**overrides)` returning kwargs for a valid `RecommendationResponse` (merchant_id="shop_a", recommendations=[ProductRecommendation(**_valid_product_rec_kwargs())], generated_at=datetime.now(timezone.utc)). NO `reasoning_tier` or `confidence_score` keys.
    4. Rewrite the four test functions per 12-PATTERNS.md (`test_required_fields`, `test_reasoning_tier_literal`, `test_confidence_bounds`, `test_product_recommendation_fields`). The exact final contents of each function are spelled out in 12-PATTERNS.md lines 308-373; copy verbatim.

    Do NOT modify `recommendation/__init__.py` (RESEARCH.md "Re-export Surface Analysis" confirms `Signal` stays import-local).

    Do NOT introduce `Decimal`, `confloat`, or `Annotated` types — keep `float` + `Field(ge=, le=)` per project convention (matches existing `service/schemas.py` line 31 pattern).
  </action>

  <verify>
    <automated>.venv/bin/pytest tests/recommendation/test_schema.py -x --tb=short</automated>
  </verify>

  <acceptance_criteria>
    - `grep -c '^class Signal' src/meshek_ml/recommendation/schema.py` returns at least 1
    - `grep -c 'predicted_demand' src/meshek_ml/recommendation/schema.py` returns at least 1
    - `grep -c 'demand_lower' src/meshek_ml/recommendation/schema.py` returns at least 1
    - `grep -c 'demand_upper' src/meshek_ml/recommendation/schema.py` returns at least 1
    - `grep -c 'signals: list\[Signal\]' src/meshek_ml/recommendation/schema.py` returns at least 1
    - `grep -v '^[[:space:]]*#' src/meshek_ml/recommendation/schema.py | grep -v '^[[:space:]]*\"' | grep -c 'quantity' ` returns 0 (no `quantity` in code, comments/docstrings ignored)
    - `grep -v '^[[:space:]]*#' src/meshek_ml/recommendation/schema.py | grep -c 'model_validator' ` returns at least 1
    - In `RecommendationResponse` body: response-level `reasoning_tier` and `confidence_score` declarations are absent (verified by `grep -A 10 'class RecommendationResponse' src/meshek_ml/recommendation/schema.py | grep -v '^[[:space:]]*#' | grep -E 'reasoning_tier|confidence_score'` returns nothing)
    - `grep -c '_valid_product_rec_kwargs' tests/recommendation/test_schema.py` returns at least 1
    - `grep -v '^[[:space:]]*#' tests/recommendation/test_schema.py | grep -c '\.quantity' ` returns 0
    - `.venv/bin/pytest tests/recommendation/test_schema.py -x --tb=short` exits 0 with all 4 test functions passing
  </acceptance_criteria>

  <done>
    schema.py contains the new `Signal`, `ProductRecommendation` (with band validator + signals list), and slim `RecommendationResponse` (no response-level fields). test_schema.py is fully rewritten. `pytest tests/recommendation/test_schema.py` is green. No `quantity` references remain in schema.py code or test_schema.py.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Rewrite all three tier constructors in tiers.py to emit new shape; remove newsvendor import; bump SERVICE_VERSION; migrate tier_1/tier_2/tier_3/engine tests inline</name>

  <files>src/meshek_ml/recommendation/tiers.py, src/meshek_ml/service/schemas.py, tests/recommendation/test_tier_1.py, tests/recommendation/test_tier_2.py, tests/recommendation/test_tier_3.py, tests/recommendation/test_engine.py</files>

  <read_first>
    - .planning/phases/phase-12-wire-contract/12-RESEARCH.md (sections "Newsvendor Decoupling — Exact Lines Changing in `tiers.py`", Pitfall 1, 2, 3, 5, 6, 8)
    - .planning/phases/phase-12-wire-contract/12-PATTERNS.md (sections "src/meshek_ml/recommendation/tiers.py", "tests/recommendation/test_tier_1.py", "test_tier_2.py", "test_tier_3.py", "test_engine.py")
    - src/meshek_ml/recommendation/tiers.py (full file — surgical edits across all three tiers)
    - src/meshek_ml/service/schemas.py line 24 (SERVICE_VERSION constant)
    - tests/recommendation/test_tier_1.py (28 lines)
    - tests/recommendation/test_tier_2.py (97 lines)
    - tests/recommendation/test_tier_3.py (99 lines)
    - tests/recommendation/test_engine.py (123 lines)
  </read_first>

  <behavior>
    - tier_1_category_defaults returns RecommendationResponse with no response-level reasoning_tier/confidence_score, and each rec has reasoning_tier=="category_default", confidence_score==0.2, signals=[Signal(name="category_default", contribution=1.0, copy_key="signal.tier_1_default")], predicted_demand==p.default_quantity
    - tier_2_pooled_priors returns RecommendationResponse with each rec having reasoning_tier=="pooled_prior", confidence_score in [0.3, 0.6] depending on n_days, signals=[Signal(name="pooled_prior", contribution=1.0, copy_key="signal.tier_2_default")], predicted_demand==round(shrink*own_mean+(1-shrink)*pooled_mean, 4)
    - tier_3_ml_forecast does NOT call optimal_order_normal, returns RecommendationResponse with each rec having reasoning_tier=="ml_forecast", confidence_score in [0.6, 0.95], predicted_demand==round(float(mu), 4), demand_lower==round(max(0.0, mu-residual_std), 4), demand_upper==round(mu+residual_std, 4), signals=[Signal(name="ml_forecast", contribution=1.0, copy_key="signal.tier_3_default")]
    - SERVICE_VERSION constant equals literal string "1.2.0"
    - All test_tier_1/test_tier_2/test_tier_3/test_engine assertions migrate from response-level (resp.reasoning_tier, resp.confidence_score, rec.quantity) to per-line (resp.recommendations[0].reasoning_tier, .confidence_score, .predicted_demand)
  </behavior>

  <action>
    Per WIRE-01, WIRE-02, WIRE-03, WIRE-04, WIRE-05 — execute all six file edits below. Use the exact code blocks from 12-PATTERNS.md and 12-RESEARCH.md (do not paraphrase).

    **A. `src/meshek_ml/recommendation/tiers.py` — three surgical edits per 12-PATTERNS.md § "src/meshek_ml/recommendation/tiers.py" and 12-RESEARCH.md § "Newsvendor Decoupling":**

    1. **Imports (lines 23, 26-29):** Remove the line `from meshek_ml.optimization.newsvendor import optimal_order_normal` (line 23) entirely (per Pitfall 2 — leaving the import triggers ruff F401). Update the schema import block (currently lines 26-29) to add `Signal`:
       ```python
       from meshek_ml.recommendation.schema import (
           ProductRecommendation,
           RecommendationResponse,
           Signal,
       )
       ```

    2. **`tier_1_category_defaults` body (replaces current lines 37-51):** Use the constructor block from 12-PATTERNS.md § "Tier 1 constructor rewrite" verbatim — `ProductRecommendation(product_id=p.product_id, unit=p.unit, predicted_demand=p.default_quantity, demand_lower=p.default_quantity, demand_upper=p.default_quantity, reasoning_tier="category_default", confidence_score=0.2, signals=[Signal(name="category_default", contribution=1.0, copy_key="signal.tier_1_default")])`. The `RecommendationResponse(...)` constructor at the end of the function drops `reasoning_tier=...` and `confidence_score=...` — keep only `merchant_id`, `recommendations`, `generated_at`.

    3. **`tier_2_pooled_priors` inner-loop body (replaces current lines 73-78) and final `RecommendationResponse(...)` (current lines 81-87):** Per 12-PATTERNS.md § "Tier 2 inner-loop rewrite" — inside the loop, replace the `ProductRecommendation(product_id=product, quantity=round(q, 2), unit="kg")` with the new constructor (predicted_demand=round(q, 4), demand_lower=round(q, 4), demand_upper=round(q, 4), reasoning_tier="pooled_prior", confidence_score=round(confidence, 6), signals=[Signal(name="pooled_prior", contribution=1.0, copy_key="signal.tier_2_default")]). NOTE: `confidence` is currently computed at line 80 (AFTER the loop). Per 12-PATTERNS.md note at line 183 and Pitfall 8 in 12-RESEARCH.md: move the `confidence = 0.3 + ...` computation to BEFORE the loop so it's in scope when constructing each `ProductRecommendation`. The final `RecommendationResponse(...)` drops `reasoning_tier` and `confidence_score` arguments.

    4. **`tier_3_ml_forecast` inner-loop body (replaces current lines 132-146) and final `RecommendationResponse(...)` (current lines 153-159):** Per 12-PATTERNS.md § "Tier 3 inner-loop rewrite" and 12-RESEARCH.md § "New inner loop body":
       - DELETE the `q = optimal_order_normal(...)` call block (current lines 134-139). The newsvendor function is no longer called from the response path (WIRE-05).
       - Move the confidence computation block (current lines 150-152: `y_mean = ...`, `raw = ...`, `confidence = max(0.6, min(0.95, raw))`) to BEFORE the `for product, mean_demand in zip(last_rows["product"], mu):` loop, so `confidence` is in scope when constructing each `ProductRecommendation` (Pitfall 8).
       - Inside the loop, append `ProductRecommendation(product_id=str(product), unit="kg", predicted_demand=round(mu_f, 4), demand_lower=round(max(0.0, mu_f - float(residual_std)), 4), demand_upper=round(mu_f + float(residual_std), 4), reasoning_tier="ml_forecast", confidence_score=round(confidence, 6), signals=[Signal(name="ml_forecast", contribution=1.0, copy_key="signal.tier_3_default")])` where `mu_f = float(mean_demand)`.
       - Final `RecommendationResponse(...)` drops `reasoning_tier` and `confidence_score` arguments.

    Also: the `tier_3_ml_forecast` signature still has `underage_cost: float = 2.0, overage_cost: float = 1.0` parameters. KEEP them — they are part of the public function signature and removing them would break callers. They are now unused within the function body; if ruff flags them as unused parameters (F841 does not apply, and ARG001 is not in the project's ruff config — confirmed by 12-RESEARCH.md "no new dependencies"), no action needed. If a lint warning appears, prefix with `_` (rename to `_underage_cost`, `_overage_cost`) ONLY if ruff fails — otherwise leave as-is for backward compatibility.

    **B. `src/meshek_ml/service/schemas.py` line 24:** Change `SERVICE_VERSION = "1.1.0"` to `SERVICE_VERSION = "1.2.0"`. No other edits to this file.

    **C. `tests/recommendation/test_tier_1.py`:** Apply the three edits in 12-PATTERNS.md § "tests/recommendation/test_tier_1.py" verbatim:
    - Line 9: `resp.reasoning_tier == "category_default"` → `resp.recommendations[0].reasoning_tier == "category_default"`
    - Line 14: `resp.confidence_score == 0.2` → `resp.recommendations[0].confidence_score == 0.2`
    - Line 22 (in `test_quantities_match_yaml`): `rec.quantity == p.default_quantity` → `rec.predicted_demand == p.default_quantity`
    - After the `predicted_demand` assertion in `test_quantities_match_yaml`, insert two lines:
      ```python
      assert len(rec.signals) == 1
      assert rec.signals[0].copy_key == "signal.tier_1_default"
      ```

    **D. `tests/recommendation/test_tier_2.py`:** Apply the five edits in 12-PATTERNS.md § "tests/recommendation/test_tier_2.py" verbatim:
    - Line 39: `resp.reasoning_tier == "pooled_prior"` → `resp.recommendations[0].reasoning_tier == "pooled_prior"`
    - Lines 47-48: `r1.confidence_score` → `r1.recommendations[0].confidence_score`; `r13.confidence_score` → `r13.recommendations[0].confidence_score`
    - Line 55 (in `test_confidence_monotonic`): `tier_2_pooled_priors(...).confidence_score` → `tier_2_pooled_priors(...).recommendations[0].confidence_score`
    - Line 69 (in `test_shrinkage_weights`): `rec.quantity == pytest.approx(round(40 / 3, 2), abs=1e-6)` → `rec.predicted_demand == pytest.approx(round(40 / 3, 2), abs=1e-6)` (Pitfall 5 — value unchanged, only field renamed; note the rounding precision in the source bumped from 2 to 4 decimals, so adjust expected to `pytest.approx(round(40 / 3, 4), abs=1e-6)` IF the test fails; if 1e-6 abs tolerance covers both rounding levels, leave as-is)
    - Line 89 (in `test_uses_pooled_store`): `resp.recommendations[0].quantity` → `resp.recommendations[0].predicted_demand`

    **E. `tests/recommendation/test_tier_3.py`:** Apply the four edits in 12-PATTERNS.md § "tests/recommendation/test_tier_3.py":
    - Line 24: `resp.reasoning_tier == "ml_forecast"` → `resp.recommendations[0].reasoning_tier == "ml_forecast"`
    - Line 40: `0.6 <= resp.confidence_score <= 0.95` → `0.6 <= resp.recommendations[0].confidence_score <= 0.95`
    - Lines 44-56: rename function `test_quantities_non_negative` → `test_predicted_demand_non_negative` (Pitfall 6); change the assertion `rec.quantity >= 0` → `rec.predicted_demand >= 0`
    - Line 99 (in `test_inference_never_reads_disk`): `resp.reasoning_tier == "ml_forecast"` → `resp.recommendations[0].reasoning_tier == "ml_forecast"`

    **F. `tests/recommendation/test_engine.py`:** Apply the seven edits in 12-PATTERNS.md § "tests/recommendation/test_engine.py" verbatim — every `resp.reasoning_tier`, `resp.confidence_score`, `engine.recommend(...).confidence_score`, and `r2/r3.confidence_score` becomes `.recommendations[0].reasoning_tier` / `.recommendations[0].confidence_score` per the table. The exact line numbers and before/after pairs are enumerated in 12-PATTERNS.md lines 510-587.

    Do NOT introduce parallel/sibling test files — all migration is inline (CONTEXT.md locked decision).
  </action>

  <verify>
    <automated>.venv/bin/pytest tests/recommendation/ -x --tb=short</automated>
  </verify>

  <acceptance_criteria>
    - `grep -c 'optimal_order_normal' src/meshek_ml/recommendation/tiers.py` returns 0
    - `grep -c 'Signal,' src/meshek_ml/recommendation/tiers.py` returns at least 1 (in the schema import block)
    - `grep -c 'signals=\[Signal(' src/meshek_ml/recommendation/tiers.py` returns at least 3 (one per tier)
    - `grep -c 'predicted_demand=' src/meshek_ml/recommendation/tiers.py` returns at least 3
    - `grep -c 'copy_key="signal.tier_1_default"' src/meshek_ml/recommendation/tiers.py` returns at least 1
    - `grep -c 'copy_key="signal.tier_2_default"' src/meshek_ml/recommendation/tiers.py` returns at least 1
    - `grep -c 'copy_key="signal.tier_3_default"' src/meshek_ml/recommendation/tiers.py` returns at least 1
    - In each tier function, the `RecommendationResponse(...)` constructor does NOT include `reasoning_tier=` or `confidence_score=` (verify via `grep -A 5 'return RecommendationResponse' src/meshek_ml/recommendation/tiers.py | grep -E 'reasoning_tier=|confidence_score='` returns 0 lines)
    - `grep -c '"1.2.0"' src/meshek_ml/service/schemas.py` returns at least 1
    - `grep -c '"1.1.0"' src/meshek_ml/service/schemas.py` returns 0
    - `grep -v '^[[:space:]]*#' tests/recommendation/test_tier_1.py | grep -c '\.quantity' ` returns 0
    - `grep -v '^[[:space:]]*#' tests/recommendation/test_tier_2.py | grep -c '\.quantity' ` returns 0
    - `grep -v '^[[:space:]]*#' tests/recommendation/test_tier_3.py | grep -c '\.quantity' ` returns 0
    - `grep -E 'resp\.reasoning_tier|resp\.confidence_score' tests/recommendation/test_engine.py | grep -v 'recommendations\[0\]' | wc -l` returns 0 (every response-level access goes through `recommendations[0]`)
    - `.venv/bin/pytest tests/recommendation/ -x --tb=short` exits 0 with all tier and engine tests passing
    - `.venv/bin/ruff check src/meshek_ml/recommendation/tiers.py` passes (no F401 from orphaned newsvendor import)
  </acceptance_criteria>

  <done>
    All three tier constructors emit the new ProductRecommendation shape with one tier-name Signal each. `optimal_order_normal` import and call removed from tiers.py. SERVICE_VERSION is "1.2.0". All four recommendation test files migrate inline to per-line assertions and `predicted_demand` field access. `pytest tests/recommendation/ -x` is green. `ruff check src/meshek_ml/recommendation/tiers.py` passes.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client → /recommend | Existing authenticated endpoint; this phase only changes response shape, not request validation |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-12-01 | Tampering | ProductRecommendation band invariant | mitigate | `model_validator(mode="after")` enforces `demand_lower <= predicted_demand <= demand_upper` (per WIRE-01) at model construction time; ValidationError propagates to FastAPI as 500 if constructed server-side with bad data |
| T-12-02 | Information Disclosure | RecommendationResponse output | accept | New shape exposes `predicted_demand` and band — no PII, no tokens; same risk class as the previous `quantity` field |
| T-12-03 | Denial of Service | signals list size | accept | `Field(min_length=1)` enforces lower bound; upper bound left unbounded — Phase 12 always emits exactly 1 signal per line, so practical max ≤ rec count (already bounded by merchant catalog size, ASVS V13 unchanged from v1.1) |
</threat_model>

<verification>
- `.venv/bin/pytest tests/recommendation/ -x --tb=short` exits 0 (covers WIRE-01..WIRE-05 unit-level)
- `.venv/bin/ruff check src/meshek_ml/recommendation/ src/meshek_ml/service/schemas.py` passes (no orphaned imports, no style regressions)
- No `quantity` references in `src/meshek_ml/recommendation/schema.py`, `src/meshek_ml/recommendation/tiers.py`, or any of the 5 migrated test files (excluding comments)
- `SERVICE_VERSION == "1.2.0"` in `src/meshek_ml/service/schemas.py`
</verification>

<success_criteria>
- New `Signal` and `ProductRecommendation` types live in `recommendation/schema.py` with the band validator and `signals: list[Signal] = Field(min_length=1)`
- `RecommendationResponse` no longer carries response-level `reasoning_tier` or `confidence_score`
- All three tier constructors emit the new shape with one tier-name signal each
- Newsvendor import and call removed from `tiers.py`
- `SERVICE_VERSION = "1.2.0"`
- 5 unit test files migrate inline; `pytest tests/recommendation/` green
- WIRE-01..WIRE-06 covered at the unit level (WIRE-06 OpenAPI test lives in plan 02)
</success_criteria>

<output>
After completion, create `.planning/phases/phase-12-wire-contract/12-01-SUMMARY.md` documenting:
- Files modified with line counts
- Test migration delta (assertions changed)
- Confirmation that `optimal_order_normal` is no longer called from response path
- pytest output summary
</output>
