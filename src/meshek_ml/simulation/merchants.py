"""Merchant archetype generation using Faker."""

from __future__ import annotations

from meshek_ml.common.types import MerchantArchetype
from meshek_ml.simulation.schemas import MerchantProfile

# Archetype definitions: (location_type, demand_scale, n_products_range)
ARCHETYPE_SPECS: dict[MerchantArchetype, dict] = {
    MerchantArchetype.SMALL_URBAN_BOUTIQUE: {
        "location_type": "urban",
        "demand_scale": 0.7,
        "n_products": (30, 50),
        "daily_customers": (50, 100),
    },
    MerchantArchetype.MEDIUM_SUBURBAN: {
        "location_type": "suburban",
        "demand_scale": 1.5,
        "n_products": (60, 100),
        "daily_customers": (100, 200),
    },
    MerchantArchetype.MARKET_STALL: {
        "location_type": "rural",
        "demand_scale": 0.5,
        "n_products": (15, 30),
        "daily_customers": (30, 80),
    },
    MerchantArchetype.CORNER_SHOP: {
        "location_type": "urban",
        "demand_scale": 0.8,
        "n_products": (20, 40),
        "daily_customers": (40, 90),
    },
}


def generate_merchants(
    n_merchants: int = 10,
    seed: int = 42,
) -> list[MerchantProfile]:
    """Generate merchant profiles with diverse archetypes.

    Args:
        n_merchants: Number of merchants to generate.
        seed: Random seed for reproducibility.

    Returns:
        List of MerchantProfile instances.
    """
    from faker import Faker

    fake = Faker("he_IL")
    Faker.seed(seed)

    archetypes = list(MerchantArchetype)
    merchants = []

    for i in range(n_merchants):
        archetype = archetypes[i % len(archetypes)]
        spec = ARCHETYPE_SPECS[archetype]

        merchant = MerchantProfile(
            merchant_id=f"merchant_{i:03d}",
            name=fake.company(),
            archetype=archetype,
            location_type=spec["location_type"],
            demand_scale=spec["demand_scale"],
            latitude=31.5 + fake.pyfloat(min_value=0, max_value=2),
            longitude=34.3 + fake.pyfloat(min_value=0, max_value=1.5),
        )
        merchants.append(merchant)

    return merchants
