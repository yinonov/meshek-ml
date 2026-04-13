# Phase 5: Data Foundation - Research

**Researched:** 2026-04-13
**Domain:** Per-merchant SQLite storage layer (stdlib `sqlite3` + pandas + Pydantic v2)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from 05-CONTEXT.md)

### Locked Decisions
- **D-01:** One SQLite file per merchant at `data/merchants/{merchant_id}.sqlite` (filesystem-level isolation → satisfies STOR-01 #1).
- **D-02:** Data root configurable via `MESHEK_DATA_DIR` env var, defaulting to repo-local `data/merchants/`.
- **D-03:** SQLite files created lazily on first profile write (`create_profile(...)`). Readers MUST error loudly on unknown merchant — no lazy-create-on-read.
- **D-04:** Sales table uses canonical columns only: `date, merchant_id, product, quantity`. Matches `forecasting/schema.py::REQUIRED_COLUMNS` exactly.
- **D-05:** Sales PK = composite `(date, product)`. Re-writes upsert (overwrite), not append.
- **D-06:** `merchant_profile` table lives inside the same per-merchant SQLite file (one row, `merchant_id` PK). No global registry DB.
- **D-07:** Schema evolution via SQLite `PRAGMA user_version` + ordered inline migration functions. Stdlib only. v1.1 ships at `user_version = 1`.
- **D-08:** Write path fails fast; reuse `SchemaValidationError` contract from `forecasting/schema.py`.
- **D-09:** Stdlib `sqlite3` only. No SQLAlchemy, no sqlmodel.
- **D-10:** `MerchantStore(merchant_id)` class owns the `sqlite3.Connection` and exposes: `create_profile`, `get_profile`, `write_sales(df)`, `read_sales(start=None, end=None) -> DataFrame`.
- **D-11:** `read_sales` returns `pd.DataFrame`; `write_sales` accepts `pd.DataFrame` and validates through canonical schema before insert.
- **D-12:** New module `src/meshek_ml/storage/merchant_store.py`; tests under `tests/storage/`.
- **D-13:** `MerchantProfile` fields: `merchant_id` (PK, text), `name` (text, nullable), `timezone` (text, default `'Asia/Jerusalem'`), `language` (text, default `'he'`), `created_at` (ISO-8601 text, auto-set on insert).
- **D-14:** `merchant_id` caller-supplied. Reject empty/whitespace with fail-fast error. meshek-ml never invents IDs.
- **D-15:** `MerchantProfile` uses Pydantic `BaseModel` for boundary validation; persistence is raw SQL — no ORM mapping.

### Claude's Discretion
- Exact SQL statements, index choices beyond the `(date, product)` PK.
- Connection pooling/reuse strategy.
- Error-class hierarchy beneath the re-used `SchemaValidationError` contract.
- Explicit `close()` / context-manager protocol on `MerchantStore` (recommended: yes).
- Test fixture strategy (`tmp_path` per test vs shared in-memory DB).

### Deferred Ideas (OUT OF SCOPE)
- Price column in sales table (dynamic pricing OoS for v1.x).
- Unit column (kg/each/box) — revisit in Phase 7.
- Cross-merchant pooled read path — Phase 6 Tier 2 concern.
- Global product catalog table — Phase 7 parser concern.
- Async I/O / connection pooling — fine at v1.1 volumes.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STOR-01 | Sales history is persisted per-merchant in isolated SQLite files | Filesystem isolation via `{merchant_id}.sqlite` (D-01); canonical-schema enforcement via reused `validate_demand_schema`; upsert semantics via `INSERT … ON CONFLICT DO UPDATE` keyed on `(date, product)` |
| STOR-02 | Merchant profiles are created and retrievable | `merchant_profile` single-row table inside per-merchant DB; `create_profile`/`get_profile` on `MerchantStore`; Pydantic `MerchantProfile` for boundary validation; zero-config defaults (timezone `Asia/Jerusalem`, language `he`) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

No `./CLAUDE.md` exists at project root. Global `~/.claude/CLAUDE.md` is present and mandates automated self-verification; this phase has no UI, so verification here = running the test suite, not browser automation.

## Summary

This phase is a small, well-scoped storage layer. The ecosystem has a stable, boring answer for every open question: Python stdlib `sqlite3` is sufficient; Pydantic v2 is already installed; `PRAGMA user_version` is the canonical migration mechanism when you don't want Alembic; `INSERT … ON CONFLICT DO UPDATE` (SQLite 3.24+, shipping since 2018) is the idiomatic upsert; pandas `read_sql_query` with `parse_dates=["date"]` round-trips dates cleanly.

The only non-trivial risk is **path traversal via `merchant_id`** — because `merchant_id` is caller-supplied (D-14) and interpolated into a filesystem path (D-01), a malicious caller could write outside `data/merchants/`. Mitigation is a strict whitelist regex on the ID plus `Path.resolve()` parent check. SQL injection is trivially avoided by parameterized queries (`?` placeholders). There are no thread-safety surprises if each `MerchantStore` is short-lived per request (D-11, D-12 in Phase 8 context) — this is explicitly the recommended SQLite + FastAPI pattern.

**Primary recommendation:** Implement `MerchantStore` as a context-managed class (`__enter__`/`__exit__`), open the connection eagerly in `__init__` with `check_same_thread=True` (default) and `detect_types=PARSE_DECLTYPES`, run migrations on connect via a small ordered `_MIGRATIONS` list, use `INSERT … ON CONFLICT(date,product) DO UPDATE` for upserts, use `pd.read_sql_query(..., parse_dates=["date"])` for reads, and validate `merchant_id` with a `^[A-Za-z0-9_-]{1,64}$` regex before any filesystem touch.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sqlite3` (stdlib) | Python 3.13 ships SQLite 3.50.2 [VERIFIED: `python -c 'import sqlite3; print(sqlite3.sqlite_version)'` → 3.50.2] | DB driver | Stdlib, zero deps, D-09 locked |
| `pandas` | 2.3.3 installed [VERIFIED: venv probe] | DataFrame I/O (`to_sql`, `read_sql_query`) | Already project dep, D-11 locked |
| `pydantic` | 2.12.5 installed [VERIFIED: venv probe] | `MerchantProfile` boundary validation | Already project dep, D-15 locked |
| `pytest` / `pytest-cov` | declared in `pyproject.toml` [VERIFIED: STACK.md §Development] | Test runner | Repo standard |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pathlib.Path` (stdlib) | — | Filesystem path construction + `.resolve()` parent check | Every path operation; never use string concat |
| `os` (stdlib) | — | `os.environ.get("MESHEK_DATA_DIR", ...)` for D-02 | Single lookup at module import or class construction |
| `re` (stdlib) | — | `merchant_id` whitelist validation | Reject invalid IDs before touching filesystem |
| `datetime` (stdlib) | — | `datetime.now(timezone.utc).isoformat()` for `created_at` | Profile insert |

### Alternatives Considered (and rejected)

| Instead of | Could Use | Rejected Because |
|------------|-----------|------------------|
| stdlib `sqlite3` | SQLAlchemy Core / sqlmodel | D-09 locks stdlib-only; two tables don't justify ORM overhead |
| `PRAGMA user_version` migrations | Alembic, yoyo-migrations | D-07 locks stdlib-only; Alembic needs SQLAlchemy metadata |
| `df.to_sql(..., if_exists="append")` | Raw `executemany` loop | `to_sql` does not emit `ON CONFLICT` — upsert (D-05) requires explicit cursor; see Pattern 3 below |
| `INSERT OR REPLACE` | `INSERT … ON CONFLICT DO UPDATE` | `OR REPLACE` deletes + re-inserts rows, which re-triggers FKs, re-fires triggers, and breaks rowid stability. `ON CONFLICT … DO UPDATE` is an in-place update. [CITED: sqlite.org/lang_upsert.html] |
| `merchant_id` as `INTEGER` surrogate | Trust caller-supplied text | D-14 locks caller-supplied; meshek app owns identity |

**Installation:** No new deps. Everything is stdlib or already in `pyproject.toml`.

**Version verification:**
- `sqlite3` C library: 3.50.2 (via `python -c "import sqlite3; print(sqlite3.sqlite_version)"`) [VERIFIED in venv]
- `ON CONFLICT` UPSERT syntax: available since SQLite **3.24.0** (released 2018-06-04) [CITED: sqlite.org/lang_upsert.html]. We are 26 minor versions ahead — no compatibility concern.
- `pandas.DataFrame.to_sql` + `pd.read_sql_query`: stable since pandas 1.x; `parse_dates` kwarg well established [CITED: pandas.pydata.org/docs/reference/api/pandas.read_sql_query.html]

## Architecture Patterns

### Recommended Project Structure

```
src/meshek_ml/
├── storage/                        # NEW subpackage
│   ├── __init__.py                 # re-export MerchantStore, MerchantProfile, errors
│   ├── merchant_store.py           # MerchantStore class, migrations, path helpers
│   └── profile.py                  # Pydantic MerchantProfile model (optional split)
tests/
└── storage/                        # NEW
    ├── __init__.py
    ├── conftest.py                 # tmp_path fixture returning a MerchantStore factory
    ├── test_merchant_store.py      # CRUD + isolation + upsert + schema-fail-fast
    ├── test_migrations.py          # user_version bump + idempotent re-open
    └── test_path_safety.py         # merchant_id whitelist / path-traversal rejection
```

Rationale: `storage/` mirrors existing domain split (`simulation/`, `forecasting/`, `optimization/`) per STRUCTURE.md §Module Grouping. Keeping `profile.py` separate from `merchant_store.py` is optional; if the Pydantic model stays small (~15 lines), inlining is fine.

### Pattern 1: `MerchantStore` class skeleton

**What:** Context-managed class that owns a single `sqlite3.Connection` for the lifetime of one merchant operation.
**When:** Every read or write — callers do `with MerchantStore(merchant_id) as store: ...`. Phase 8 FastAPI endpoints construct one per request (per CONTEXT.md "short-lived stores" note).

```python
# src/meshek_ml/storage/merchant_store.py
from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, Field

from meshek_ml.forecasting.schema import (
    REQUIRED_COLUMNS,
    SchemaValidationError,
    validate_demand_schema,
)

_MERCHANT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_SCHEMA_VERSION = 1


class MerchantStoreError(RuntimeError):
    """Base class for storage errors (not a ValueError — distinct from schema errors)."""


class UnknownMerchantError(MerchantStoreError):
    """Raised when reader is asked about a merchant whose file does not exist (D-03)."""


class InvalidMerchantIdError(MerchantStoreError):
    """Raised when merchant_id fails whitelist validation (D-14 + path-traversal guard)."""


class MerchantProfile(BaseModel):
    merchant_id: str
    name: str | None = None
    timezone: str = "Asia/Jerusalem"
    language: str = "he"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def _data_root() -> Path:
    return Path(os.environ.get("MESHEK_DATA_DIR", "data/merchants")).resolve()


def _validate_merchant_id(merchant_id: str) -> str:
    if not merchant_id or not merchant_id.strip():
        raise InvalidMerchantIdError("merchant_id must not be empty or whitespace")
    if not _MERCHANT_ID_PATTERN.match(merchant_id):
        raise InvalidMerchantIdError(
            f"merchant_id {merchant_id!r} must match {_MERCHANT_ID_PATTERN.pattern}"
        )
    return merchant_id


def _merchant_path(merchant_id: str) -> Path:
    root = _data_root()
    candidate = (root / f"{merchant_id}.sqlite").resolve()
    # Defense in depth: even after regex, confirm we stayed under root.
    if root not in candidate.parents and candidate.parent != root:
        raise InvalidMerchantIdError(
            f"merchant_id {merchant_id!r} resolves outside data root"
        )
    return candidate


class MerchantStore:
    def __init__(self, merchant_id: str, *, must_exist: bool = False) -> None:
        self.merchant_id = _validate_merchant_id(merchant_id)
        self._path = _merchant_path(self.merchant_id)
        if must_exist and not self._path.exists():
            raise UnknownMerchantError(f"No store for merchant {merchant_id!r}")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(self._path),
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")  # safer concurrent reads
        _apply_migrations(self._conn)

    def __enter__(self) -> "MerchantStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None  # type: ignore[assignment]

    # --- profile (STOR-02) ---
    def create_profile(self, profile: MerchantProfile) -> MerchantProfile:
        if profile.merchant_id != self.merchant_id:
            raise InvalidMerchantIdError("profile.merchant_id mismatches store")
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO merchant_profile
                    (merchant_id, name, timezone, language, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    profile.merchant_id,
                    profile.name,
                    profile.timezone,
                    profile.language,
                    profile.created_at,
                ),
            )
        return profile

    def get_profile(self) -> MerchantProfile | None:
        row = self._conn.execute(
            "SELECT merchant_id, name, timezone, language, created_at "
            "FROM merchant_profile WHERE merchant_id = ?",
            (self.merchant_id,),
        ).fetchone()
        if row is None:
            return None
        return MerchantProfile(
            merchant_id=row[0],
            name=row[1],
            timezone=row[2],
            language=row[3],
            created_at=row[4],
        )

    # --- sales (STOR-01) ---
    def write_sales(self, df: pd.DataFrame) -> int:
        df = validate_demand_schema(df)  # fail-fast per D-08
        foreign = df.loc[df["merchant_id"] != self.merchant_id, "merchant_id"].unique()
        if len(foreign):
            raise SchemaValidationError(
                f"write_sales received foreign merchant_id(s): {list(foreign)}"
            )
        rows = [
            (
                row.date.to_pydatetime().date().isoformat(),
                self.merchant_id,
                str(row.product),
                float(row.quantity),
            )
            for row in df.itertuples(index=False)
        ]
        with self._conn:
            self._conn.executemany(
                """
                INSERT INTO sales (date, merchant_id, product, quantity)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(date, product) DO UPDATE SET
                    quantity = excluded.quantity,
                    merchant_id = excluded.merchant_id
                """,
                rows,
            )
        return len(rows)

    def read_sales(
        self,
        start: str | pd.Timestamp | None = None,
        end: str | pd.Timestamp | None = None,
    ) -> pd.DataFrame:
        query = "SELECT date, merchant_id, product, quantity FROM sales"
        params: list[str] = []
        clauses: list[str] = []
        if start is not None:
            clauses.append("date >= ?")
            params.append(pd.Timestamp(start).date().isoformat())
        if end is not None:
            clauses.append("date <= ?")
            params.append(pd.Timestamp(end).date().isoformat())
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY date, product"
        df = pd.read_sql_query(
            query,
            self._conn,
            params=params,
            parse_dates=["date"],
        )
        # Ensure canonical column order + dtype alignment
        return df[REQUIRED_COLUMNS]
```

### Pattern 2: `PRAGMA user_version` migrations (D-07)

**What:** Ordered list of `(version, callable)` applied on connect. Each migration bumps `user_version`. Idempotent — re-opening a current DB runs zero migrations.

```python
def _migration_001_initial(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS merchant_profile (
            merchant_id TEXT PRIMARY KEY NOT NULL,
            name        TEXT,
            timezone    TEXT NOT NULL DEFAULT 'Asia/Jerusalem',
            language    TEXT NOT NULL DEFAULT 'he',
            created_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sales (
            date        TEXT NOT NULL,
            merchant_id TEXT NOT NULL,
            product     TEXT NOT NULL,
            quantity    REAL NOT NULL,
            PRIMARY KEY (date, product)
        );

        CREATE INDEX IF NOT EXISTS idx_sales_product ON sales(product);
        """
    )


_MIGRATIONS: list[tuple[int, callable]] = [
    (1, _migration_001_initial),
    # (2, _migration_002_add_unit_column),  # future
]


def _apply_migrations(conn: sqlite3.Connection) -> None:
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    for target_version, fn in _MIGRATIONS:
        if current < target_version:
            with conn:  # implicit BEGIN/COMMIT, rolls back on exception
                fn(conn)
                conn.execute(f"PRAGMA user_version = {target_version}")
            current = target_version
```

**Why this shape:** `PRAGMA user_version` is a 32-bit integer slot SQLite reserves for application use; no separate `schema_version` table needed. `with conn:` wraps each migration in a transaction so partial failures roll back. [CITED: sqlite.org/pragma.html#pragma_user_version]

### Pattern 3: UPSERT trade-offs

**Chosen:** `INSERT … ON CONFLICT(date, product) DO UPDATE SET quantity = excluded.quantity`.

| Dimension | `INSERT OR REPLACE` | `ON CONFLICT DO UPDATE` |
|-----------|---------------------|-------------------------|
| Mechanism | DELETE conflicting row, INSERT new row | UPDATE conflicting row in place |
| Triggers | Fires DELETE + INSERT triggers | Fires UPDATE trigger only |
| rowid | Changes (new row) | Stable |
| FKs with CASCADE | Cascades deletes — can nuke related rows | Does not |
| Partial updates | Must re-supply every column | Can target subset (`SET quantity = excluded.quantity`) |
| SQLite version | Since forever | Since 3.24.0 (2018) [CITED: sqlite.org/lang_upsert.html] |

For our use case (no FKs, no triggers) both *work*, but `ON CONFLICT DO UPDATE` is the current SQLite idiom and future-proof if we ever add a trigger or a surrogate rowid column.

### Pattern 4: pandas ↔ sqlite3 round-trip and type fidelity

**Write path:** **Do not** use `df.to_sql(..., if_exists="append")` because it emits plain `INSERT` and cannot express `ON CONFLICT DO UPDATE`. Use explicit `cursor.executemany()` after validation (see Pattern 1 `write_sales`).

**Read path:** Use `pd.read_sql_query(query, conn, params=..., parse_dates=["date"])`. Without `parse_dates`, the `date` column comes back as Python `str` (because we stored it as TEXT ISO-8601). With `parse_dates=["date"]`, pandas converts it to `datetime64[ns]` — the same dtype `validate_demand_schema` produces. [CITED: pandas.pydata.org/docs/reference/api/pandas.read_sql_query.html]

**Date storage format:** ISO-8601 `YYYY-MM-DD` as TEXT. SQLite has no native DATE type; the official docs recommend TEXT in ISO-8601, REAL as Julian day, or INTEGER as Unix time. TEXT ISO-8601 is the only one that sorts lexicographically matching chronological order and is human-readable in `sqlite3` CLI debugging. [CITED: sqlite.org/datatype3.html §2.2 Date and Time Datatype]

### Pattern 5: Connection lifecycle & thread-safety (Phase 8 concern)

**Default:** `sqlite3.connect()` sets `check_same_thread=True`, meaning a connection can only be used from the thread that created it. This is the correct default for FastAPI: each request handler constructs its own `MerchantStore`, uses it, and closes it. Do not share `MerchantStore` across threads or request boundaries. [CITED: docs.python.org/3/library/sqlite3.html#sqlite3.connect]

**WAL mode:** `PRAGMA journal_mode = WAL` allows one writer concurrent with many readers — relevant if Phase 8 runs multiple uvicorn workers against the same merchant file. Trade-off: creates `-wal` and `-shm` sidecar files next to the DB. [CITED: sqlite.org/wal.html]

**Do NOT** introduce a connection pool. At v1.1 volumes (one merchant per request, tens to low-hundreds of requests/day per the PROJECT.md merchant context), the per-request open/close cost (<1 ms) is invisible.

### Anti-Patterns to Avoid

- **String-formatting `merchant_id` into SQL.** Always use `?` parameter placeholders. SQL injection is otherwise trivial.
- **String-concatenating `merchant_id` into file paths without regex.** Even with `Path()`, a `merchant_id` of `"../../etc/passwd"` becomes a real path. Regex-first is mandatory.
- **Using `df.to_sql(if_exists="append")` for sales.** Silently appends duplicates on re-submit — breaks D-05 upsert semantic.
- **Lazy-create-on-read.** Explicitly forbidden by D-03. Readers pass `must_exist=True`.
- **Sharing one long-lived `Connection` across requests.** Breaks `check_same_thread`; hides transaction-leak bugs.
- **Storing `date` as REAL/INTEGER.** TEXT ISO-8601 is what SQLite docs recommend and what pandas round-trips cleanly.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Schema validation | Custom column checker | Reuse `validate_demand_schema` from `forecasting/schema.py` | Single source of truth; already tested; error class already known downstream (D-08) |
| Profile dict validation | `if "name" not in d: raise …` | Pydantic `BaseModel` (D-15) | Handles defaults, types, serialization, error messages for free |
| Schema versioning | `meta_version` table | `PRAGMA user_version` | SQLite reserves an integer slot for exactly this use case |
| Upsert | `SELECT … then INSERT or UPDATE` | `INSERT … ON CONFLICT DO UPDATE` | Atomic, one round-trip, idiomatic, avoids race conditions |
| DataFrame → rows | Custom serializer | `df.itertuples(index=False)` + `executemany` | Stdlib; type-coerce at the boundary (`.date().isoformat()`, `float(...)`) |
| Env-var parsing | Custom `.env` reader | `os.environ.get("MESHEK_DATA_DIR", default)` | One variable, no need for `python-dotenv` |
| File-path safety | Custom traversal checker | Regex whitelist + `Path.resolve()` + parent check | Two independent defenses; both stdlib |

**Key insight:** every piece of this phase has a boring, correct stdlib/existing-dep answer. Resisting the temptation to bring in Alembic or SQLAlchemy is the main design discipline.

## Common Pitfalls

### Pitfall 1: Date dtype drift on round-trip
**What goes wrong:** `write_sales(df)` stores `date` as TEXT; `read_sales()` returns a DataFrame whose `date` column is `object` dtype (strings), not `datetime64[ns]`. Downstream forecasting code fails with a cryptic "can't compare str and Timestamp".
**Why:** SQLite stores dates as TEXT; pandas `read_sql_query` does not auto-parse dates unless told to.
**How to avoid:** Always pass `parse_dates=["date"]` to `read_sql_query` (see Pattern 4). Add a test that asserts `df["date"].dtype == "datetime64[ns]"` after a round-trip.
**Warning sign:** Phase 6 recommendation engine test fails with `TypeError: '<=' not supported between instances of 'str' and 'Timestamp'`.

### Pitfall 2: `merchant_id` path traversal (CRITICAL)
**What goes wrong:** Caller passes `merchant_id = "../../../etc/passwd"`. `Path(root / f"{merchant_id}.sqlite")` resolves outside `data/merchants/`. `sqlite3.connect` happily creates a file wherever it lands.
**Why:** `merchant_id` is caller-supplied (D-14) and directly interpolated into a filesystem path (D-01). The meshek app trust boundary ends at the HTTP request.
**How to avoid:** Two defenses in depth (see `_validate_merchant_id` + `_merchant_path` in Pattern 1):
1. Regex whitelist `^[A-Za-z0-9_-]{1,64}$` — rejects `/`, `.`, `\`, unicode.
2. After `Path.resolve()`, verify the resolved path's parent is the data root.
**Warning sign:** Any file created outside `data/merchants/` during tests. Add a test that asserts `InvalidMerchantIdError` for `"../evil"`, `"a/b"`, `"a\x00b"`, `""`, `"   "`.

### Pitfall 3: `PRAGMA user_version` vs `PRAGMA schema_version` confusion
**What goes wrong:** Developer uses `PRAGMA schema_version` thinking it's the app slot. That pragma is SQLite's internal counter for cache invalidation and mutating it corrupts the DB.
**Why:** Confusing name pair in SQLite.
**How to avoid:** Only ever read/write `user_version`. Comment in the migration module pointing at this pitfall.
**Warning sign:** Migrations run on every connect because the slot never persists.

### Pitfall 4: `INSERT OR REPLACE` breaks rowid and fires unwanted triggers
**What goes wrong:** Future Phase 6 adds a trigger or a FK, and sales re-writes start cascading unexpectedly.
**Why:** `INSERT OR REPLACE` is DELETE+INSERT under the hood.
**How to avoid:** Use `ON CONFLICT DO UPDATE` from day one (see Pattern 3).

### Pitfall 5: Transaction not committed
**What goes wrong:** Python's DB-API `sqlite3` module starts an implicit transaction on the first DML statement and only commits on `conn.commit()`. Writes appear to succeed but vanish on `close()`.
**Why:** Implicit transactions + forgotten commit.
**How to avoid:** Use `with self._conn:` as a context manager — it commits on success, rolls back on exception. Applied in every write method in Pattern 1. [CITED: docs.python.org/3/library/sqlite3.html#sqlite3-connection-context-manager]

### Pitfall 6: WAL sidecar files leak into tests
**What goes wrong:** Test fixture uses `tmp_path`; after the test, WAL + SHM files remain open because the connection was not closed, causing cleanup failure on Windows.
**Why:** WAL mode creates `.sqlite-wal` and `.sqlite-shm` sidecar files.
**How to avoid:** Always use `with MerchantStore(...)` in tests (context manager closes the connection). Or, for strict isolation, test fixture can use `":memory:"` connections — but that requires factoring out the path logic, so use `tmp_path` + context manager.

## Runtime State Inventory

**This is a greenfield phase — no runtime state inventory needed.** Nothing is being renamed, refactored, or migrated. The phase creates a new `storage/` subpackage with no pre-existing databases, no OS-registered tasks, no cached service config, and no installed artifacts bearing an old name. Skipping this section per the RESEARCH template guidance for greenfield phases.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.9+ | Everything | ✓ | 3.13.5 [VERIFIED: venv probe] | — |
| `sqlite3` (stdlib) | `MerchantStore` | ✓ | SQLite 3.50.2 [VERIFIED: venv probe] | — |
| `pandas` | DataFrame I/O | ✓ | 2.3.3 [VERIFIED: venv probe] | — |
| `pydantic` | `MerchantProfile` | ✓ | 2.12.5 [VERIFIED: venv probe] | — |
| `pytest` | Test suite | ✓ | declared in `pyproject.toml` [VERIFIED: STACK.md] | — |
| `MESHEK_DATA_DIR` env var | Deployment flexibility | N/A (optional) | — | Defaults to `./data/merchants/` per D-02 |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

**Note on SQLite UPSERT version:** `ON CONFLICT … DO UPDATE` requires SQLite ≥ 3.24.0. Installed version is 3.50.2 — 26 minor versions ahead. No concern.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest` + `pytest-cov` [VERIFIED: STACK.md §Development] |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) [VERIFIED: STACK.md] |
| Quick run command | `pytest tests/storage/ -x -q` |
| Full suite command | `make test-all` (alias for `pytest` over all of `tests/`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STOR-01 #1 | Merchant A and B land in distinct files | unit | `pytest tests/storage/test_merchant_store.py::test_filesystem_isolation -x` | ❌ Wave 0 |
| STOR-01 #3 | `write_sales(df)` → `read_sales()` round-trip preserves date, merchant_id, product, quantity | unit | `pytest tests/storage/test_merchant_store.py::test_sales_roundtrip -x` | ❌ Wave 0 |
| STOR-01 #4 | Missing columns → `SchemaValidationError` (fail-fast) | unit | `pytest tests/storage/test_merchant_store.py::test_write_rejects_bad_schema -x` | ❌ Wave 0 |
| STOR-01 upsert | Re-writing a `(date, product)` overwrites quantity | unit | `pytest tests/storage/test_merchant_store.py::test_sales_upsert -x` | ❌ Wave 0 |
| STOR-01 date dtype | `read_sales` returns `datetime64[ns]` not `object` | unit | `pytest tests/storage/test_merchant_store.py::test_read_sales_date_dtype -x` | ❌ Wave 0 |
| STOR-01 date range | `read_sales(start, end)` filters correctly | unit | `pytest tests/storage/test_merchant_store.py::test_read_sales_date_range -x` | ❌ Wave 0 |
| STOR-01 cross-merchant write | `write_sales` with foreign `merchant_id` rejected | unit | `pytest tests/storage/test_merchant_store.py::test_write_rejects_foreign_merchant_id -x` | ❌ Wave 0 |
| STOR-02 #1 | `create_profile(...)` + `get_profile()` returns same fields | unit | `pytest tests/storage/test_merchant_store.py::test_profile_roundtrip -x` | ❌ Wave 0 |
| STOR-02 defaults | Zero-config: only `merchant_id` required; `timezone='Asia/Jerusalem'`, `language='he'` filled | unit | `pytest tests/storage/test_merchant_store.py::test_profile_defaults -x` | ❌ Wave 0 |
| STOR-02 unknown reader | `MerchantStore("never_created", must_exist=True)` raises `UnknownMerchantError` (D-03) | unit | `pytest tests/storage/test_merchant_store.py::test_reader_rejects_unknown_merchant -x` | ❌ Wave 0 |
| D-07 migrations | Re-opening an existing store is idempotent (migrations don't re-run) | unit | `pytest tests/storage/test_migrations.py::test_reopen_idempotent -x` | ❌ Wave 0 |
| D-07 user_version | Fresh DB ends at `PRAGMA user_version = 1` | unit | `pytest tests/storage/test_migrations.py::test_user_version_set -x` | ❌ Wave 0 |
| D-14 empty ID | Empty/whitespace `merchant_id` → `InvalidMerchantIdError` | unit | `pytest tests/storage/test_path_safety.py::test_empty_merchant_id_rejected -x` | ❌ Wave 0 |
| Threat: path traversal | `merchant_id` containing `../`, `/`, `\x00`, unicode → rejected; no file outside `data/merchants/` | unit | `pytest tests/storage/test_path_safety.py::test_path_traversal_rejected -x` | ❌ Wave 0 |
| D-02 env override | `MESHEK_DATA_DIR` env var redirects file creation | unit (monkeypatch) | `pytest tests/storage/test_merchant_store.py::test_data_dir_env_override -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/storage/ -x -q` (fast, <5 s expected)
- **Per wave merge:** `make test-all`
- **Phase gate:** Full suite green before `/gsd-verify-work`; additionally run `make lint` (ruff) because `pyproject.toml` enables `E, F, W, I, N, UP, B, SIM, RUF`.

### Wave 0 Gaps
- [ ] `tests/storage/__init__.py` — empty marker
- [ ] `tests/storage/conftest.py` — fixture producing a `MerchantStore` rooted at `tmp_path`, monkeypatching `MESHEK_DATA_DIR`
- [ ] `tests/storage/test_merchant_store.py` — primary CRUD + isolation + upsert + roundtrip tests
- [ ] `tests/storage/test_migrations.py` — `user_version` + idempotency coverage
- [ ] `tests/storage/test_path_safety.py` — threat-model coverage (empty ID, traversal, null byte)
- [ ] No framework install needed — `pytest` already declared in `pyproject.toml`

## Security Domain (Threat Model)

### Applicable ASVS L1 Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | meshek-ml is an internal inference service; authn is the meshek app's job. No auth in this phase. |
| V3 Session Management | no | Short-lived per-request `MerchantStore`; no sessions. |
| V4 Access Control | partial | Enforce `merchant_id` match between `MerchantStore.merchant_id` and DataFrame `merchant_id` column — prevents accidental cross-tenant write. |
| V5 Input Validation | **yes** | Regex whitelist for `merchant_id`; `validate_demand_schema` for sales DataFrame (D-08); Pydantic v2 for `MerchantProfile`. |
| V6 Cryptography | no | Data-at-rest encryption explicitly deferred (see "Known Threat Patterns" below). |
| V12 Files & Resources | **yes** | Filename derives from user-influenced string — path-traversal mitigation required. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `merchant_id` in filename | Tampering / Information Disclosure | Regex whitelist `^[A-Za-z0-9_-]{1,64}$` **plus** `Path.resolve()` parent-of-data-root check (two independent defenses) |
| SQL injection via `merchant_id` or sales fields | Tampering | Parameterized queries only (`?` placeholders) — never f-string into SQL |
| Cross-tenant write (caller supplies DataFrame with foreign `merchant_id`) | Tampering / Authorization bypass | `write_sales` checks `df["merchant_id"].unique() == {self.merchant_id}` and raises |
| Disk exhaustion via unbounded writes | DoS | **Out of scope for Phase 5** — rate limiting is Phase 8's API concern; note as open question |
| Data-at-rest disclosure (raw SQLite readable on disk) | Information Disclosure | **Accepted risk for v1.1**: data is commercial order history, not PII/PHI. Host-level disk encryption (Railway/Fly volumes) is the standard control. Application-level encryption (SQLCipher) deferred to v2. |
| Null-byte injection in `merchant_id` (`"a\x00b"`) | Tampering | Regex whitelist excludes `\x00` implicitly (not in `[A-Za-z0-9_-]`); `Path` rejects null bytes anyway |
| Backup/restore tampering | Integrity | Out of scope Phase 5; operational concern at Phase 8 deployment |

**Must-have Phase 5 controls** (verified by tests listed in Validation Architecture above):
1. `merchant_id` regex whitelist.
2. `Path.resolve()` parent check.
3. Parameterized SQL everywhere.
4. `write_sales` cross-tenant rejection.
5. `validate_demand_schema` on write path.

## Code Examples (additional, verified sources)

### Minimal `PRAGMA user_version` lifecycle
```python
# Source: https://sqlite.org/pragma.html#pragma_user_version
# "The user_version pragma will get or set the value of the user-version
#  integer at offset 60 in the database header. The user-version is an
#  integer that is available to applications to use however they want."
conn.execute("PRAGMA user_version").fetchone()[0]  # read
conn.execute("PRAGMA user_version = 1")             # write
```

### `ON CONFLICT DO UPDATE` canonical form
```sql
-- Source: https://sqlite.org/lang_upsert.html
INSERT INTO sales (date, merchant_id, product, quantity)
VALUES (?, ?, ?, ?)
ON CONFLICT(date, product) DO UPDATE SET
    quantity = excluded.quantity;
```
`excluded` is a special pseudo-table containing the row that would have been inserted.

### `sqlite3.Connection` as context manager for transactions
```python
# Source: https://docs.python.org/3/library/sqlite3.html#sqlite3-connection-context-manager
with conn:
    conn.execute("INSERT ...")
# Commits on clean exit, rolls back on exception.
```

### `read_sql_query` with date parsing
```python
# Source: https://pandas.pydata.org/docs/reference/api/pandas.read_sql_query.html
df = pd.read_sql_query(
    "SELECT date, merchant_id, product, quantity FROM sales WHERE date >= ?",
    conn,
    params=[start_iso],
    parse_dates=["date"],  # coerces TEXT ISO-8601 to datetime64[ns]
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `INSERT OR REPLACE` for upsert | `INSERT … ON CONFLICT DO UPDATE` | SQLite 3.24.0 (2018-06-04) | Preserves rowid, fires only UPDATE triggers, allows partial column updates |
| Pandas `date` cols as `object` dtype from `read_sql` | `parse_dates=["..."]` on `read_sql_query` | Stable across pandas 1.x/2.x | Keeps downstream pipeline type-consistent |
| Separate `schema_version` table | `PRAGMA user_version` (stdlib, single integer) | Always available | No extra table, no query overhead |
| `check_same_thread=False` + shared connection | Per-request short-lived connection under FastAPI | FastAPI best practice since ~2020 | Avoids thread-safety footguns |

**Deprecated/outdated:**
- Python `sqlite3` module's `isolation_level` autocommit toggle — the recommended idiom is now `with conn:` transactional blocks.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Merchant IDs fit the regex `^[A-Za-z0-9_-]{1,64}$` | Pattern 1 / Threat Model | If meshek app uses UUIDs (`-`, hex, 36 chars) — fits. If it uses Hebrew-unicode slugs or phone-number-based IDs (`+972-...`), regex rejects them. Discuss-phase must confirm. [ASSUMED] |
| A2 | One writer per merchant at a time is acceptable (WAL mode not strictly required) | Pattern 5 | If Phase 8 spawns concurrent writers for the same merchant (very unlikely — one merchant ≈ one human at a time), WAL prevents `SQLITE_BUSY`. Including it is harmless. [ASSUMED with low risk] |
| A3 | `data/merchants/` is excluded from git (or gitignored) | D-02 | If not, test runs will create tracked files. Check `.gitignore`; plan task should add entry if missing. [ASSUMED] |
| A4 | Data-at-rest encryption is not required for v1.1 | Threat Model | If merchant-level compliance (e.g., Israeli PDPA) requires it, SQLCipher or volume-level encryption is needed. **Recommend discuss-phase confirms this with user.** [ASSUMED] |
| A5 | `created_at` in ISO-8601 UTC is acceptable (not Israel local time) | Pattern 1 | If the meshek app expects local time, convert at API boundary in Phase 8. Storage stays UTC (best practice). [ASSUMED] |
| A6 | Merchant count per deployment stays in the low-thousands (filesystem can handle one file per merchant) | D-01 | ext4/APFS handle millions of files per directory fine; no concern below ~10k. [ASSUMED — low risk based on PROJECT.md merchant scale] |

## Open Questions

1. **`merchant_id` character set — does the meshek app use pure ASCII slug/UUID, or something with `+`, `.`, `@`, or Hebrew characters?**
   - What we know: D-14 locks caller-supplied IDs. PROJECT.md says meshek app owns identity.
   - What's unclear: Exact format. Regex in this research assumes `[A-Za-z0-9_-]`.
   - Recommendation: Discuss-phase follow-up — confirm format with meshek app repo. If format is wider (e.g., includes `.` or unicode), tighten the regex accordingly but keep `/`, `\`, `..`, `\x00` blacklisted.

2. **Data-at-rest encryption requirements.**
   - What we know: Not mentioned in CONTEXT or REQUIREMENTS.
   - What's unclear: Regulatory posture (Israeli privacy law, merchant contractual requirements).
   - Recommendation: Explicit "accepted risk for v1.1" note in the plan + track as v2 candidate if user confirms.

3. **`read_sales` empty-merchant behavior.**
   - What we know: D-03 says unknown merchant → loud error.
   - What's unclear: Is "merchant file exists but has zero sales rows" an error or an empty DataFrame?
   - Recommendation: Return empty DataFrame with correct schema (`REQUIRED_COLUMNS` columns, zero rows) — matches the invariant `read_sales().columns == REQUIRED_COLUMNS`.

## Recommendations Summary

1. **Structure.** New `src/meshek_ml/storage/` subpackage with a single `merchant_store.py` that houses `MerchantStore`, `MerchantProfile` (Pydantic v2), the error hierarchy, and the migrations list. Mirror under `tests/storage/`.
2. **Lifecycle.** `MerchantStore` is a context manager. Connection opened in `__init__`, closed on `__exit__`. Phase 8 FastAPI endpoints `with MerchantStore(id) as store:` per request.
3. **Migrations.** Ordered `_MIGRATIONS: list[tuple[int, callable]]` applied on connect, guarded by `PRAGMA user_version`. Ships at `user_version = 1`. Each migration wrapped in `with conn:` for atomicity.
4. **Sales upsert.** `INSERT … ON CONFLICT(date, product) DO UPDATE SET quantity = excluded.quantity` — never `INSERT OR REPLACE`.
5. **Schema enforcement.** Reuse `validate_demand_schema` (D-08) at the top of `write_sales`. Add a cross-tenant guard: `df["merchant_id"] must == self.merchant_id` or raise `SchemaValidationError`.
6. **Pandas round-trip.** Store `date` as TEXT ISO-8601; read back with `parse_dates=["date"]` to get `datetime64[ns]`. Test dtype explicitly.
7. **Security.** Regex whitelist `^[A-Za-z0-9_-]{1,64}$` + `Path.resolve()` parent-of-root check for `merchant_id`. Parameterized SQL everywhere. No shell-outs, no string-format SQL.
8. **Env var.** `MESHEK_DATA_DIR` read once via `os.environ.get(..., "data/merchants")` then `Path(...).resolve()`. Tests monkeypatch this to `tmp_path`.
9. **Test fixture.** `tests/storage/conftest.py` fixture that monkeypatches `MESHEK_DATA_DIR` to `tmp_path` and yields a `MerchantStore` factory. Each test gets fresh isolation, WAL sidecar cleanup handled by context manager close.
10. **Phase gate.** `pytest tests/storage/ -x -q` green + `make test-all` green + `make lint` clean. No new dependency added to `pyproject.toml`.

## Sources

### Primary (HIGH confidence)
- `sqlite.org/lang_upsert.html` — `ON CONFLICT DO UPDATE` syntax, semantics, version history (3.24.0+)
- `sqlite.org/pragma.html#pragma_user_version` — user_version slot semantics
- `sqlite.org/datatype3.html` §2.2 — Date and Time Datatype recommendations
- `sqlite.org/wal.html` — Write-Ahead Logging trade-offs
- `docs.python.org/3/library/sqlite3.html` — `check_same_thread`, connection-context-manager semantics
- `pandas.pydata.org/docs/reference/api/pandas.read_sql_query.html` — `parse_dates` kwarg
- Project files read: `05-CONTEXT.md`, `REQUIREMENTS.md`, `STATE.md`, `ROADMAP.md`, `src/meshek_ml/forecasting/schema.py`, `.planning/codebase/STACK.md`, `STRUCTURE.md`, `CONVENTIONS.md`
- Venv probes: Python 3.13.5, SQLite 3.50.2, pandas 2.3.3, pydantic 2.12.5

### Secondary (MEDIUM confidence)
- OWASP ASVS L1 V5 (Input Validation) and V12 (Files & Resources) categories — mapped by convention, not re-fetched this session

### Tertiary (LOW confidence)
- None — every claim in this research has either a stdlib/official-docs source or a verified venv probe. The only `[ASSUMED]` items are listed explicitly in the Assumptions Log.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all deps already installed, SQLite features verified against docs and version probe
- Architecture: HIGH — pattern matches established CONVENTIONS.md shape (domain subpackage, pure functions + one stateful class, dataclass/Pydantic at boundaries)
- Pitfalls: HIGH — all six pitfalls backed by official docs
- Threat model: MEDIUM-HIGH — path-traversal mitigation is well-understood; data-at-rest encryption stance is an assumption flagged for discuss-phase

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (stable domain; SQLite/pandas/pydantic APIs change slowly)

## RESEARCH COMPLETE
