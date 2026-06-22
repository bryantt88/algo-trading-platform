import pandas as pd
from strategies.base import BaseStrategy


class MACDStrategy(BaseStrategy):
    """MACD line / signal line crossover.

    Buy when MACD crosses above signal; sell (flat) when it crosses below.
    Long-only by default (set allow_short=True in config for long/short).
    """

    DEFAULTS = {"fast": 12, "slow": 26, "signal": 9, "allow_short": False}

    def __init__(self, symbol: str, config: dict = None):
        super().__init__(symbol, {**self.DEFAULTS, **(config or {})})

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        self.validate_data(data)
        c = data["Close"]
        ema_fast = c.ewm(span=self.config["fast"], adjust=False).mean()
        ema_slow = c.ewm(span=self.config["slow"], adjust=False).mean()
        macd = ema_fast - ema_slow
        sig = macd.ewm(span=self.config["signal"], adjust=False).mean()

        above = (macd > sig).astype(int)
        if not self.config["allow_short"]:
            return above  # 1 when long, 0 when flat
        return above * 2 - 1  # +1 long, -1 short


class EMACrossoverStrategy(BaseStrategy):
    """Dual EMA crossover (e.g. 50/200 golden cross).

    Long when fast EMA > slow EMA, flat (or short) otherwise.
    """

    DEFAULTS = {"fast": 50, "slow": 200, "allow_short": False}

    def __init__(self, symbol: str, config: dict = None):
        super().__init__(symbol, {**self.DEFAULTS, **(config or {})})

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        self.validate_data(data)
        c = data["Close"]
        ema_fast = c.ewm(span=self.config["fast"], adjust=False).mean()
        ema_slow = c.ewm(span=self.config["slow"], adjust=False).mean()

        above = (ema_fast > ema_slow).astype(int)
        if not self.config["allow_short"]:
            return above
        return above * 2 - 1


class RSIMomentumStrategy(BaseStrategy):
    """RSI-based momentum: buy when RSI crosses above oversold, sell when overbought.

    Long-only by default.
    """

    DEFAULTS = {"period": 14, "oversold": 30, "overbought": 70}

    def __init__(self, symbol: str, config: dict = None):
        super().__init__(symbol, {**self.DEFAULTS, **(config or {})})

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        self.validate_data(data)
        delta = data["Close"].diff()
        gain = delta.clip(lower=0).rolling(self.config["period"]).mean()
        loss = (-delta.clip(upper=0)).rolling(self.config["period"]).mean()
        rs = gain / loss.replace(0, float("inf"))
        rsi = 100 - (100 / (1 + rs))

        long_signal = (rsi < self.config["oversold"]).astype(int)
        exit_signal = (rsi > self.config["overbought"]).astype(int)
        position = pd.Series(0, index=data.index)
        in_trade = False
        for i in range(len(data)):
            if not in_trade and long_signal.iloc[i]:
                in_trade = True
            elif in_trade and exit_signal.iloc[i]:
                in_trade = False
            position.iloc[i] = 1 if in_trade else 0
        return position
