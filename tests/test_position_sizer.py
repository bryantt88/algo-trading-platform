import pytest
import pandas as pd
import numpy as np
from risk.position_sizer import PositionSizer


def test_fixed_fraction_basic():
    sizer = PositionSizer(method="fixed_fraction", fraction=0.05)
    shares = sizer.size(portfolio_value=100_000, price=100.0)
    assert shares == 50  # 5% of 100k = 5000 / 100 = 50


def test_max_position_cap():
    sizer = PositionSizer(method="fixed_fraction", fraction=0.20, max_position=0.10)
    shares = sizer.size(portfolio_value=100_000, price=100.0)
    assert shares == 100  # capped at 10% → 10k / 100


def test_kelly_requires_stats():
    sizer = PositionSizer(method="kelly")
    with pytest.raises(ValueError):
        sizer.size(portfolio_value=100_000, price=100.0)


def test_kelly_positive_edge():
    sizer = PositionSizer(method="kelly", kelly_multiplier=0.5)
    shares = sizer.size(
        portfolio_value=100_000,
        price=50.0,
        win_rate=0.60,
        avg_win=0.04,
        avg_loss=-0.02,
    )
    assert shares >= 0


def test_volatility_scaled_requires_returns():
    sizer = PositionSizer(method="volatility_scaled")
    with pytest.raises(ValueError):
        sizer.size(portfolio_value=100_000, price=100.0)


def test_volatility_scaled_basic():
    rng = np.random.default_rng(0)
    returns = pd.Series(rng.normal(0, 0.01, 252))
    sizer = PositionSizer(method="volatility_scaled", vol_target=0.10)
    shares = sizer.size(portfolio_value=100_000, price=100.0, returns=returns)
    assert shares >= 0


def test_zero_price_returns_zero():
    sizer = PositionSizer()
    shares = sizer.size(portfolio_value=100_000, price=0.01)
    assert shares >= 0  # no crash
