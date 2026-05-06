# Phase 5: Data Foundation - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a per-merchant SQLite storage layer and a Python data-access API that
the recommendation engine (Phase 6), Hebrew parser (Phase 7), and FastAPI
surface (Phase 8) will call. Scope is limited to: file layout, schema, a
`MerchantStore` class, and merchant profile CRUD. No HTTP, no ML, no parsing.

</domain>

<decisions>
## Implementation Decisions

### Storage Layout
- **D-01:** One SQLite file per merchant at `data/merchants/{merchant_id}.sqlite`. Filesystem-level isolation satisfies STOR-01 success criterion 1.
- **D-02:** The data root (`data/merchants/`) is configurable via a `MESHEK_DATA_DIR` environment variable, defaulting to the repo path. This unblocks Phase 8 Docker/Railway deployment where a mounted volume must be used instead of the repo tree.
- **D-03:** SQLite files are created lazily on the first profile write (`create_merchant(...)`). Readers error loudly when asked about an unknown merchant — lazy-create-on-read is forbidden because it would mask typos in `merchant_id`.

### Schema & Tables
- **D-04:** Sales table uses the canonical columns only: `date, merchant_id, product, quantity`. This matches `src/meshek_ml/forecasting/schema.py::REQUIRED_COLUMNS` exactly so stored rows flow unchanged into the existing forecasting pipeline. Price/unit/audit columns are deferred.
- **D-05:** Sales primary key is the composite `(date, product)`. Daily cadence means at most one row per product per day. Re-writes upsert (INSERT OR REPLACE) rather than append.
- **D-06:** Merchant profile lives in a `merchant_profile` table inside the same per-merchant SQLite file (one row, `merchant_id` as PK). Keeps a single file per merchant — no global registry DB.
- **D-07:** Schema evolution uses SQLite `PRAGMA user_version` plus ordered inline migration functions applied on connect. Stdlib only, no Alembic. v1.1 ships at `user_version = 1`.
- **D-08:** Storage layer enforces canonical schema with fail-fast errors on write, reusing (or matching the contract of) `SchemaValidationError` from `forecasting/schema.py`. Satisfies STOR-01 success criterion 4.

### Access API Shape
- **D-09:** Use the Python stdlib `sqlite3` module directly. No SQLAlchemy, no sqlmodel. Two tables do not justify an ORM, and the project values minimal dependencies.
- **D-10:** Expose a `MerchantStore(merchant_id)` class that owns the `sqlite3.Connection` and provides: `create_profile`, `get_profile`, `write_sales(df)`, `read_sales(start=None, end=None) -> DataFrame`. Class encapsulation makes connection lifecycle and mocking explicit.
- **D-11:** `read_sales` returns a `pandas.DataFrame`; `write_sales` accepts a `pandas.DataFrame` and validates it through the canonical schema path before insert. This keeps the storage layer plug-compatible with the existing forecasting pipeline.
- **D-12:** New module path: `src/meshek_ml/storage/merchant_store.py` (new `storage` subpackage). Tests mirror under `tests/storage/`.

### Profile Fields & ID
- **D-13:** `MerchantProfile` holds: `merchant_id` (PK, text), `name` (text, nullable), `timezone` (text, default `'Asia/Jerusalem'`), `language` (text, default `'he'`), `created_at` (ISO-8601 text, auto-set on insert).
- **D-14:** `merchant_id` is **caller-supplied**. The meshek app owns the canonical merchant identity; meshek-ml never invents IDs. `create_profile` rejects empty/whitespace IDs with a fail-fast error.
- **D-15:** Profile modeling uses a Pydantic `BaseModel` (Pydantic is already a project dep) for validation at the Python boundary, but persistence is raw SQL rows — no ORM mapping.

### Claude's Discretion
- Exact SQL statements, index choices beyond the `(date, product)` PK, connection pooling/reuse strategy, and error-class hierarchy.
- Whether to add an explicit `close()` / context-manager protocol on `MerchantStore` (recommended: yes, but details are planner's call).
- Test fixture strategy (tmp_path per test vs shared in-memory DB).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/PROJECT.md` — Milestone v1.1 scope and architectural split (meshek-ml is backend ML service only).
- `.planning/REQUIREMENTS.md` §Storage — STOR-01, STOR-02.
- `.planning/ROADMAP.md` §Phase 5 — Goal and success criteria for Data Foundation.

### Canonical Schema (MUST match)
- `src/meshek_ml/forecasting/schema.py` — `REQUIRED_COLUMNS = ["date", "merchant_id", "product", "quantity"]` and `SchemaValidationError`. The storage layer's write path must reuse this contract.

### Codebase Conventions
- `.planning/codebase/STACK.md` — Python 3.9+, stdlib preference, Pydantic available.
- `.planning/codebase/STRUCTURE.md` — `src/meshek_ml/` package layout; tests mirror under `tests/`.
- `.planning/codebase/CONVENTIONS.md` — Project coding/testing conventions.

### Deployment Context
- Future Phase 8 (`.planning/ROADMAP.md` §Phase 8) — Docker deployment informs the `MESHEK_DATA_DIR` env var decision (D-02).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/meshek_ml/forecasting/schema.py::validate_demand_schema` — call this on every `write_sales` DataFrame so storage fails fast with the same error class the pipeline already knows.
- `src/meshek_ml/forecasting/schema.py::REQUIRED_COLUMNS` — single source of truth for sales columns; import rather than duplicate.
- Pydantic is already in the stack — use `BaseModel` for `MerchantProfile` without adding a dep.

### Established Patterns
- Minimal-dependency stdlib-first policy (no ORM anywhere in the repo today).
- Pandas DataFrames are the lingua franca between pipeline stages; storage layer honors that contract on both read and write.
- Tests mirror source packages under `tests/<domain>/` — new `tests/storage/` module to be added.

### Integration Points
- Phase 6 `RecommendationEngine` will call `MerchantStore(merchant_id).read_sales()` to build its input DataFrame for LightGBM.
- Phase 7 Hebrew parser produces rows that Phase 8 `/sales` endpoint will feed into `MerchantStore.write_sales()`.
- Phase 8 FastAPI `lifespan` does not need to own DB connections — each request constructs a short-lived `MerchantStore`.

</code_context>

<specifics>
## Specific Ideas

- `data/merchants/{merchant_id}.sqlite` is the exact path convention.
- Default timezone is `'Asia/Jerusalem'`; default language is `'he'`.
- `user_version = 1` for the v1.1 schema baseline; migration functions added only when `user_version` bumps.
- Sales writes are upserts keyed on `(date, product)` — re-sending a day's record overwrites it, matching the merchant redo-the-day behavior.

</specifics>

<deferred>
## Deferred Ideas

- Price column in the sales table — PROJECT.md marks dynamic pricing as Out of Scope for v1.x.
- Unit column (kg/each/box) — tempting for Phase 7, but revisit there; not a v1.1 Phase 5 concern.
- Cross-merchant aggregate/pooled read path — Phase 6 Tier 2 (cross-merchant priors) will design this on top of whatever `MerchantStore` exposes; may become a separate `PooledStore` helper.
- Global product catalog table — belongs to Phase 7 parser, not Phase 5 storage.
- Async I/O / connection pooling — single-node FastAPI with short-lived connections is fine at v1.1 volumes.

</deferred>

---

*Phase: 05-data-foundation*
*Context gathered: 2026-04-13*
