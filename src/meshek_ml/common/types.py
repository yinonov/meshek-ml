"""Shared type definitions and enums."""

from __future__ import annotations

from enum import Enum


class ProductCategory(str, Enum):
    """Categories of perishable produce."""

    TOMATOES = "tomatoes"
    CUCUMBERS = "cucumbers"
    LETTUCE = "lettuce"
    STRAWBERRIES = "strawberries"
    BANANAS = "bananas"
    APPLES = "apples"
    POTATOES = "potatoes"
    CITRUS = "citrus"
    BERRIES = "berries"
    ROOT_VEGETABLES = "root_vegetables"
    LEAFY_GREENS = "leafy_greens"
    EXOTIC = "exotic"


class MerchantArchetype(str, Enum):
    """Merchant store archetypes with distinct demand profiles."""

    SMALL_URBAN_BOUTIQUE = "small_urban_boutique"
    MEDIUM_SUBURBAN = "medium_suburban"
    MARKET_STALL = "market_stall"
    CORNER_SHOP = "corner_shop"


class SeasonType(str, Enum):
    """Season classification for demand patterns."""

    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


# Type aliases
MetricsDict = dict[str, float]
