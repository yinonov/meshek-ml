"""Wave 0 stub for plan 06 — Docker smoke test (integration guard).

Actual test body is written in plan 06. This file exists so
pytest --collect-only succeeds for every downstream plan.
"""
import os

import pytest


@pytest.mark.integration
def test_docker_smoke_placeholder():
    """Placeholder guarded by MESHEK_DOCKER_SMOKE env flag.

    Skipped unless MESHEK_DOCKER_SMOKE=1 is set. Actual assertions
    are added in plan 06.
    """
    if not os.environ.get("MESHEK_DOCKER_SMOKE"):
        pytest.skip("MESHEK_DOCKER_SMOKE not set — skipping Docker smoke test")
