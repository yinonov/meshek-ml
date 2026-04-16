# Phase 10: Fix Cloud Run Smoke Test — Research

**Researched:** 2026-04-16
**Domain:** Python test file correction — pytest, urllib, FastAPI route contract
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-03 | Service runs on Google Cloud Run in the `meshek-prod` GCP project with per-merchant SQLite files persisted via a GCS FUSE volume mount | The live service is already deployed and working. This phase closes the automated smoke test gap so INFRA-03 is verifiable without manual intervention. |
</phase_requirements>

---

## Summary

Phase 10 is a targeted bug fix to a single test file: `tests/deploy/test_cloudrun_smoke.py`. The file was written during Phase 8.1 to model the Docker smoke pattern, but it was written against a hypothetical path-per-merchant API shape (`/merchants/{id}/sales`) that never existed in the actual implementation. The real API (implemented in Phase 8) uses flat paths with `merchant_id` in the request body: `POST /sales` and `POST /recommend`.

There are exactly three bugs in the file:

1. **Wrong path for sales** — calls `POST /merchants/{merchant_id}/sales` (404) instead of `POST /sales` with `merchant_id` in the body.
2. **Wrong path for recommend** — calls `POST /merchants/{merchant_id}/recommend` (404) instead of `POST /recommend` with `merchant_id` in the body.
3. **Wrong response field assertion for sales** — asserts `"parsed" in body` (key does not exist) instead of `"accepted_rows" in body` and `"skipped" in body`.

No application code, infrastructure, or schemas need to change. This is purely a test-file correction.

**Primary recommendation:** Edit `tests/deploy/test_cloudrun_smoke.py` — fix the two URL paths and the one response field assertion. Run against the live Cloud Run URL with `MESHEK_CLOUDRUN_SMOKE=1` to confirm green.

---

## Standard Stack

### Core (already installed — no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | >=7.4 (project dep) | Test runner | Project standard |
| urllib.request | stdlib | HTTP calls in smoke test | Already used in test file; no extra deps for integration tests |

No new packages required. [VERIFIED: pyproject.toml `[project.optional-dependencies].dev`]

**Installation:** None needed.

---

## Architecture Patterns

### Actual API Shape (ground truth)

Source: `src/meshek_ml/service/routes/sales.py` line 30, `src/meshek_ml/service/routes/recommend.py` line 24, `src/meshek_ml/service/routes/merchants.py` line 27. [VERIFIED: codebase read]

```
POST /merchants           body: {}                          → 201, {merchant_id, ...}
POST /sales               body: {merchant_id, date, text}  → 200, {accepted_rows, skipped}
POST /recommend           body: {merchant_id}               → 200, {recommendations, ...}
```

### What the smoke test currently does (bugs)

```
POST /merchants                           → 201  ✓ correct
POST /merchants/{merchant_id}/sales       → 404  ✗ wrong path
  asserts "parsed" in body               → KeyError ✗ wrong field
POST /merchants/{merchant_id}/recommend   → 404  ✗ wrong path
```

### Correct POST /sales Payload

From `SalesRequest` schema (`src/meshek_ml/service/schemas.py` lines 80–100): [VERIFIED: codebase read]

```python
{
    "merchant_id": merchant_id,   # MerchantIdStr — required
    "date": "2026-04-16",         # ISO date string — required
    "text": "20 עגבניות, 5 מלפפונים"  # Hebrew free text — must supply text XOR items
}
```

`date` is a required field — the current smoke test omits it (calls `POST /merchants/{id}/sales` with only `{"text": ...}`). The fix must add `date` to the payload. [VERIFIED: SalesRequest model_validator requires exactly one of items/text; date is a non-optional field with no default]

### Correct POST /sales Response Assertions

From `SalesResponse` schema (`src/meshek_ml/service/schemas.py` lines 103–108): [VERIFIED: codebase read]

```python
assert "accepted_rows" in body
assert isinstance(body["accepted_rows"], int) and body["accepted_rows"] >= 0
assert "skipped" in body
assert isinstance(body["skipped"], list)
```

### Correct POST /recommend Payload

From `RecommendRequest` schema (`src/meshek_ml/service/schemas.py` lines 115–122): [VERIFIED: codebase read]

```python
{"merchant_id": merchant_id}
```

### Correct POST /recommend Response Assertions

From `RecommendationResponse` — source is `src/meshek_ml/recommendation/schema.py` (not read, but smoke test only checks `"recommendations" in body`). The existing assertion on line 89–91 of the smoke test is correct:

```python
assert "recommendations" in body
assert isinstance(body["recommendations"], list)
```

No change needed to the recommend response assertions. [VERIFIED: current test lines 88–94 already correct for the response shape]

### Full Corrected Test Flow

```python
# 1. Create merchant — unchanged
status, body = _post("/merchants", {})
assert status == 201
merchant_id = body.get("merchant_id")

# 2. Post Hebrew sales — FIXED path, FIXED payload, FIXED assertions
status, body = _post(
    "/sales",
    {
        "merchant_id": merchant_id,
        "date": date.today().isoformat(),   # was missing
        "text": "20 עגבניות, 5 מלפפונים",
    },
)
assert status == 200
assert "accepted_rows" in body              # was: "parsed"
assert isinstance(body["accepted_rows"], int) and body["accepted_rows"] >= 0

# 3. Get recommendations — FIXED path, FIXED payload
status, body = _post("/recommend", {"merchant_id": merchant_id})  # was /merchants/{id}/recommend
assert status == 200
assert "recommendations" in body            # unchanged — already correct
assert isinstance(body["recommendations"], list)
```

### Import Change Required

The fix adds use of `date.today()`. The standard library `datetime.date` must be imported:

```python
from datetime import date
```

[ASSUMED: current imports in test file do not include `datetime.date` — verified by reading the file: imports are `json`, `os`, `urllib.error`, `urllib.request`, `pytest`]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Date string for request | Manual string literal `"2026-04-16"` | `date.today().isoformat()` | Smoke test should not embed a hardcoded date that ages out |

---

## Common Pitfalls

### Pitfall 1: Missing `date` Field in Sales Payload
**What goes wrong:** `SalesRequest` has `date: date` with no default — Pydantic raises 422 Unprocessable Entity.
**Why it happens:** The current smoke test omits `date` because it was targeting a path-based route that didn't exist, so no one noticed the body was incomplete.
**How to avoid:** Add `"date": date.today().isoformat()` to the `_post("/sales", {...})` call.
**Warning signs:** `422` response code instead of `200` when running the corrected smoke test.

### Pitfall 2: Asserting `accepted_rows >= 1` Instead of `>= 0`
**What goes wrong:** The sales route returns `accepted_rows == 0` if MerchantStore returns 0 rows written (possible if the product is unrecognised).
**Why it happens:** Hebrew text "20 עגבניות, 5 מלפפונים" should parse correctly via the Phase 7 catalog. But if it doesn't, `accepted_rows` would be 0 and all lines would go to `skipped`.
**How to avoid:** Assert `>= 0` for robustness, or assert `>= 1` only if you're confident the catalog contains these product names. The Phase 7 catalog has been verified to contain עגבניות (tomatoes) and מלפפונים (cucumbers) — asserting `>= 1` is safe and more meaningful.
**Warning signs:** `422` (all lines failed) means catalog lookup failed or merchant doesn't exist.

### Pitfall 3: `merchant_id` Format from `/merchants`
**What goes wrong:** `uuid.uuid4().hex` returns 32-char lowercase hex — valid against `MerchantIdStr` regex `^[A-Za-z0-9_-]{1,64}$`. No issue here.
**How to avoid:** No change needed — smoke test already correctly extracts `merchant_id` from the `/merchants` response.

### Pitfall 4: Test Skipped When Env Vars Unset
**What goes wrong:** Reporting the test "passed" when it was actually skipped.
**Why it happens:** `_SMOKE_ENABLED` guard at module level means any `pytest` run without both `MESHEK_CLOUDRUN_SMOKE=1` AND `MESHEK_CLOUDRUN_URL` will skip silently.
**How to avoid:** The phase success criterion requires running with both env vars set against the live Cloud Run URL. CI must not claim green from a skip.

---

## Code Examples

### Corrected `test_cloudrun_full_merchant_flow` function

```python
# Source: derived from actual API schemas in src/meshek_ml/service/schemas.py
# and src/meshek_ml/service/routes/{sales,recommend}.py
from datetime import date as _date

@pytest.mark.skipif(
    not _SMOKE_ENABLED,
    reason="Cloud Run smoke disabled (set MESHEK_CLOUDRUN_SMOKE=1 + MESHEK_CLOUDRUN_URL)",
)
def test_cloudrun_full_merchant_flow():
    # 1. Create merchant
    status, body = _post("/merchants", {})
    assert status == 201, f"expected 201 Created, got {status}: {body}"
    merchant_id = body.get("merchant_id")
    assert isinstance(merchant_id, str) and merchant_id, f"missing merchant_id: {body}"

    # 2. Post Hebrew sales line
    status, body = _post(
        "/sales",
        {
            "merchant_id": merchant_id,
            "date": _date.today().isoformat(),
            "text": "20 עגבניות, 5 מלפפונים",
        },
    )
    assert status == 200, f"expected 200 OK from /sales, got {status}: {body}"
    assert "accepted_rows" in body, f"sales response missing 'accepted_rows': {body}"
    assert isinstance(body["accepted_rows"], int) and body["accepted_rows"] >= 1, (
        f"expected accepted_rows >= 1, got {body['accepted_rows']!r}"
    )

    # 3. Get recommendations
    status, body = _post("/recommend", {"merchant_id": merchant_id})
    assert status == 200, f"expected 200 OK from /recommend, got {status}: {body}"
    assert "recommendations" in body, (
        f"recommend response missing 'recommendations': {body}"
    )
    assert isinstance(body["recommendations"], list), (
        f"recommendations not a list: {body['recommendations']!r}"
    )
```

---

## State of the Art

| Old (broken) | Correct | Notes |
|---|---|---|
| `POST /merchants/{id}/sales` | `POST /sales` with `merchant_id` in body | Phase 8 API design decision |
| `POST /merchants/{id}/recommend` | `POST /recommend` with `merchant_id` in body | Phase 8 API design decision |
| Assert `"parsed" in body` | Assert `"accepted_rows" in body` | `SalesResponse` schema, Phase 8 |
| No `date` in sales body | `"date": date.today().isoformat()` | `SalesRequest.date` is required |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `date` is not in the current smoke test's sales payload | Common Pitfalls / Code Examples | Low — verified by reading test file: payload is `{"text": "..."}` only |
| A2 | `datetime.date` is not currently imported in the smoke test | Code Examples | Low — verified by reading test file imports: `json, os, urllib.error, urllib.request, pytest` |
| A3 | `accepted_rows >= 1` is safe because עגבניות and מלפפונים are in Phase 7 catalog | Code Examples | Low — Phase 7 was verified in VERIFICATION.md; these are the canonical test products |

**All assumptions are LOW risk and grounded in codebase reading.**

---

## Open Questions

None. The delta between current test behavior and correct behavior is fully characterized by reading the test file and the actual route implementations.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pytest | Test runner | ✓ | >=7.4 (pyproject.toml) | — |
| Live Cloud Run URL | INFRA-03 verification | Not verified here (external) | — | Phase already deployed per Phase 8.1 VERIFICATION |
| `gcloud` CLI | Get Cloud Run URL | Not checked | — | URL can be retrieved from GCP Console or from Phase 8.1 notes |

**Missing dependencies with no fallback:** None for the fix itself.

**For running the smoke test:** Requires `MESHEK_CLOUDRUN_URL` to be set to the live Cloud Run service URL. This value is available from `gcloud run services describe meshek-ml --region me-west1 --format='value(status.url)'` — as documented in the test file's docstring. The service is live per Phase 8.1 and Phase 9 verification.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >=7.4 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/deploy/test_cloudrun_smoke.py -x -v -m integration` (skips without env vars) |
| Full run command | `MESHEK_CLOUDRUN_SMOKE=1 MESHEK_CLOUDRUN_URL="<url>" uv run pytest tests/deploy/test_cloudrun_smoke.py -x -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-03 | Cloud Run smoke test passes against live service | integration/e2e | `MESHEK_CLOUDRUN_SMOKE=1 MESHEK_CLOUDRUN_URL="..." uv run pytest tests/deploy/test_cloudrun_smoke.py -x -v` | ✅ (needs fix) |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/deploy/ -v` (will skip unless env vars set; confirms no syntax errors)
- **Phase gate:** Full smoke run with live URL before `/gsd-verify-work`

### Wave 0 Gaps

None — `tests/deploy/test_cloudrun_smoke.py` already exists. This phase edits it, not creates it.

---

## Security Domain

No new security surface. This phase edits a test file only. The `MESHEK_CLOUDRUN_URL` env var is already documented in the test file and is a read-only config value (no secrets exposure). Existing threats T-5-01 through T-8-10 are unaffected.

---

## Sources

### Primary (HIGH confidence)
- `tests/deploy/test_cloudrun_smoke.py` — current broken test, read directly [VERIFIED]
- `src/meshek_ml/service/routes/sales.py` — actual `POST /sales` route definition [VERIFIED]
- `src/meshek_ml/service/routes/recommend.py` — actual `POST /recommend` route definition [VERIFIED]
- `src/meshek_ml/service/routes/merchants.py` — actual `POST /merchants` route definition [VERIFIED]
- `src/meshek_ml/service/schemas.py` — `SalesRequest`, `SalesResponse`, `RecommendRequest` schemas [VERIFIED]
- `.planning/v1.1-MILESTONE-AUDIT.md` — audit finding identifying the exact bugs [VERIFIED]

### Secondary (MEDIUM confidence)
- `pyproject.toml` — pytest version, markers, test paths [VERIFIED]

---

## Metadata

**Confidence breakdown:**
- What's broken: HIGH — audit document and direct code reading confirm all three bugs
- Fix approach: HIGH — directly derived from actual route implementations
- Test execution: HIGH — env-guard pattern already in place, no new infrastructure needed

**Research date:** 2026-04-16
**Valid until:** Stable — this is a pure Python test file fix with no external dependencies that could change
