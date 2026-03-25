"""Experiment tracking via Trackio.

Thin wrapper around trackio that gracefully degrades when the package
is not installed.  Every call is a no-op when tracking is disabled so
that training scripts work without the ``tracking`` extra.

Usage::

    from meshek_ml.common.tracking import tracker

    tracker.init(project="forecasting", config={"model": "lightgbm", "lr": 0.05})
    tracker.log({"mae": 2.3, "rmse": 3.1})
    tracker.alert("Loss spike", "MAE jumped to 5.0 at epoch 12", level="warn")
    tracker.finish()
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_HAS_TRACKIO = False
try:
    import trackio as _trackio

    _HAS_TRACKIO = True
except ImportError:
    _trackio = None  # type: ignore[assignment]


class _Tracker:
    """Unified tracking interface that wraps Trackio."""

    def __init__(self) -> None:
        self._active = False

    @property
    def available(self) -> bool:
        return _HAS_TRACKIO

    def init(
        self,
        project: str,
        run_name: str | None = None,
        config: dict[str, Any] | None = None,
        space_id: str | None = None,
    ) -> None:
        """Start a tracking run.

        Args:
            project: Project name (e.g. "forecasting", "optimization").
            run_name: Optional run name.  Auto-generated if *None*.
            config: Hyperparameters / metadata dict.
            space_id: HF Space for remote dashboard (e.g. "user/trackio").
        """
        if not _HAS_TRACKIO:
            logger.debug("trackio not installed — tracking disabled")
            return

        kwargs: dict[str, Any] = {"project": project}
        if run_name is not None:
            kwargs["run"] = run_name
        if config is not None:
            kwargs["config"] = config
        if space_id is not None:
            kwargs["space_id"] = space_id

        _trackio.init(**kwargs)
        self._active = True

    def log(self, metrics: dict[str, float | int]) -> None:
        """Log a dict of metrics for the current step."""
        if not self._active:
            return
        _trackio.log(metrics)

    def alert(
        self,
        title: str,
        text: str = "",
        level: str = "info",
    ) -> None:
        """Fire a tracking alert.

        Args:
            title: Short alert title.
            text: Longer description.
            level: One of "info", "warn", "error".
        """
        if not self._active:
            return
        level_map = {
            "info": _trackio.AlertLevel.INFO,
            "warn": _trackio.AlertLevel.WARN,
            "error": _trackio.AlertLevel.ERROR,
        }
        _trackio.alert(
            title=title,
            text=text,
            level=level_map.get(level, _trackio.AlertLevel.INFO),
        )

    def finish(self) -> None:
        """End the current tracking run."""
        if not self._active:
            return
        _trackio.finish()
        self._active = False


# Module-level singleton — import and use directly.
tracker = _Tracker()
