import pandas as pd
import numpy as np
from typing import Dict


def compute_metrics(
    returns: pd.Series,
    equity_curve: pd.Series,
    trades: pd.DataFrame,
    ann_factor: int = 252,
) -> Dict:
    """Compute a standard set of backtesting performance metrics."""
    returns = returns.dropna()
    if len(returns) == 0:
        return _empty_metrics()

    total_return = equity_curve.iloc[-1] / equity_curve.iloc[0] - 1
    n_years = len(returns) / ann_factor
    annual_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0

    daily_std = returns.std()
    annual_vol = daily_std * np.sqrt(ann_factor)
    sharpe = annual_return / annual_vol if annual_vol > 0 else 0

    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    calmar = annual_return / abs(max_drawdown) if max_drawdown < 0 else float("inf")

    downside_returns = returns[returns < 0]
    downside_std = downside_returns.std() * np.sqrt(ann_factor)
    sortino = annual_return / downside_std if downside_std > 0 else 0

    if len(trades) > 0 and "pnl_pct" in trades.columns:
        wins = trades.loc[trades["pnl_pct"] > 0, "pnl_pct"]
        losses = trades.loc[trades["pnl_pct"] <= 0, "pnl_pct"]
        win_rate = len(wins) / len(trades)
        profit_factor = wins.sum() / abs(losses.sum()) if len(losses) > 0 and losses.sum() != 0 else float("inf")
        avg_win = wins.mean() if len(wins) > 0 else 0.0
        avg_loss = losses.mean() if len(losses) > 0 else 0.0
        expectancy = win_rate * avg_win + (1 - win_rate) * avg_loss
    else:
        win_rate = profit_factor = avg_win = avg_loss = expectancy = 0

    return {
        "total_return": total_return,
        "annual_return": annual_return,
        "annual_volatility": annual_vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "expectancy": expectancy,
        "num_trades": len(trades),
        "n_days": len(returns),
    }


def gate1_check(metrics: Dict) -> Dict:
    """Check if metrics clear Gate 1 requirements for paper trading promotion."""
    checks = {
        "sharpe >= 1.0": metrics["sharpe"] >= 1.0,
        "max_drawdown <= 20%": metrics["max_drawdown"] >= -0.20,
        "profit_factor >= 1.5": metrics["profit_factor"] >= 1.5,
        "win_rate >= 50%": metrics["win_rate"] >= 0.50,
        "num_trades >= 30": metrics["num_trades"] >= 30,
    }
    checks["PASS"] = all(checks.values())
    return checks


def print_metrics(metrics: Dict, gate: Dict = None) -> None:
    """Pretty-print metrics to console."""
    print("\n===== Backtest Results =====")
    print(f"  Total Return:     {metrics['total_return']:>8.1%}")
    print(f"  Annual Return:    {metrics['annual_return']:>8.1%}")
    print(f"  Annual Vol:       {metrics['annual_volatility']:>8.1%}")
    print(f"  Sharpe Ratio:     {metrics['sharpe']:>8.2f}")
    print(f"  Sortino Ratio:    {metrics['sortino']:>8.2f}")
    print(f"  Calmar Ratio:     {metrics['calmar']:>8.2f}")
    print(f"  Max Drawdown:     {metrics['max_drawdown']:>8.1%}")
    print(f"  Win Rate:         {metrics['win_rate']:>8.1%}")
    print(f"  Profit Factor:    {metrics['profit_factor']:>8.2f}")
    print(f"  Num Trades:       {metrics['num_trades']:>8}")
    if gate:
        print("\n===== Gate 1 Check =====")
        for k, v in gate.items():
            if k != "PASS":
                print(f"  {'✓' if v else '✗'} {k}")
        print(f"\n  {'>>> PASS <<<' if gate['PASS'] else '>>> FAIL <<<'}")
    print()


def _empty_metrics() -> Dict:
    keys = ["total_return", "annual_return", "annual_volatility", "sharpe", "sortino",
            "calmar", "max_drawdown", "win_rate", "profit_factor", "avg_win",
            "avg_loss", "expectancy", "num_trades", "n_days"]
    return {k: 0 for k in keys}
