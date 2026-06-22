import numpy as np
import pandas as pd
from typing import Optional


class PositionSizer:
    """Calculate position sizes using various methods.

    Methods:
        fixed_fraction  — fixed % of portfolio (default 5%)
        kelly           — Kelly criterion (use fractional Kelly to limit risk)
        volatility_scaled — size inversely proportional to asset volatility
    """

    METHODS = ("fixed_fraction", "kelly", "volatility_scaled")

    def __init__(
        self,
        method: str = "fixed_fraction",
        fraction: float = 0.05,
        kelly_multiplier: float = 0.25,
        vol_target: float = 0.10,
        max_position: float = 0.10,
    ):
        if method not in self.METHODS:
            raise ValueError(f"method must be one of {self.METHODS}")
        self.method = method
        self.fraction = fraction
        self.kelly_multiplier = kelly_multiplier
        self.vol_target = vol_target
        self.max_position = max_position

    def size(
        self,
        portfolio_value: float,
        price: float,
        returns: Optional[pd.Series] = None,
        win_rate: Optional[float] = None,
        avg_win: Optional[float] = None,
        avg_loss: Optional[float] = None,
    ) -> int:
        """Return number of shares to trade (always a non-negative integer)."""
        if self.method == "fixed_fraction":
            frac = min(self.fraction, self.max_position)

        elif self.method == "kelly":
            if any(v is None for v in [win_rate, avg_win, avg_loss]):
                raise ValueError("kelly requires win_rate, avg_win, avg_loss")
            if avg_loss == 0:
                frac = 0.0
            else:
                kelly_f = win_rate - (1 - win_rate) / (avg_win / abs(avg_loss))
                frac = max(0.0, kelly_f) * self.kelly_multiplier
            frac = min(frac, self.max_position)

        elif self.method == "volatility_scaled":
            if returns is None:
                raise ValueError("volatility_scaled requires returns Series")
            daily_vol = returns.std()
            annual_vol = daily_vol * np.sqrt(252)
            frac = self.vol_target / annual_vol if annual_vol > 0 else self.fraction
            frac = min(frac, self.max_position)

        position_value = portfolio_value * frac
        shares = int(position_value / price)
        return max(0, shares)
