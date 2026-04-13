# Phase 5: Data Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-13
**Phase:** 05-data-foundation
**Areas discussed:** Storage layout, Schema & tables, Access API shape, Profile fields & ID

---

## Storage layout

### Q: Where should per-merchant SQLite files live and how should they be named?

| Option | Description | Selected |
|--------|-------------|----------|
| data/merchants/{id}.sqlite | Flat dir under repo data/, filename = merchant_id. | ✓ |
| Configurable root via env | Default to data/merchants/ with MESHEK_DATA_DIR override. | (folded as D-02) |
| XDG user data dir | platformdirs-based location. | |

**User's choice:** `data/merchants/{id}.sqlite` — then layered in env override for Docker in Phase 8.

### Q: When should a merchant's SQLite file be created?

| Option | Description | Selected |
|--------|-------------|----------|
| On first profile write | create_merchant(...) runs CREATE TABLE IF NOT EXISTS. | ✓ |
| Explicit bootstrap call | Require init_merchant_storage(id) first. | |
| Lazy on any access | Auto-create on read too. | |

**User's choice:** On first profile write.

---

## Schema & tables

### Q: What columns should the sales table hold?

| Option | Description | Selected |
|--------|-------------|----------|
| Canonical only | date, merchant_id, product, quantity — matches schema.py. | ✓ |
| Canonical + price + unit | Add price and unit now. | |
| Canonical + created_at | Add audit timestamp. | |

**User's choice:** Canonical only.

### Q: How should the sales primary key / uniqueness work?

| Option | Description | Selected |
|--------|-------------|----------|
| (date, product) composite PK | One row per product per day; upsert on rewrite. | ✓ |
| Surrogate INT PK, append-only | Every write is a new row. | |
| (date, product) UNIQUE + rowid | Hybrid. | |

**User's choice:** (date, product) composite PK.

### Q: How should schema evolution be handled?

| Option | Description | Selected |
|--------|-------------|----------|
| user_version pragma + inline migrations | Stdlib, ordered migration functions on connect. | ✓ |
| CREATE IF NOT EXISTS only | No migrations. | |
| Alembic | Full migration framework. | |

**User's choice:** user_version pragma + inline migrations.

---

## Access API shape

### Q: Which SQLite library should the storage layer use?

| Option | Description | Selected |
|--------|-------------|----------|
| sqlite3 stdlib | Zero new deps. | ✓ |
| SQLAlchemy Core | Typed expression language. | |
| sqlmodel / SQLAlchemy ORM | Pydantic-integrated ORM. | |

**User's choice:** sqlite3 stdlib.

### Q: How should the access layer be organized?

| Option | Description | Selected |
|--------|-------------|----------|
| MerchantStore class | One object per merchant owning the connection. | ✓ |
| Module-level functions | storage.write_sales(merchant_id, df). | |
| Repository per entity | Separate SalesRepo and ProfileRepo. | |

**User's choice:** MerchantStore class.

### Q: What should sales reads return?

| Option | Description | Selected |
|--------|-------------|----------|
| pandas DataFrame | Matches forecasting pipeline. | ✓ |
| List of Pydantic SalesRecord | Typed rows. | |
| Raw list of dicts | Stdlib only. | |

**User's choice:** pandas DataFrame.

---

## Profile fields & ID

### Q: What fields should the merchant profile hold at v1.1?

| Option | Description | Selected |
|--------|-------------|----------|
| name | Display name. | ✓ |
| timezone | IANA tz, default Asia/Jerusalem. | ✓ |
| language | Default 'he'. | ✓ |
| created_at | ISO insert timestamp. | ✓ |

**User's choice:** All four.

### Q: How should merchant_id be generated?

| Option | Description | Selected |
|--------|-------------|----------|
| Caller-supplied string | meshek app owns the ID. | ✓ |
| UUID4 generated here | Store returns new UUID. | |
| Short slug from name | Human-readable slug. | |

**User's choice:** Caller-supplied string.

---

## Claude's Discretion

- Exact SQL statements and index choices beyond the PK
- Connection lifecycle details (context manager, `close()`)
- Error class hierarchy within the storage module
- Test fixture strategy

## Deferred Ideas

- Price column (out of scope per PROJECT.md)
- Unit column (revisit in Phase 7)
- Cross-merchant pooled read helper (Phase 6 concern)
- Global product catalog (Phase 7 concern)
- Async I/O / connection pooling (not needed at v1.1 volumes)
