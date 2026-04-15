"""Env-guarded Docker smoke test.

Guards: MESHEK_DOCKER_SMOKE=1 must be set for the test to actually run.
Without the env flag the test is skipped, keeping normal test runs fast.

Marked @pytest.mark.integration so ``-m "not integration"`` excludes it.

Usage:
    MESHEK_DOCKER_SMOKE=1 uv run pytest tests/service/test_docker_smoke.py -x -v
"""
from __future__ import annotations

import os
import subprocess
import time
import urllib.error
import urllib.request

import pytest

_SMOKE_ENABLED = os.environ.get("MESHEK_DOCKER_SMOKE") == "1"
_IMAGE_TAG = "meshek-ml-smoke:test"
_HOST_PORT = 18000
_HEALTH_URL = f"http://localhost:{_HOST_PORT}/health"
_BUILD_TIMEOUT_S = 600  # 10 minutes for a cold Docker cache
_POLL_ATTEMPTS = 15
_POLL_INTERVAL_S = 1


def _docker_run_detached() -> str:
    """Start the container in detached mode and return the container ID."""
    result = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "-p",
            f"{_HOST_PORT}:8000",
            "-e",
            "MESHEK_DATA_DIR=/tmp/merchants",
            _IMAGE_TAG,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip()


def _stop_container(container_id: str) -> None:
    """Force-remove a running container."""
    subprocess.run(
        ["docker", "rm", "-f", container_id],
        capture_output=True,
        timeout=15,
    )


def _poll_health() -> int:
    """Poll /health until it responds or attempts are exhausted.

    Returns the HTTP status code of the first successful response.
    Raises ``RuntimeError`` if the service does not come up within the
    allowed window.
    """
    last_exc: Exception | None = None
    for attempt in range(1, _POLL_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(_HEALTH_URL, timeout=3) as resp:
                return resp.status
        except urllib.error.HTTPError as exc:
            # 503 degraded-start is a valid "alive" signal — return its code.
            return exc.code
        except (urllib.error.URLError, ConnectionRefusedError, OSError) as exc:
            last_exc = exc
            time.sleep(_POLL_INTERVAL_S)
    raise RuntimeError(
        f"Service did not respond on {_HEALTH_URL} after {_POLL_ATTEMPTS} attempts. "
        f"Last error: {last_exc}"
    )


@pytest.mark.integration
@pytest.mark.skipif(not _SMOKE_ENABLED, reason="MESHEK_DOCKER_SMOKE=1 not set")
def test_health():
    """Build the image, run it, verify /health responds 200 or 503.

    Accepts 503 because the image may not contain a model bundle — the
    degraded-start contract means the container still boots and responds.
    Cleanup is guaranteed via a finally block.
    """
    # Build
    subprocess.run(
        ["docker", "build", "-t", _IMAGE_TAG, "."],
        check=True,
        timeout=_BUILD_TIMEOUT_S,
    )

    container_id: str | None = None
    try:
        container_id = _docker_run_detached()
        status = _poll_health()
        assert status in (200, 503), (
            f"Expected /health to return 200 or 503, got {status}"
        )
    finally:
        if container_id:
            _stop_container(container_id)
