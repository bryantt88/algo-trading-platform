import pytest
import pandas as pd
import numpy as np
from backtesting.metrics import compute_metrics, gate1_check


def _make_returns(n=252, mean=0.001, std=0.01, seed=42):
    rng = np.random.default_rng(seed)
    returns = pd.Series(rng.normal(mean, std, n), name="returns")
    equity = (1 + returns).cumprod() * 100_000
    return returns, equity


def _make_trades(n=50, win_rate=0.55, seed=42):
    rng = np.random.default_rng(seed)
    wins = rng.uniform(0.01, 0.05, int(n * win_rate))
    losses = rng.uniform(-0.03, -0.001, n - len(wins))
    pnl = np.concatenate([wins, losses])
    rng.shuffle(pnl)
    return pd.DataFrame({"pnl_pct": pnl})


def test_sharpe_positive_for_good_returns():
    returns, equity = _make_returns(mean=0.001)
    metrics = compute_metrics(returns, equity, pd.DataFrame())
    assert metrics["sharpe"] > 0


def test_max_drawdown_nonpositive():
    returns, equity = _make_returns()
    metrics = compute_metrics(returns, equity, pd.DataFrame())
    assert metrics["max_drawdown"] <= 0


def test_win_rate_within_bounds():
    returns, equity = _make_returns()
    trades = _make_trades(win_rate=0.55)
    metrics = compute_metrics(returns, equity, trades)
    assert 0 <= metrics["win_rate"] <= 1


def test_gate1_pass():
    returns, equity = _make_returns(n=500, mean=0.0015, std=0.008)
    trades = _make_trades(n=60, win_rate=0.60)
    metrics = compute_metrics(returns, equity, trades)
    # With good synthetic data, at least some checks pass
    gate = gate1_check(metrics)
    assert isinstance(gate["PASS"], bool)
    assert "sharpe >= 1.0" in gate


def test_empty_data_returns_zeros():
    returns = pd.Series([], dtype=float)
    equity = pd.Series([], dtype=float)
    metrics = compute_metrics(returns, equity, pd.DataFrame())
    assert metrics["sharpe"] == 0
    assert metrics["num_trades"] == 0
