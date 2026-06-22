import yfinance as yf
import pandas as pd
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)


def fetch_ohlcv(
    symbol: str,
    start: str,
    end: Optional[str] = None,
    interval: str = "1d",
    use_cache: bool = True,
) -> pd.DataFrame:
    """Fetch OHLCV data from yfinance, cached to parquet.

    Args:
        symbol: Ticker (e.g. 'AAPL', 'SPY', 'BTC-USD')
        start:  'YYYY-MM-DD'
        end:    'YYYY-MM-DD' or None for today
        interval: '1d', '1h', '30m', '15m', '5m', '1m'
        use_cache: Read from/write to data/cache/ as parquet

    Returns:
        DataFrame with columns Open/High/Low/Close/Volume and DatetimeIndex (tz-naive)
    """
    cache_key = f"{symbol.replace('/', '-')}_{start}_{end or 'today'}_{interval}.parquet"
    cache_path = CACHE_DIR / cache_key

    if use_cache and cache_path.exists():
        logger.info(f"[cache] {symbol} {interval}")
        return pd.read_parquet(cache_path)

    logger.info(f"[fetch] {symbol} {start} → {end or 'today'} ({interval})")
    ticker = yf.Ticker(symbol)
    data = ticker.history(start=start, end=end, interval=interval, auto_adjust=True)

    if data.empty:
        raise ValueError(f"yfinance returned no data for {symbol!r} ({start} – {end})")

    data = data[["Open", "High", "Low", "Close", "Volume"]].copy()
    data.index = pd.to_datetime(data.index).tz_localize(None)

    if use_cache:
        data.to_parquet(cache_path)

    return data


def fetch_multiple(symbols: list, start: str, end: Optional[str] = None) -> dict:
    """Fetch OHLCV for multiple symbols. Returns {symbol: DataFrame}."""
    result = {}
    for sym in symbols:
        try:
            result[sym] = fetch_ohlcv(sym, start, end)
        except Exception as e:
            logger.warning(f"Failed to fetch {sym}: {e}")
    return result


def get_benchmark(start: str, end: Optional[str] = None) -> pd.DataFrame:
    """SPY as the default benchmark."""
    return fetch_ohlcv("SPY", start, end)


def clean(data: pd.DataFrame) -> pd.DataFrame:
    """Drop NaN rows, sort by date, remove duplicate index entries."""
    data = data.sort_index()
    data = data[~data.index.duplicated(keep="last")]
    data = data.dropna()
    return data
