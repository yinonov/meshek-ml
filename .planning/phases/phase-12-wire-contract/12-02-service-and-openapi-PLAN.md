---
phase: 12-wire-contract
plan: 02
type: execute
wave: 2
depends_on: ["12-01"]
files_modified:
  - tests/service/test_recommend.py
autonomous: true
requirements: [WIRE-01, WIRE-02, WIRE-03, WIRE-04, WIRE-06]
tags: [fastapi, openapi, contract-test, http-integration]

must_haves:
  truths:
    - "POST /recommend over HTTP returns body with per-line reasoning_tier and confidence_score (no response-level fields)."
    - "GET /openapi.json exposes ProductRecommendation.properties with predicted_demand, demand_lower, demand_upper, reasoning_tier, confidence_score, signals — and NO quantity."
    - "GET /openapi.json exposes RecommendationResponse.properties WITHOUT reasoning_tier or confidence_score at the response level."
    - "A Tier-1 contract test pins the full expected key set + types for both response envelope and per-line shape."
    - "tests/service/test_recommend.py contains the new test functions test_openapi_wire_contract and test_tier1_contract_key_set."
    - "All existing tests/service/test_recommend.py per-tier assertions migrate from response-level to per-line successfully."
    - "Full pytest suite passes."
  artifacts:
    - path: "tests/service/test_recommend.py"
      provides: "Migrated per-tier HTTP assertions + new OpenAPI contract test + new full-key-set Tier-1 contract test"
      contains: "test_openapi_wire_contract"
  key_links:
    - from: "test_openapi_wire_contract"
      to: "GET /openapi.json"
      via: "TestClient.get('/openapi.json') → schema['components']['schemas']['ProductRecommendation']['properties']"
      pattern: "openapi\\.json"
    - from: "test_tier1_contract_key_set"
      to: "POST /recommend with Tier 1 merchant"
      via: "_seed_merchant + app_client.post"
      pattern: "test_tier1_contract_key_set"
---

<objective>
Migrate the service-layer HTTP integration tests to the new wire shape, and add two new contract tests: (1) `test_openapi_wire_contract` asserting the OpenAPI schema reflects the new per-line fields and excludes `quantity`; (2) `test_tier1_contract_key_set` pinning the full key set + types for a Tier-1 response. Then run the full pytest suite as the wave-2 gate.

Purpose: Plan 01 changes the Pydantic models, which automatically updates FastAPI's OpenAPI schema (verified in 12-RESEARCH.md). Plan 02 verifies that automatic propagation actually happened end-to-end across the HTTP layer and OpenAPI generation. The full key-set Tier-1 contract test (per CONTEXT.md decision) pins the exact public shape so meshek can rely on it.

Output: All HTTP assertions use per-line locations; two new contract tests appended to `tests/service/test_recommend.py`; full suite green.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/phase-12-wire-contract/12-CONTEXT.md
@.planning/phases/phase-12-wire-contract/12-RESEARCH.md
@.planning/phases/phase-12-wire-contract/12-PATTERNS.md
@.planning/phases/phase-12-wire-contract/12-VALIDATION.md
@.planning/phases/phase-12-wire-contract/12-01-SUMMARY.md
@tests/service/test_recommend.py
@tests/service/conftest.py

<interfaces>
<!-- Existing fixtures and helpers in tests/service/test_recommend.py — reuse, do not redefine. -->

`app_client` fixture: session-scoped, model-loaded TestClient (from tests/service/conftest.py).
`data_dir` fixture: patches `MESHEK_DATA_DIR` to a temp directory.
`no_model_client` fixture: TestClient with model NOT loaded (used in degraded-mode test at line 131).

`_seed_merchant(data_dir, merchant_id: str, days: int) -> None` — helper at lines 23-45 of tests/service/test_recommend.py. Reuse as-is for new contract test.

OpenAPI schema shape (from FastAPI):
```python
schema = resp.json()
schema["components"]["schemas"]["ProductRecommendation"]["properties"]
schema["components"]["schemas"]["RecommendationResponse"]["properties"]
schema["components"]["schemas"]["Signal"]["properties"]   # auto-emitted because RecommendationResponse references Signal
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Migrate existing tests/service/test_recommend.py per-tier assertions to per-line locations and add the OpenAPI + Tier-1 contract tests</name>

  <files>tests/service/test_recommend.py</files>

  <read_first>
    - .planning/phases/phase-12-wire-contract/12-RESEARCH.md (Pitfall 3 table, Code Examples → "Tier 1 contract test" and "OpenAPI assertion test")
    - .planning/phases/phase-12-wire-contract/12-PATTERNS.md (section "tests/service/test_recommend.py" — exact line-by-line edits and the two new functions verbatim)
    - .planning/phases/phase-12-wire-contract/12-VALIDATION.md (Wave 0 Requirements, Per-Task Verification Map for plan 02)
    - tests/service/test_recommend.py (full file — 153 lines)
    - tests/service/conftest.py (for `app_client` / `data_dir` fixture confirmations)
    - .planning/phases/phase-12-wire-contract/12-01-SUMMARY.md (plan 01 outputs — confirms schema rewrite landed)
  </read_first>

  <behavior>
    - test_recommend_tier1: HTTP POST /recommend for a 0-day merchant returns 200; body["recommendations"][0]["reasoning_tier"] == "category_default"; "confidence_score" key exists at body["recommendations"][0]; body itself has NO top-level "reasoning_tier" or "confidence_score"
    - test_recommend_tier2: same pattern; body["recommendations"][0]["reasoning_tier"] == "pooled_prior"; 0.3 <= body["recommendations"][0]["confidence_score"] <= 0.6
    - test_recommend_tier3: same pattern; body["recommendations"][0]["reasoning_tier"] == "ml_forecast"; 0.6 <= body["recommendations"][0]["confidence_score"] <= 0.95
    - test_tier1_in_degraded_mode: body["recommendations"][0]["reasoning_tier"] == "category_default" when model fails to load
    - test_openapi_wire_contract (NEW): GET /openapi.json returns 200; ProductRecommendation properties include predicted_demand, demand_lower, demand_upper, reasoning_tier, confidence_score, signals; ProductRecommendation properties does NOT include quantity; RecommendationResponse properties does NOT include reasoning_tier or confidence_score
    - test_tier1_contract_key_set (NEW): seeds a 0-day merchant, calls POST /recommend, asserts body has exactly the response envelope keys (merchant_id, recommendations, generated_at) and NO quantity / response-level reasoning_tier / response-level confidence_score; per-line types for predicted_demand, demand_lower, demand_upper (numeric), reasoning_tier ("category_default"), confidence_score in [0,1]; signals[0] has name, contribution, copy_key with copy_key starting with "signal."
  </behavior>

  <action>
    Per WIRE-01..WIRE-04 (HTTP-level coverage) and WIRE-06 — execute all migrations + appends below. Use the verbatim code blocks from 12-PATTERNS.md § "tests/service/test_recommend.py" and 12-RESEARCH.md § "Tier 1 contract test" / "OpenAPI assertion test".

    **A. Inline assertion migration in `tests/service/test_recommend.py`** — six edits per 12-PATTERNS.md (and Pitfall 3 in 12-RESEARCH.md):

    1. Line 59 (in `test_recommend_tier1`): `body["reasoning_tier"] == "category_default"` → `body["recommendations"][0]["reasoning_tier"] == "category_default"`
    2. Line 61 (in `test_recommend_tier1`): `"confidence_score" in body` → `"confidence_score" in body["recommendations"][0]`
    3. Line 74 (in `test_recommend_tier2`): `body["reasoning_tier"] == "pooled_prior"` → `body["recommendations"][0]["reasoning_tier"] == "pooled_prior"`
    4. Line 75 (in `test_recommend_tier2`): `0.3 <= body["confidence_score"] <= 0.6` → `0.3 <= body["recommendations"][0]["confidence_score"] <= 0.6`
    5. Line 84 (in `test_recommend_tier3`): `body["reasoning_tier"] == "ml_forecast"` → `body["recommendations"][0]["reasoning_tier"] == "ml_forecast"`
    6. Line 85 (in `test_recommend_tier3`): `0.6 <= body["confidence_score"] <= 0.95` → `0.6 <= body["recommendations"][0]["confidence_score"] <= 0.95`
    7. Line 131 (in `test_tier1_in_degraded_mode`): `body["reasoning_tier"] == "category_default"` → `body["recommendations"][0]["reasoning_tier"] == "category_default"`

    Do NOT change any other assertions, fixtures, or imports. The `_seed_merchant` helper (lines 23-45) is reused; do not redefine it.

    **B. Append the new `test_openapi_wire_contract` function** at the end of `tests/service/test_recommend.py`, exactly as specified in 12-RESEARCH.md "OpenAPI assertion test" (lines 517-531) / 12-PATTERNS.md "New `test_openapi_wire_contract` function" (lines 640-653):

    ```python
    def test_openapi_wire_contract(app_client):
        """GET /openapi.json reflects new wire shape; legacy quantity absent (WIRE-06)."""
        resp = app_client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        pr_props = schema["components"]["schemas"]["ProductRecommendation"]["properties"]
        for field in ("predicted_demand", "demand_lower", "demand_upper",
                      "reasoning_tier", "confidence_score", "signals"):
            assert field in pr_props, f"OpenAPI missing field: {field}"
        assert "quantity" not in pr_props, "quantity must be absent from OpenAPI schema"
        rr_props = schema["components"]["schemas"]["RecommendationResponse"]["properties"]
        assert "reasoning_tier" not in rr_props
        assert "confidence_score" not in rr_props
    ```

    **C. Append the new `test_tier1_contract_key_set` function** immediately after `test_openapi_wire_contract`, exactly as specified in 12-RESEARCH.md "Tier 1 contract test" (lines 479-512) / 12-PATTERNS.md "New `test_tier1_contract_key_set` function" (lines 658-691):

    ```python
    def test_tier1_contract_key_set(app_client, data_dir):
        """Full key-set + type contract test for Tier 1 response (WIRE-01 to WIRE-06)."""
        _seed_merchant(data_dir, "contract_t1", days=0)
        resp = app_client.post("/recommend", json={"merchant_id": "contract_t1"})
        assert resp.status_code == 200
        body = resp.json()

        # Response envelope
        assert set(body.keys()) >= {"merchant_id", "recommendations", "generated_at"}
        assert "reasoning_tier" not in body, "response-level reasoning_tier must be absent"
        assert "confidence_score" not in body, "response-level confidence_score must be absent"
        assert "quantity" not in body

        # Per-line fields
        assert len(body["recommendations"]) >= 1
        line = body["recommendations"][0]
        assert isinstance(line["product_id"], str)
        assert isinstance(line["unit"], str)
        assert isinstance(line["predicted_demand"], (int, float))
        assert isinstance(line["demand_lower"], (int, float))
        assert isinstance(line["demand_upper"], (int, float))
        assert line["reasoning_tier"] == "category_default"
        assert 0.0 <= line["confidence_score"] <= 1.0
        assert "quantity" not in line

        # Signals
        assert isinstance(line["signals"], list)
        assert len(line["signals"]) >= 1
        sig = line["signals"][0]
        assert isinstance(sig["name"], str)
        assert isinstance(sig["contribution"], (int, float))
        assert isinstance(sig["copy_key"], str)
        assert sig["copy_key"].startswith("signal.")
    ```

    Per CONTEXT.md "Claude's Discretion": both new tests live INLINE in `tests/service/test_recommend.py` (not in a sibling `test_recommend_contract.py`) — the file is short enough (~153 lines today + ~50 new lines = ~200) that splitting adds no value.

    Per CONTEXT.md "key_set" decision: `test_tier1_contract_key_set` uses a relaxed superset assertion (`set(body.keys()) >= {"merchant_id", "recommendations", "generated_at"}`) so future additive fields don't break it, while still pinning that `quantity` and response-level tier/score are absent (the explicit `not in` assertions).

    No new fixtures, no parallel test files, no edits outside `tests/service/test_recommend.py`.
  </action>

  <verify>
    <automated>.venv/bin/pytest tests/service/test_recommend.py -x --tb=short -v</automated>
  </verify>

  <acceptance_criteria>
    - `grep -c 'test_openapi_wire_contract' tests/service/test_recommend.py` returns at least 2 (function definition + at least one self-reference is acceptable; minimum 1 def line)
    - `grep -c '^def test_openapi_wire_contract' tests/service/test_recommend.py` returns 1
    - `grep -c '^def test_tier1_contract_key_set' tests/service/test_recommend.py` returns 1
    - In existing tier tests, no `body["reasoning_tier"]` or `body["confidence_score"]` accesses remain at top-level — verify: `grep -E 'body\["reasoning_tier"\]|body\["confidence_score"\]' tests/service/test_recommend.py | grep -v 'recommendations\[0\]' | grep -v '"reasoning_tier" not in body' | grep -v '"confidence_score" not in body' | wc -l` returns 0
    - `grep -c 'body\["recommendations"\]\[0\]\["reasoning_tier"\]' tests/service/test_recommend.py` returns at least 4 (covers tier1, tier2, tier3, degraded mode)
    - `grep -c 'openapi.json' tests/service/test_recommend.py` returns at least 1
    - `grep -c 'ProductRecommendation' tests/service/test_recommend.py` returns at least 1 (in OpenAPI test)
    - `.venv/bin/pytest tests/service/test_recommend.py -x --tb=short` exits 0 with the new test functions visible in `-v` output
  </acceptance_criteria>

  <done>
    All 7 inline migrations applied. `test_openapi_wire_contract` and `test_tier1_contract_key_set` appended to `tests/service/test_recommend.py`. `pytest tests/service/test_recommend.py -x` is green. The OpenAPI test confirms the public schema lost `quantity` and gained the new per-line fields; the Tier-1 contract test confirms the full HTTP shape.
  </done>
</task>

<task type="auto">
  <name>Task 2: Run the full pytest suite as the wave-2 gate</name>

  <files>tests/ (read-only — full suite execution; no source edits unless a regression is found)</files>

  <read_first>
    - .planning/phases/phase-12-wire-contract/12-VALIDATION.md (Sampling Rate — wave-merge command)
    - tests/conftest.py (top-level shared fixtures)
  </read_first>

  <action>
    Run the full pytest suite to confirm no other test in the repo regresses against the new wire shape. Per 12-VALIDATION.md "Per Wave Merge" gate.

    Run: `.venv/bin/pytest tests/ -x --tb=short`

    If any test outside `tests/recommendation/` or `tests/service/` fails because it imported `ProductRecommendation` with old kwargs (`quantity=...`) or asserted on response-level fields, identify it and fix inline using the same migration pattern from Plan 01 (Pitfall 3 in 12-RESEARCH.md). The expected baseline is that no such tests exist outside the 6 already migrated, but verifying empirically is the wave-2 gate.

    Do NOT relax assertions, skip tests, or mark them xfail to make the suite pass. If something genuinely fails, capture the failure, fix the root cause, and re-run.
  </action>

  <verify>
    <automated>.venv/bin/pytest tests/ -x --tb=short</automated>
  </verify>

  <acceptance_criteria>
    - `.venv/bin/pytest tests/ -x --tb=short` exits 0
    - No test is skipped or xfailed as part of this wave
    - The summary line shows the new tests `test_openapi_wire_contract` and `test_tier1_contract_key_set` ran (verify with `.venv/bin/pytest tests/service/test_recommend.py -v 2>&1 | grep -E 'test_openapi_wire_contract|test_tier1_contract_key_set' | wc -l` returns at least 2)
    - `grep -rn 'ProductRecommendation(.*quantity=' tests/ src/ 2>/dev/null | wc -l` returns 0 (no leftover `quantity=` constructor calls anywhere in source or tests)
  </acceptance_criteria>

  <done>
    Full `pytest tests/` suite green. No quantity= constructor calls remain anywhere in the repo. The two new contract tests are visible in pytest output.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client → /recommend | Existing authenticated boundary; this plan only verifies the response shape via tests |
| client → /openapi.json | Public unauthenticated endpoint; this plan adds a contract assertion against it |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-12-04 | Information Disclosure | /openapi.json | accept | Already public in v1.1; the new schema exposes `predicted_demand` and band — no new sensitive fields, same risk class as the previous `quantity` field |
| T-12-05 | Tampering | Contract drift | mitigate | `test_openapi_wire_contract` and `test_tier1_contract_key_set` pin the public shape so accidental schema changes break CI before they ship |
</threat_model>

<verification>
- `.venv/bin/pytest tests/service/test_recommend.py -x` is green (covers WIRE-01..WIRE-04 at HTTP layer + WIRE-06 OpenAPI)
- `.venv/bin/pytest tests/ -x` full suite is green
- `test_openapi_wire_contract` and `test_tier1_contract_key_set` exist as defined functions
- No top-level `body["reasoning_tier"]` / `body["confidence_score"]` accesses remain in tier tests
</verification>

<success_criteria>
- All 7 service-test inline migrations land in `tests/service/test_recommend.py`
- Two new contract tests (`test_openapi_wire_contract`, `test_tier1_contract_key_set`) exist and pass
- Full pytest suite passes
- WIRE-06 verified end-to-end (Pydantic → FastAPI → OpenAPI JSON response)
- Plan 03 unblocked: the meshek-side TypeScript update can now reference a stable, tested public shape
</success_criteria>

<output>
After completion, create `.planning/phases/phase-12-wire-contract/12-02-SUMMARY.md` documenting:
- Service test migration delta (7 line edits)
- The two new contract test functions added (with paths and what they pin)
- Full pytest suite output summary (test count, pass/fail)
- Confirmation that `grep -rn 'ProductRecommendation(.*quantity=' tests/ src/` returns 0 lines
</output>
