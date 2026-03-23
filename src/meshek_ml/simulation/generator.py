"""Simulation orchestrator: generates complete synthetic datasets."""

from __future__ import annotations

import pandas as pd

from meshek_ml.common.types import ProductCategory
from meshek_ml.simulation.demand import generate_demand
from meshek_ml.simulation.merchants import generate_merchants
from meshek_ml.simulation.schemas import MerchantProfile, ProductSpec

# Default product catalog for a small greengrocer
DEFAULT_PRODUCTS: list[ProductSpec] = [
    ProductSpec(ProductCategory.TOMATOES, "Tomatoes", 20.0, 3.0, 6, 5.0, 7.0, 0.3, peak_month=7),
    ProductSpec(ProductCategory.BANANAS, "Bananas", 15.0, 2.0, 5, 3.0, 5.0, 0.15, peak_month=None),
    ProductSpec(
        ProductCategory.STRAWBERRIES, "Strawberries", 8.0, 2.5, 3, 8.0, 14.0, 0.6, peak_month=5
    ),
    ProductSpec(ProductCategory.LETTUCE, "Lettuce", 15.0, 2.5, 4, 2.0, 4.0, 0.25, peak_month=6),
    ProductSpec(ProductCategory.APPLES, "Apples", 18.0, 2.0, 30, 3.0, 5.5, 0.2, peak_month=10),
    ProductSpec(
        ProductCategory.POTATOES, "Potatoes", 22.0, 2.0, 60, 2.0, 3.5, 0.15, peak_month=None
    ),
    ProductSpec(ProductCategory.CITRUS, "Oranges", 14.0, 2.5, 14, 4.0, 6.0, 0.4, peak_month=1),
    ProductSpec(ProductCategory.EXOTIC, "Dragon Fruit", 2.0, 1.5, 6, 12.0, 20.0, 0.1, peak_month=8),
]


def run_simulation(
    n_merchants: int = 10,
    products: list[ProductSpec] | None = None,
    start_date: str = "2023-01-01",
    end_date: str = "2024-12-31",
    seed: int = 42,
) -> pd.DataFrame:
    """Generate a complete synthetic dataset.

    Args:
        n_merchants: Number of merchants to simulate.
        products: Product catalog. Defaults to DEFAULT_PRODUCTS.
        start_date: Simulation start date (YYYY-MM-DD).
        end_date: Simulation end date (YYYY-MM-DD).
        seed: Random seed.

    Returns:
        DataFrame with columns: date, merchant_id, product, base_demand,
        seasonal_factor, weekly_factor, holiday_factor, adjusted_demand,
        realized_demand.
    """
    import numpy as np

    if products is None:
        products = DEFAULT_PRODUCTS

    rng = np.random.default_rng(seed)
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    merchants: list[MerchantProfile] = generate_merchants(n_merchants, seed=seed)

    all_records = []
    for merchant in merchants:
        for product in products:
            df = generate_demand(
                product=product,
                dates=dates,
                merchant_scale=merchant.demand_scale,
                rng=rng,
            )
            df["merchant_id"] = merchant.merchant_id
            df["product"] = product.name
            all_records.append(df)

    return pd.concat(all_records, ignore_index=True)
