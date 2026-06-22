# Project Status & Roadmap

_Last updated: 2026-06-22_

## ✅ Done
- **Framework**: phase-gate engine (Backtest→Paper→Live), vectorized backtester with 1-bar lag + costs,
  risk/position sizing, Alpaca paper/live execution, starter strategies (MACD, EMA, RSI).
- **Tooling**: Streamlit dashboard (`dashboard/app.py`), 3 agents + 3 skills (`.claude/`),
  MCP config (`.mcp.json`: GitHub + Alpaca), TradingView MCP installed.
- **Portfolio**: pushed public → https://github.com/bryantt88/algo-trading-platform (branch `main`).
- **Verified**: 12/12 tests pass; engine smoke-tested; Alpaca paper account live ($100k, ACTIVE).

## ⚙️ Environment notes
- **Deps**: lean venv `.venv` is **fully installed and verified** (12/12 tests pass in-venv; no
  torch/transformers — sentiment deferred). Just `.venv\Scripts\activate` and go. Key versions:
  pandas 3.0, numpy 2.2, streamlit 1.58, alpaca-py 0.43, statsmodels 0.14, xgboost 3.3, quantstats 0.0.81.
- **Alpaca**: keys in `.env` (gitignored) and as Windows user env vars — **restart terminal/VS Code**
  so the Alpaca MCP picks them up.
- **TradingView MCP**: installed at `C:\Users\Bryant Effendi\mcp-servers\tradingview-mcp`. For live data,
  launch TradingView Desktop with `--remote-debugging-port=9222`.

## 🎯 Current focus
Full **quant + price action**. NLP/sentiment is deferred.

## 🔜 Next steps
1. **Donchian breakout** — first real strategy. Run: `strategy-researcher` → `new-strategy` →
   `run-backtest` → `quant-reviewer`. Validates the whole pipeline end-to-end against Gate 1.
2. **Pairs trading / stat-arb** (cointegration via `statsmodels`) — the quant centerpiece.

## ▶️ How to run
```bash
.venv\Scripts\activate
python -m pytest tests/ -v          # verify framework
streamlit run dashboard/app.py       # interactive dashboard
```
