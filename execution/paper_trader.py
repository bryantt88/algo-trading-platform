"""
Alpaca paper trading integration.

Setup:
  1. Create a free account at https://alpaca.markets
  2. Generate paper trading API keys (Dashboard → API Keys → Paper)
  3. Add to .env:
       ALPACA_API_KEY=...
       ALPACA_SECRET_KEY=...
       ALPACA_BASE_URL=https://paper-api.alpaca.markets

Install: pip install alpaca-py
"""
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class PaperTrader:
    """Alpaca paper trading client.

    Use this after a strategy clears Gate 1 (backtest) to validate
    real-world execution before risking capital.
    """

    def __init__(self):
        from alpaca.trading.client import TradingClient
        from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce

        self._MarketOrderRequest = MarketOrderRequest
        self._LimitOrderRequest = LimitOrderRequest
        self._OrderSide = OrderSide
        self._TimeInForce = TimeInForce

        api_key = os.getenv("ALPACA_API_KEY")
        secret = os.getenv("ALPACA_SECRET_KEY")
        base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

        if not api_key or not secret:
            raise EnvironmentError("ALPACA_API_KEY and ALPACA_SECRET_KEY must be set in .env")
        if "paper" not in base_url:
            raise EnvironmentError(
                "PaperTrader requires paper endpoint. "
                "Set ALPACA_BASE_URL=https://paper-api.alpaca.markets"
            )

        self.client = TradingClient(api_key, secret, paper=True)
        logger.info("PaperTrader ready (paper mode)")

    def get_account(self) -> dict:
        a = self.client.get_account()
        return {
            "equity": float(a.equity),
            "cash": float(a.cash),
            "portfolio_value": float(a.portfolio_value),
            "buying_power": float(a.buying_power),
        }

    def buy(self, symbol: str, qty: int) -> dict:
        return self._submit(symbol, qty, "buy")

    def sell(self, symbol: str, qty: int) -> dict:
        return self._submit(symbol, qty, "sell")

    def _submit(self, symbol: str, qty: int, side: str) -> dict:
        side_enum = self._OrderSide.BUY if side == "buy" else self._OrderSide.SELL
        req = self._MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=side_enum,
            time_in_force=self._TimeInForce.DAY,
        )
        order = self.client.submit_order(req)
        logger.info(f"[paper] {side.upper()} {qty} {symbol} — {order.id}")
        return {"id": str(order.id), "symbol": symbol, "qty": qty, "side": side, "status": order.status.value}

    def get_positions(self) -> list:
        return [
            {
                "symbol": p.symbol,
                "qty": int(p.qty),
                "avg_entry": float(p.avg_entry_price),
                "market_value": float(p.market_value),
                "unrealized_pl": float(p.unrealized_pl),
                "unrealized_plpc": float(p.unrealized_plpc),
            }
            for p in self.client.get_all_positions()
        ]

    def close_all(self) -> None:
        self.client.close_all_positions(cancel_orders=True)
        logger.info("[paper] All positions closed")
