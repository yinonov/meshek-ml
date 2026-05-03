---
phase: 9
slug: model-bundle-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-15
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `.venv/bin/python -m pytest tests/recommendation/test_model_bundle.py -x -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests -q` |
| **Shell lint command** | `bash -n scripts/train-and-publish-model.sh` |
| **Estimated runtime** | ~5s (unit) |

---

## Sampling Rate

- **After every task commit:** Run the quick command
- **After every plan wave:** Run the full suite
- **Before `/gsd-verify-work`:** Full suite green + deterministic bundle verified twice
- **Max feedback latency:** 10s

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| 9-01-01 | 01 | 1 | MODEL-02 | cli_train wraps train_and_save with deterministic seed | unit | `.venv/bin/python -m pytest tests/recommendation/test_model_bundle.py::test_cli_produces_loadable_bundle -x` | ❌ W0 | ⬜ pending |
| 9-01-02 | 01 | 1 | MODEL-02 | deterministic seed produces matching feature_cols+residual_std across runs | unit | `.venv/bin/python -m pytest tests/recommendation/test_model_bundle.py::test_deterministic_rerun -x` | ❌ W0 | ⬜ pending |
| 9-02-01 | 02 | 2 | MODEL-02 | `scripts/train-and-publish-model.sh` is syntactically valid and DRY_RUN=1 prints gcloud cp | infra | `bash -n scripts/train-and-publish-model.sh && DRY_RUN=1 LOCAL_ONLY=0 bash scripts/train-and-publish-model.sh \| grep -q 'gcloud storage cp'` | ❌ W0 | ⬜ pending |
| 9-02-02 | 02 | 2 | MODEL-02 | LOCAL_ONLY=1 actually trains and writes a bundle (no upload) | integration | `LOCAL_ONLY=1 bash scripts/train-and-publish-model.sh && test -f models/lightgbm_v1.bundle` | ❌ W0 | ⬜ pending |
| 9-03-01 | 03 | 3 | MODEL-01 | `scripts/bootstrap-cloudrun.sh` adds models bucket block with versioning+lifecycle+IAM (dry-run) | infra | `DRY_RUN=1 bash scripts/bootstrap-cloudrun.sh \| grep -E 'meshek-prod-models.*versioning\|objectViewer.*meshek-prod-models'` | ✅ | ⬜ pending |
| 9-03-02 | 03 | 3 | MODEL-01 | `scripts/deploy-cloudrun.sh` emits a second `--add-volume` pair for models (dry-run) | infra | `DRY_RUN=1 bash scripts/deploy-cloudrun.sh \| grep -E 'models-vol.*cloud-storage.*meshek-prod-models.*readonly=true'` | ✅ | ⬜ pending |
| 9-03-03 | 03 | 3 | MODEL-01 | Existing deploy dry-run test still matches the merchants mount line | infra | `DRY_RUN=1 bash scripts/deploy-cloudrun.sh \| grep -E 'merchants-vol.*mount-path=/var/lib/meshek/merchants'` | ✅ | ⬜ pending |
| 9-04-01 | 04 | 4 | MODEL-01 | `docs/deploy-cloudrun.md` gains a "Training and publishing a model bundle" section | doc | `grep -qE 'Training and publishing' docs/deploy-cloudrun.md` | ✅ | ⬜ pending |
| 9-04-02 | 04 | 4 | MODEL-01 | Docs document rollback via generation copy | doc | `grep -qE 'generation\|#[0-9]+' docs/deploy-cloudrun.md` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/meshek_ml/recommendation/cli_train.py` — new CLI wrapper
- [ ] `tests/recommendation/test_model_bundle.py` — regression test (load, shape, determinism)
- [ ] `scripts/train-and-publish-model.sh` — bash entrypoint, executable
- [ ] `scripts/bootstrap-cloudrun.sh` — extend with models bucket block
- [ ] `scripts/deploy-cloudrun.sh` — extend with second `--add-volume` pair
- [ ] `docs/deploy-cloudrun.md` — add training+publishing+rollback section

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Re-run bootstrap to provision models bucket | MODEL-01 | Operator GCP creds | `./scripts/bootstrap-cloudrun.sh` |
| Train + publish a real bundle | MODEL-02 | GCP billing + Cloud Storage write | `./scripts/train-and-publish-model.sh` |
| Redeploy Cloud Run with 2nd FUSE mount | MODEL-01 | Live GCP | `./scripts/deploy-cloudrun.sh` |
| Verify `/health` flips to 200 | MODEL-01 | Live service | identity-token curl with temporary ingress relaxation |
| Verify Tier 3 recommendation | MODEL-01 | Live service + seeded merchant | curl `POST /recommend` for merchant with ≥14 days sales |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
