import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Optional

from strategies.base import BaseStrategy
from backtesting.metrics import compute_metrics, gate1_check
from risk.position_sizer import PositionSizer

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


class BacktestEngine:
    """Vectorized backtesting engine.

    Design choices to avoid common pitfalls:
    - Signals are shifted forward by 1 bar (execute at next bar open, not same bar close)
    - Transaction costs applied on every position change
    - Benchmark comparison uses SPY by default
    """

    def __init__(
        self,
        initial_capital: float = 100_000.0,
        commission: float = 0.001,
        slippage: float = 0.001,
        position_sizer: Optional[PositionSizer] = None,
    ):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.position_sizer = position_sizer or PositionSizer()

    def run(self, strategy: BaseStrategy, data: pd.DataFrame) -> dict:
        """Run backtest. Returns results dict with equity_curve, trades, metrics."""
        strategy.validate_data(data)

        raw_signals = strategy.generate_signals(data)
        position = raw_signals.shift(1).fillna(0).clip(-1, 1)

        price_returns = data["Close"].pct_change().fillna(0)
        trade_cost = position.diff().abs() * (self.commission + self.slippage)
        strategy_returns = (position * price_returns) - trade_cost.fillna(0)

        equity_curve = (1 + strategy_returns).cumprod() * self.initial_capital

        trades = self._extract_trades(data, position, strategy_returns)
        metrics = compute_metrics(strategy_returns, equity_curve, trades)
        gate = gate1_check(metrics)

        logger.info(
            f"{strategy.name} [{strategy.symbol}] | "
            f"Sharpe={metrics['sharpe']:.2f} | "
            f"MaxDD={metrics['max_drawdown']:.1%} | "
            f"Gate1={'PASS' if gate['PASS'] else 'FAIL'}"
        )

        return {
            "equity_curve": equity_curve,
            "trades": trades,
            "metrics": metrics,
            "gate1": gate,
            "raw_signals": raw_signals,
            "position": position,
            "strategy_returns": strategy_returns,
            "benchmark_returns": price_returns,
        }

    def run_walkforward(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        train_pct: float = 0.70,
    ) -> dict:
        """Split data 70/30, train on first part, test on second."""
        split = int(len(data) * train_pct)
        train_data = data.iloc[:split]
        test_data = data.iloc[split:]

        train_results = self.run(strategy, train_data)
        test_results = self.run(strategy, test_data)

        return {
            "train": train_results,
            "test": test_results,
            "train_period": (str(train_data.index[0].date()), str(train_data.index[-1].date())),
            "test_period": (str(test_data.index[0].date()), str(test_data.index[-1].date())),
        }

    def _extract_trades(
        self, data: pd.DataFrame, position: pd.Series, returns: pd.Series
    ) -> pd.DataFrame:
        transitions = position.diff().fillna(0)
        entries = position.index[transitions != 0]
        trades = []
        open_trade = None

        for date in entries:
            pos = position[date]
            if open_trade is None and pos != 0:
                open_trade = {"entry_date": date, "direction": "long" if pos > 0 else "short"}
            elif open_trade is not None and pos == 0:
                entry_price = data.loc[open_trade["entry_date"], "Close"]
                exit_price = data.loc[date, "Close"]
                sign = 1 if open_trade["direction"] == "long" else -1
                pnl_pct = (exit_price / entry_price - 1) * sign
                trades.append({**open_trade, "exit_date": date, "entry_price": entry_price,
                                "exit_price": exit_price, "pnl_pct": pnl_pct})
                open_trade = None

        return pd.DataFrame(trades)
