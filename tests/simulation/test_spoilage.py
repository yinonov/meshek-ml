"""Tests for spoilage model and FIFO inventory."""

from meshek_ml.simulation.spoilage import FIFOInventory, weibull_quality


def test_weibull_quality_decreases_with_age():
    q0 = weibull_quality(0, shape=2.0, scale=5.0)
    q3 = weibull_quality(3, shape=2.0, scale=5.0)
    q7 = weibull_quality(7, shape=2.0, scale=5.0)
    assert q0 > q3 > q7


def test_fifo_sell_oldest_first():
    inv = FIFOInventory(max_shelf_life=7)
    inv.receive(10)  # batch A, age 0
    inv.age_and_expire()  # batch A now age 1
    inv.receive(5)  # batch B, age 0
    sold, unmet = inv.sell(8)
    assert sold == 8
    assert unmet == 0
    # Batch A should have 2 left, batch B should have 5
    assert inv.total_stock == 7


def test_fifo_expiration():
    inv = FIFOInventory(max_shelf_life=2)
    inv.receive(10)
    inv.age_and_expire()  # age 1
    inv.age_and_expire()  # age 2
    wasted = inv.age_and_expire()  # age 3 > max_shelf_life=2
    assert wasted == 10
    assert inv.total_stock == 0


def test_fifo_stockout():
    inv = FIFOInventory(max_shelf_life=7)
    inv.receive(5)
    sold, unmet = inv.sell(10)
    assert sold == 5
    assert unmet == 5
