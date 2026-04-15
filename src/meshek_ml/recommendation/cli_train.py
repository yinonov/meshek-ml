# src/meshek_ml/recommendation/cli_train.py
# CLI entry point for offline LightGBM training -- D-10.
#
# Usage:
#     python -m meshek_ml.recommendation.cli_train [options]
#
# MESHEK_MODELS_DIR must be set by the caller (bash wrapper or test fixture)
# before invocation. This module never sets it so that monkeypatch.setenv
# works correctly in tests and the bash wrapper can derive it from the output
# path (T-9-01-01, D-16).
#
# Env var defaults:
#   MESHEK_TRAIN_SEED         default 42
#   MESHEK_TRAIN_N_MERCHANTS  default 20
#   MESHEK_TRAIN_DAYS         default 180
#   MESHEK_TRAIN_OUTPUT       default models/lightgbm_v1.bundle
from __future__ import annotations

import argparse
import json
import os
from datetime import date, timedelta
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Train and save a LightGBM model bundle from synthetic seed data."
    )
    p.add_argument(
        "--seed",
        type=int,
        default=int(os.environ.get("MESHEK_TRAIN_SEED", "42")),
        help="Random seed for deterministic data generation (default: 42).",
    )
    p.add_argument(
        "--n-merchants",
        type=int,
        default=int(os.environ.get("MESHEK_TRAIN_N_MERCHANTS", "20")),
        help="Number of synthetic merchants to simulate (default: 20).",
    )
    p.add_argument(
        "--days",
        type=int,
        default=int(os.environ.get("MESHEK_TRAIN_DAYS", "180")),
        help="Number of days of history to simulate (default: 180).",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=Path(os.environ.get("MESHEK_TRAIN_OUTPUT", "models/lightgbm_v1.bundle")),
        help="Destination path for the model bundle (default: models/lightgbm_v1.bundle).",
    )
    p.add_argument(
        "--start-date",
        type=str,
        default="2024-01-01",
        help="Simulation start date ISO YYYY-MM-DD (default: 2024-01-01).",
    )
    return p.parse_args()


def main() -> None:
    """Train a LightGBM bundle and emit a JSON summary line on success."""
    args = _parse_args()

    # run_simulation takes start_date + end_date; convert --days to end_date.
    start = date.fromisoformat(args.start_date)
    end = start + timedelta(days=args.days - 1)

    # Late imports: surfaces missing-package errors at run time with a clean trace.
    from meshek_ml.simulation.generator import run_simulation
    from meshek_ml.recommendation.training import train_and_save

    data = run_simulation(
        n_merchants=args.n_merchants,
        start_date=args.start_date,
        end_date=end.isoformat(),
        seed=args.seed,
    )

    bundle = train_and_save(args.output, data)

    summary = {
        "bundle_path": str(args.output.resolve()),
        "residual_std": bundle["residual_std"],
        "feature_count": len(bundle["feature_cols"]),
        "row_count": len(data),
        "seed": args.seed,
        "n_merchants": args.n_merchants,
        "days": args.days,
    }
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
