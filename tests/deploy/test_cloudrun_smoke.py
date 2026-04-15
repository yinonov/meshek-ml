"""Env-guarded live Cloud Run smoke test.

Wave-0 stub — body is filled in by Plan 04 (task 8.1-04-02). Kept as a collectable
placeholder so CI / normal test runs exercise the test discovery path now.

Guards: MESHEK_CLOUDRUN_SMOKE=1 AND MESHEK_CLOUDRUN_URL must be set to actually run.
"""
from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration

_SMOKE_ENABLED = (
    os.environ.get("MESHEK_CLOUDRUN_SMOKE") == "1"
    and bool(os.environ.get("MESHEK_CLOUDRUN_URL"))
)


@pytest.mark.skipif(not _SMOKE_ENABLED, reason="Cloud Run smoke disabled (set MESHEK_CLOUDRUN_SMOKE=1 + MESHEK_CLOUDRUN_URL)")
def test_cloudrun_smoke_placeholder():
    """Placeholder — replaced by Plan 04, task 8.1-04-02."""
    pytest.skip("Wave-0 stub; real body arrives in plan 04")
