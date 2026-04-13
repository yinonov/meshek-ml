"""Per-merchant SQLite storage layer.

Implements `MerchantStore` — a thin stdlib `sqlite3` wrapper that owns one
SQLite file per merchant under `MESHEK_DATA_DIR` (default `data/merchants/`).

Design references (see .planning/phases/05-data-foundation/05-CONTEXT.md):
  D-01: one SQLite file per merchant (filesystem-level isolation)
  D-02: data root configurable via MESHEK_DATA_DIR
  D-03: no lazy-create-on-read; `must_exist=True` raises UnknownMerchantError
  D-05: sales primary key = (date, product); writes are upserts
  D-07: schema evolution via PRAGMA user_version + ordered migrations
  D-08: fail-fast via reused `forecasting.schema.validate_demand_schema`
  D-13: MerchantProfile fields and defaults
  D-14: merchant_id is caller-supplied — must be validated as a filename
  T-5-01: regex whitelist + Path.resolve() parent check (defense in depth)
  T-5-02: ALL caller values flow through `?` placeholders, never f-strings
"""
from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
from pydantic import BaseModel, Field

from meshek_ml.forecasting.schema import (
    REQUIRED_COLUMNS,
    SchemaValidationError,
    validate_demand_schema,
)

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

# T-5-01: merchant_id whitelist. ASCII alnum + `_` + `-`, 1..64 chars.
# Rejects: empty, whitespace, `/`, `\`, `.`, `\x00`, unicode, oversized,
# absolute paths, parent-traversal sequences. Tested by
# tests/storage/test_path_traversal.py.
_MERCHANT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# Schema baseline for v1.1 — bump when adding migrations.
_SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


class MerchantStoreError(RuntimeError):
    """Base class for storage-layer errors."""


class UnknownMerchantError(MerchantStoreError):
    """Raised when `must_exist=True` is requested and no store file exists."""


class InvalidMerchantIdError(MerchantStoreError):
    """Raised when a caller-supplied merchant_id fails the whitelist check."""


# ---------------------------------------------------------------------------
# Public model — MerchantProfile (D-13)
# ---------------------------------------------------------------------------


class MerchantProfile(BaseModel):
    """Merchant identity and locale defaults persisted per store."""

    merchant_id: str
    name: Optional[str] = None
    timezone: str = "Asia/Jerusalem"
    language: str = "he"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Path helpers (T-5-01 mitigation)
# ---------------------------------------------------------------------------


def _data_root() -> Path:
    """Resolve the data root from ``$MESHEK_DATA_DIR``.

    Read on every call so tests using ``monkeypatch.setenv`` see the override.

    WR-03: Fail fast when ``MESHEK_DATA_DIR`` is unset rather than silently
    anchoring to the process CWD. Different working directories would
    otherwise produce different data roots and orphan stores. Callers must
    set the env var explicitly (tests use a monkeypatched ``tmp_path``).
    """
    raw = os.environ.get("MESHEK_DATA_DIR")
    if raw is None or not raw.strip():
        raise MerchantStoreError(
            "MESHEK_DATA_DIR must be set to an absolute path. "
            "Tests should monkeypatch it to tmp_path; deployments should "
            "point it at a persistent volume (e.g. /var/lib/meshek/merchants)."
        )
    return Path(raw).resolve()


def _validate_merchant_id(merchant_id: str) -> str:
    """Validate `merchant_id` against the whitelist regex.

    Raises:
        InvalidMerchantIdError: on type mismatch, empty/whitespace, or any
            character outside the whitelist (T-5-01).
    """
    if not isinstance(merchant_id, str):
        raise InvalidMerchantIdError(
            f"merchant_id must be str, got {type(merchant_id).__name__}"
        )
    if not merchant_id or not merchant_id.strip():
        raise InvalidMerchantIdError(
            "merchant_id must not be empty or whitespace"
        )
    if not _MERCHANT_ID_PATTERN.match(merchant_id):
        raise InvalidMerchantIdError(
            f"merchant_id {merchant_id!r} must match "
            f"{_MERCHANT_ID_PATTERN.pattern}"
        )
    return merchant_id


def _merchant_path(merchant_id: str) -> Path:
    """Build and verify the absolute SQLite file path for a merchant.

    Defense in depth: even if the regex is ever loosened, `Path.resolve()`
    plus a parent-equality check guarantees no file lands outside the root.
    """
    root = _data_root()
    candidate = (root / f"{merchant_id}.sqlite").resolve()
    if candidate.parent != root:
        raise InvalidMerchantIdError(
            f"merchant_id {merchant_id!r} resolves outside data root"
        )
    return candidate


# ---------------------------------------------------------------------------
# Migrations (D-07, Pattern 2 from 05-RESEARCH.md)
#
# NOTE: PRAGMA user_version is the application's slot. PRAGMA schema_version
# is SQLite's internal cache-invalidation counter — never touch it
# (Pitfall 3 in 05-RESEARCH.md).
# ---------------------------------------------------------------------------


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
        -- IN-01: `merchant_id` is structurally redundant here — each
        -- SQLite file already belongs to exactly one merchant (D-01,
        -- filesystem-level isolation) and `write_sales` enforces a
        -- cross-merchant guard (T-5-03). The column is retained to keep
        -- the on-disk row shape aligned with `forecasting.schema`'s
        -- REQUIRED_COLUMNS and to preserve a future migration path
        -- toward multi-tenant consolidation without a schema rewrite.
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


_MIGRATIONS = [(1, _migration_001_initial)]


def _apply_migrations(conn: sqlite3.Connection) -> None:
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    for target, fn in _MIGRATIONS:
        if current < target:
            with conn:
                fn(conn)
                # Hardcoded int constant — never caller input. The only
                # f-string SQL allowed in this module (T-5-02 audit).
                conn.execute(f"PRAGMA user_version = {int(target)}")
            current = target


# ---------------------------------------------------------------------------
# MerchantStore
# ---------------------------------------------------------------------------


class MerchantStore:
    """Owns one SQLite connection scoped to a single merchant.

    Use as a context manager:

        with MerchantStore("shop_a") as store:
            store.create_profile(MerchantProfile(merchant_id="shop_a"))
            df = store.read_sales()

    Short-lived; do not share across threads.
    """

    def __init__(self, merchant_id: str, *, must_exist: bool = False) -> None:
        self.merchant_id = _validate_merchant_id(merchant_id)
        self._path = _merchant_path(self.merchant_id)

        if must_exist and not self._path.exists():
            raise UnknownMerchantError(
                f"No store for merchant {merchant_id!r}"
            )

        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = sqlite3.connect(
            str(self._path), detect_types=sqlite3.PARSE_DECLTYPES
        )
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        _apply_migrations(self._conn)

    # -- context manager protocol -----------------------------------------

    def __enter__(self) -> "MerchantStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        """Idempotently close the underlying SQLite connection."""
        if self._conn is not None:
            try:
                self._conn.close()
            finally:
                self._conn = None

    # -- profile CRUD ------------------------------------------------------

    def create_profile(self, profile: MerchantProfile) -> MerchantProfile:
        if profile.merchant_id != self.merchant_id:
            raise InvalidMerchantIdError(
                f"profile.merchant_id {profile.merchant_id!r} does not match "
                f"store merchant_id {self.merchant_id!r}"
            )
        assert self._conn is not None
        with self._conn:
            self._conn.execute(
                "INSERT INTO merchant_profile "
                "(merchant_id, name, timezone, language, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    profile.merchant_id,
                    profile.name,
                    profile.timezone,
                    profile.language,
                    profile.created_at,
                ),
            )
        return profile

    def get_profile(self) -> Optional[MerchantProfile]:
        assert self._conn is not None
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

    # -- sales DML ---------------------------------------------------------

    def write_sales(self, df: pd.DataFrame) -> int:
        # D-08 fail-fast: shape, dtype, nulls — reuse forecasting schema.
        df = validate_demand_schema(df)

        # T-5-03 cross-merchant guard.
        foreign = (
            df.loc[df["merchant_id"] != self.merchant_id, "merchant_id"]
            .unique()
            .tolist()
        )
        if foreign:
            raise SchemaValidationError(
                f"write_sales received foreign merchant_id(s): {foreign}"
            )

        rows = []
        for row in df.itertuples(index=False):
            date_val = pd.Timestamp(row.date).to_pydatetime().date().isoformat()
            rows.append(
                (
                    date_val,
                    str(row.merchant_id),
                    str(row.product),
                    float(row.quantity),
                )
            )

        assert self._conn is not None
        with self._conn:
            # WR-02: drop the no-op `merchant_id = excluded.merchant_id`
            # SET clause. The cross-merchant guard above already prevents
            # foreign merchant_ids from reaching this statement, and the
            # per-file isolation layer ensures collision is impossible in
            # practice. Keeping the SET was misleading dead code.
            self._conn.executemany(
                "INSERT INTO sales (date, merchant_id, product, quantity) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(date, product) DO UPDATE SET "
                "quantity = excluded.quantity",
                rows,
            )
        return len(rows)

    def read_sales(self, start=None, end=None) -> pd.DataFrame:
        clauses = ["merchant_id = ?"]
        params: list = [self.merchant_id]
        if start is not None:
            clauses.append("date >= ?")
            params.append(pd.Timestamp(start).date().isoformat())
        if end is not None:
            clauses.append("date <= ?")
            params.append(pd.Timestamp(end).date().isoformat())

        # Static SQL; only the WHERE-clause skeleton varies, all values
        # flow through `?` placeholders (T-5-02).
        query = (
            "SELECT date, merchant_id, product, quantity FROM sales "
            "WHERE " + " AND ".join(clauses) + " ORDER BY date, product"
        )

        assert self._conn is not None
        out = pd.read_sql_query(
            query, self._conn, params=params, parse_dates=["date"]
        )
        # WR-01: parse_dates no-ops on empty result sets, leaving object
        # dtype. Coerce explicitly so downstream consumers always see
        # datetime64[ns].
        if out["date"].dtype != "datetime64[ns]":
            out["date"] = pd.to_datetime(out["date"])
        return out[REQUIRED_COLUMNS]
