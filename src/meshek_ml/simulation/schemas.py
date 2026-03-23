"""Data schemas for simulation output."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from meshek_ml.common.types import MerchantArchetype, ProductCategory


@dataclass
class ProductSpec:
    """Specification for a simulated product."""

    category: ProductCategory
    name: str
    base_demand_mean: float
    dispersion: float
    shelf_life_days: int
    purchase_cost: float
    selling_price: float
    seasonal_amplitude: float = 0.3
    peak_month: int | None = None  # 1-12, None for no seasonal peak


@dataclass
class MerchantProfile:
    """Profile of a simulated merchant."""

    merchant_id: str
    name: str
    archetype: MerchantArchetype
    location_type: str  # urban, suburban, rural
    demand_scale: float
    product_ids: list[str] = field(default_factory=list)
    latitude: float = 32.0
    longitude: float = 34.8


@dataclass
class DailyDemandRecord:
    """A single day's demand record for one product at one merchant."""

    date: date
    merchant_id: str
    product_id: str
    base_demand: float
    seasonal_factor: float
    weekly_factor: float
    holiday_factor: float
    adjusted_demand: float
    realized_demand: int


@dataclass
class InventorySnapshot:
    """Inventory state at end of day for one product at one merchant."""

    date: date
    merchant_id: str
    product_id: str
    stock_on_hand: int
    units_sold: int
    units_wasted: int
    units_ordered: int
    stockout_quantity: int
