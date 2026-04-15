---
id: SEED-001
status: dormant
planted: 2026-04-15
planted_during: v1.1 — Merchant Order Advisor (Phase 8 complete)
trigger_when: merchant count > 50 OR cross-merchant aggregations needed OR GCS FUSE POSIX incompatibilities cause incidents
scope: Large
---

# SEED-001: GCP-native storage migration — SQLite → Cloud SQL Postgres

## Why This Matters

The v1.1 storage model is one SQLite file per merchant (`MerchantStore` in
`src/meshek_ml/storage/merchant_store.py`), selected for filesystem-level
isolation, zero ops burden, and stdlib-only dependencies. Phase 8.1 will
extend this to Cloud Run by mounting a GCS bucket via GCS FUSE so each
merchant's SQLite file persists across container restarts.

This works great until it doesn't:

1. **GCS FUSE is not POSIX-complete.** SQLite's WAL mode relies on
   memory-mapped I/O and atomic rename semantics that FUSE over object
   storage can misbehave on. Phase 8.1 will force `journal_mode=DELETE` as
   a workaround, but locking edge cases can still bite in production.
2. **No cross-merchant queries.** Tier 2 pooled priors currently scan every
   merchant's file sequentially. With 50+ merchants this becomes O(N) disk
   I/O on every recommendation. Postgres with a shared `sales` table
   indexed by `(merchant_id, date, product)` turns this into a single
   planned query.
3. **Backups and PITR.** GCS versioning gives per-file rollback but no
   point-in-time recovery across the full merchant corpus. Cloud SQL gives
   both out of the box.
4. **Connection pooling and observability.** Cloud SQL + Cloud SQL Auth
   Proxy + sqlalchemy gives us structured query logs, slow query analysis,
   and per-request pooling — all of which are hand-rolled today.

## When to Surface

**Trigger** (ANY of the following):

- Production merchant count exceeds ~50 (pooled prior scan becomes a hot path)
- Product asks for cross-merchant analytics or a merchant-wide admin dashboard
  that file-per-merchant can't express efficiently
- GCS FUSE causes a production incident (corruption, lost writes, lock
  contention on `.db-journal` files) — scope v2 ASAP
- Any work that needs multi-merchant transactions or referential integrity
- When we add federated learning across merchants (v2 `OPT-02`) — training
  needs cross-merchant reads anyway

Present this seed during `/gsd-new-milestone` whenever the upcoming milestone
mentions any of: "scale", "analytics", "admin", "federated", "cross-merchant",
"observability", "reporting", "migration", "storage", "database", "postgres".

## Scope

**Full milestone** (estimated 4-6 phases):

1. **Schema design phase** — ERD for `merchants`, `profiles`, `sales`,
   `products`, `merchant_config`; index strategy; partition key decisions;
   timezone handling (currently per-merchant `Asia/Jerusalem` in profile).
2. **MerchantStore rewrite** — new `PostgresMerchantStore` implementing the
   same interface as today's SQLite `MerchantStore`. Keep a dual-write
   adapter behind a feature flag so the service can run both in parallel
   during cutover.
3. **Cloud SQL provisioning** — private IP, Auth Proxy sidecar on Cloud Run,
   IAM-based auth (no passwords), automated backups, PITR window, read
   replica decision.
4. **Migration tool** — batch script that walks `data/merchants/*.db`, reads
   each SQLite store via the existing API, and inserts into Postgres.
   Idempotent, resumable, produces a reconciliation report.
5. **Service cutover** — feature-flag flip, shadow-read validation period,
   then sqlite teardown. Includes rollback plan (dual-write keeps sqlite
   writable until flag flip).
6. **Observability + pooling** — sqlalchemy + pgBouncer or Cloud SQL
   connector, structured query logs wired into the Phase 8 request logger,
   slow query alerting.

## Dependencies

- **Hard prereq:** Phase 8.1 (Cloud Run + GCS FUSE) deployed to production
  with real merchants using it. We need real traffic data to justify the
  migration and to sanity-check that Postgres schema decisions match
  actual query patterns.
- Phase 5 (Data Foundation) storage API is stable — any changes to
  `MerchantStore` during v1.x would force a rebase here.
- Phase 6 (Recommendation Engine) `PooledStore.aggregate_priors` is the
  main hot path that drives the cross-merchant query requirement.

## Breadcrumbs

- `src/meshek_ml/storage/merchant_store.py` — current SQLite implementation
  (`_MERCHANT_ID_PATTERN`, `_apply_migrations`, `write_sales`, `read_sales`)
- `src/meshek_ml/recommendation/pooled_store.py` — cross-merchant aggregation
  that becomes expensive at scale
- `.planning/phases/05-data-foundation/05-CONTEXT.md` D-01, D-02, D-07 —
  original decisions on file-per-merchant isolation and `PRAGMA user_version`
  migration mechanism. Any Postgres rewrite must preserve the isolation
  semantics (no merchant can see another merchant's rows without explicit
  admin path).
- `.planning/REQUIREMENTS.md` §STOR-01/STOR-02 — storage requirements,
  which are satisfied by both SQLite and Postgres implementations.
- `.planning/phases/06-recommendation-engine/06-CONTEXT.md` D-05, D-06 —
  pooled prior shrinkage logic; moves cleanly to SQL but the weighting
  formula must be preserved.
- `.planning/phases/08-api-surface-deployment/08-CONTEXT.md` D-15, D-16 —
  Docker image must install the Cloud SQL Auth Proxy binary OR rely on the
  sqlalchemy `cloud-sql-python-connector` package.
- `.planning/phases/08-api-surface-deployment/08-VERIFICATION.md` — end-to-end
  tests pattern that should be ported to run against Postgres.

## Open Questions (to resolve at milestone planning time)

- Cloud SQL edition: Enterprise vs Enterprise Plus? Standard vs HA? Single
  region (me-west1 Tel Aviv) or multi-region?
- Schema: one big `sales` table with `(merchant_id, date, product)` PK, or
  partitioned per-merchant schema? (Leaning single table + BRIN index on
  date given typical query shape.)
- Do we keep per-merchant SQLite as a local development fallback (to avoid
  forcing Cloud SQL for tests) via an adapter interface?
- Migration window: online dual-write or brief maintenance window? Given
  greengrocers order at 2 AM, a 5-minute outage at 10 AM is probably fine.
- Does this milestone also tackle REC-05 (async retrain endpoint) since
  retrain jobs will want cross-merchant reads anyway?

---

*Planted 2026-04-15 after Phase 8 completion. Surface during
`/gsd-new-milestone` when the trigger conditions above are met, or when the
user explicitly asks "how would we scale storage?".*
