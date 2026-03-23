"""Generate synthetic perishable goods data."""

from meshek_ml.common.io import save_parquet
from meshek_ml.common.seed import set_global_seed
from meshek_ml.simulation.generator import run_simulation


def main():
    set_global_seed(42)
    df = run_simulation(
        n_merchants=10,
        start_date="2023-01-01",
        end_date="2024-12-31",
        seed=42,
    )
    path = save_parquet(df, "data/synthetic/demand.parquet")
    print(f"Generated {len(df)} records -> {path}")


if __name__ == "__main__":
    main()
