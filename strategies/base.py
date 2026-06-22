from abc import ABC, abstractmethod
import pandas as pd


class BaseStrategy(ABC):
    """Abstract base for all trading strategies.

    Subclass this and implement generate_signals().
    The engine calls validate_data() automatically before running.
    """

    def __init__(self, symbol: str, config: dict = None):
        self.symbol = symbol
        self.config = config or {}
        self.name = self.__class__.__name__

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Return a Series of raw signals aligned to data.index.

        Values: +1 = long, -1 = short, 0 = flat.
        The engine shifts this by 1 bar before calculating returns — do NOT pre-shift here.
        """
        pass

    def validate_data(self, data: pd.DataFrame) -> None:
        required = {"Open", "High", "Low", "Close", "Volume"}
        missing = required - set(data.columns)
        if missing:
            raise ValueError(f"Data missing columns: {missing}")
        if not isinstance(data.index, pd.DatetimeIndex):
            raise TypeError("data.index must be DatetimeIndex")
        if data.isnull().any().any():
            raise ValueError("Data contains NaN — run fetcher.clean() first")
        if len(data) < 30:
            raise ValueError(f"Too few rows ({len(data)}) — need at least 30")

    def get_config(self) -> dict:
        return {**self.config, "symbol": self.symbol, "strategy": self.name}
