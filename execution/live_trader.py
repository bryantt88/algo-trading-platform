"""
⚠️  LIVE TRADING MODULE — REAL CAPITAL AT RISK ⚠️

Prerequisites before using this module:
  1. Strategy has passed Gate 1 (backtest) AND Gate 2 (30+ days paper trading)
  2. You have reviewed the risk rules in CLAUDE.md
  3. .env has ALPACA_BASE_URL=https://api.alpaca.markets (live endpoint)
  4. Start with ≤ 10% of your intended allocation
  5. Kill switch: max daily loss = 3% of session-start equity

Never call submit_order() without first calling check_kill_switch().
"""
import os
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

MAX_DAILY_LOSS_PCT = 0.03
MAX_POSITION_PCT = 0.10


class LiveTrader:
    """Alpaca live trading client with mandatory kill switch.

    Kill switch fires if daily P&L < -3% of session-start equity.
    When triggered it closes all positions and halts trading.
    """

    def __init__(self):
        from alpaca.trading.client import TradingClient
        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce

        self._MarketOrderRequest = MarketOrderRequest
        self._OrderSide = OrderSide
        self._TimeInForce = TimeInForce

        api_key = os.getenv("ALPACA_API_KEY")
        secret = os.getenv("ALPACA_SECRET_KEY")
        base_url = os.getenv("ALPACA_BASE_URL", "")

        if "paper" in base_url or not base_url:
            raise EnvironmentError(
                "LiveTrader requires live endpoint. "
                "Set ALPACA_BASE_URL=https://api.alpaca.markets in .env"
            )
        if not api_key or not secret:
            raise EnvironmentError("Set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env")

        self.client = TradingClient(api_key, secret, paper=False)
        self._session_start_equity = float(self.client.get_account().equity)
        self._killed = False

        logger.warning(f"LIVE TRADER STARTED — equity: ${self._session_start_equity:,.2f}")
        self._log("SESSION_START", {"equity": self._session_start_equity})

    def check_kill_switch(self) -> bool:
        """Returns True if kill switch has triggered (trading halted)."""
        if self._killed:
            return True
        equity = float(self.client.get_account().equity)
        daily_loss = (equity - self._session_start_equity) / self._session_start_equity
        if daily_loss < -MAX_DAILY_LOSS_PCT:
            logger.critical(f"KILL SWITCH: daily loss {daily_loss:.1%} — closing all positions")
            self.client.close_all_positions(cancel_orders=True)
            self._killed = True
            self._log("KILL_SWITCH", {"daily_loss_pct": daily_loss, "equity": equity})
            return True
        return False

    def submit_order(self, symbol: str, qty: int, side: str) -> dict:
        """Submit a live market order. Checks kill switch first."""
        if self.check_kill_switch():
            raise RuntimeError("Kill switch active — no new orders allowed this session")
        side_enum = self._OrderSide.BUY if side == "buy" else self._OrderSide.SELL
        req = self._MarketOrderRequest(
            symbol=symbol, qty=qty, side=side_enum, time_in_force=self._TimeInForce.DAY
        )
        order = self.client.submit_order(req)
        logger.warning(f"[LIVE] {side.upper()} {qty} {symbol} — {order.id}")
        self._log("ORDER", {"symbol": symbol, "qty": qty, "side": side, "order_id": str(order.id)})
        return {"id": str(order.id), "symbol": symbol, "qty": qty, "side": side, "status": order.status.value}

    def get_account(self) -> dict:
        a = self.client.get_account()
        return {"equity": float(a.equity), "cash": float(a.cash), "buying_power": float(a.buying_power)}

    def _log(self, event: str, data: dict) -> None:
        log_file = LOG_DIR / f"live_{datetime.now().strftime('%Y%m%d')}.log"
        with open(log_file, "a") as f:
            f.write(f"{datetime.now().isoformat()} | {event} | {data}\n")
