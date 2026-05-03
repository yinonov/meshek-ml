---
phase: 10-fix-cloudrun-smoke-test
reviewed: 2026-04-16T00:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - tests/deploy/test_cloudrun_smoke.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-04-16
**Depth:** standard
**Files Reviewed:** 1
**Status:** issues_found

## Summary

`tests/deploy/test_cloudrun_smoke.py` is an env-guarded integration smoke test
for the live Cloud Run deployment. It follows the Phase 8 Docker smoke pattern
and is structurally sound. The guard logic, URL stripping, and JSON parsing
are all correct.

Three warnings are present: an uncaught `urllib.error.URLError` in `_post()`
that will surface as an unreadable stack trace on network failure or cold-start
timeout, a weak recommendation assertion that accepts an empty list (making the
smoke test miss a broken engine), and a missing assertion on the number of sales
rows accepted relative to what was sent.

Two info items cover an unconventional `date` import alias and a missing
`/health` preflight check.

---

## Warnings

### WR-01: `_post()` does not catch `urllib.error.URLError` — network errors surface as raw tracebacks

**File:** `tests/deploy/test_cloudrun_smoke.py:58-62`
**Issue:** `urllib.request.urlopen` raises `urllib.error.URLError` (a subclass of
`OSError`) for connection-level failures: DNS resolution failure, connection
refused, and — critically — timeout when the socket times out before an HTTP
response is received. The `except` clause in `_post()` only catches
`urllib.error.HTTPError` (a subclass of `URLError` that carries an HTTP status
code). A 60-second cold-start window makes a timeout plausible; when it fires
the test fails with an unguided `urllib.error.URLError: <urlopen error timed
out>` traceback rather than a clear assertion message pointing to which endpoint
failed.

**Fix:**
```python
    except urllib.error.URLError as exc:
        # URLError covers both HTTPError (4xx/5xx) and connection-level errors.
        detail = (
            exc.read().decode("utf-8", errors="replace")
            if isinstance(exc, urllib.error.HTTPError)
            else str(exc.reason)
        )
        code = exc.code if isinstance(exc, urllib.error.HTTPError) else "connection error"
        raise AssertionError(
            f"HTTP {code} from POST {url}: {detail}"
        ) from exc
```
Replace the current `except urllib.error.HTTPError` with the broader
`except urllib.error.URLError` clause above.

---

### WR-02: Smoke test accepts an empty `recommendations` list — a broken engine goes undetected

**File:** `tests/deploy/test_cloudrun_smoke.py:101-103`
**Issue:** After creating a merchant and posting two sales items, the test only
checks that `body["recommendations"]` is a list. An empty list satisfies this.
The `RecommendationEngine` has three tiers; if the engine falls back to
`category_default` or `pooled_prior` it should still produce at least one
recommendation for the two products just sold. An empty list signals a silent
engine failure but the smoke test passes anyway.

**Fix:**
```python
    assert isinstance(body["recommendations"], list), (
        f"recommendations not a list: {body['recommendations']!r}"
    )
    assert len(body["recommendations"]) >= 1, (
        f"expected at least one recommendation after posting sales, got empty list: {body!r}"
    )
```

---

### WR-03: `accepted_rows` is asserted `>= 1` but two items were sent — a partial-parse failure is silent

**File:** `tests/deploy/test_cloudrun_smoke.py:87-89`
**Issue:** The Hebrew text `"20 עגבניות, 5 מלפפונים"` contains two comma-separated
lines. The assertion only requires `accepted_rows >= 1`, meaning if the catalog
only recognises one product and silently skips the other, the smoke test still
passes. This masks catalog configuration drift on the deployed service. The
`skipped` list is checked to be a list but its length is never validated.

**Fix:**
```python
    assert body["accepted_rows"] == 2, (
        f"expected both sales lines accepted, got accepted_rows={body['accepted_rows']!r}, "
        f"skipped={body['skipped']!r}"
    )
    assert body["skipped"] == [], (
        f"expected no skipped lines, got: {body['skipped']!r}"
    )
```
If the catalog legitimately only knows one of these products, adjust the
assertion to `>= 1` with an explicit comment documenting the known partial
match, or use a product string guaranteed to be in the deployed catalog.

---

## Info

### IN-01: `date` imported with underscore alias `_date` — unconventional

**File:** `tests/deploy/test_cloudrun_smoke.py:32`
**Issue:** `from datetime import date as _date` uses the private-by-convention
`_` prefix, implying the symbol is module-private. The alias was likely chosen
to avoid shadowing a local variable named `date` in the test payload dict, but
there is no such local variable in the current code. The Docker smoke test
(`tests/service/test_docker_smoke.py`) does not import `date` at all. The alias
is harmless but may confuse future readers who expect `_` imports to be internal
helpers.

**Fix:**
```python
from datetime import date
# then: "date": date.today().isoformat(),
```
Or keep the alias with a brief inline comment:
```python
from datetime import date as _date  # alias avoids shadowing 'date' key in payload dicts
```

---

### IN-02: No `/health` preflight before exercising the full flow

**File:** `tests/deploy/test_cloudrun_smoke.py:69`
**Issue:** The Docker smoke test (`test_docker_smoke.py`) polls `/health` before
making business-logic requests, which gives a clear failure reason when the
service has not started (cold-start vs application error). The Cloud Run smoke
test jumps straight to `POST /merchants`. On a cold start the first request may
time out (60 s budget) with no indication of whether the service is up at all.
A `/health` GET preflight would distinguish "service not reachable" from
"merchants route broken".

**Fix:** Add a `_get_health()` call (or reuse the `_post` helper adapted for
GET) as the first assertion in `test_cloudrun_full_merchant_flow`:
```python
    # 0. Verify service is up before exercising business logic
    url = f"{_BASE_URL}/health"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
        assert resp.status in (200, 503), f"health check failed: {resp.status}"
```

---

_Reviewed: 2026-04-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
