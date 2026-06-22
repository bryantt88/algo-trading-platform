# Algorithmic Trading Project — Bryant Effendi

> ▶ **START HERE (every session):** Read [`docs/STATUS.md`](docs/STATUS.md) first — it has the current
> state, what's done, environment notes, and the next steps. Then follow the rules below.
>
> **Snapshot:** Public portfolio repo at https://github.com/bryantt88/algo-trading-platform (branch `main`).
> Current focus: **full quant + price action** (NLP/sentiment deferred). Framework + dashboard + MCP
> (GitHub, Alpaca-paper, TradingView) + custom agents/skills are built and verified. Alpaca paper account
> is live. Next: build the **Donchian breakout** strategy, then **pairs trading**.

## Project Purpose
Build a reliable pipeline to develop, backtest, paper trade, and live trade quantitative strategies.
Priority: accuracy and real-world applicability over speed of deployment.

---

## Phase Gate System

Every strategy must pass every gate in sequence. No skipping.

```
Research → Backtest (Gate 1) → Paper Trade (Gate 2) → Live (Gate 3)
```

### Gate 1 — Backtest Requirements
| Metric | Minimum |
|--------|---------|
| Sharpe Ratio (annualized) | ≥ 1.0 |
| Max Drawdown | ≤ 20% |
| Profit Factor | ≥ 1.5 |
| Win Rate | ≥ 50% |
| Number of trades | ≥ 30 |
| Backtest period | ≥ 252 trading days |

Additional: walk-forward validation (70/30 train/test), confirmed no lookahead bias.

### Gate 2 — Paper Trade Requirements
- Minimum 30 trading days on Alpaca paper account
- Live Sharpe ≥ 80% of backtest Sharpe
- No operational failures (data gaps, missed orders)

### Gate 3 — Live Trade Requirements
- Start with ≤ 10% of intended capital allocation
- 60 days consistent live performance before scaling
- Kill switch calibrated and tested

---

## Risk Management (NON-NEGOTIABLE)

- Max position size: 5% of portfolio per position
- Stop loss: 2% per trade (hard)
- Max daily portfolio loss: 3% (kill switch triggers close-all)
- Max concurrent positions: 20
- New position correlation with existing: |ρ| < 0.6
- Leverage: maximum 2x
- No trading 30 minutes before/after FOMC, earnings, or major macro releases
  (unless the strategy is explicitly designed for those events)

---

## File Structure

```
Algoritmic Trading Project/
├── CLAUDE.md                        ← this file
├── .claude/
│   └── settings.json               ← permissions, hooks, allowed commands
├── .env                             ← API keys (never commit)
├── .env.example                     ← template for env vars
├── .gitignore
├── requirements.txt
├── README.md
│
├── strategies/                      ← one file per strategy
│   ├── base.py                     ← BaseStrategy abstract class (all strategies inherit this)
│   ├── momentum.py                 ← MACD, EMA crossover, RSI momentum
│   ├── mean_reversion.py           ← Bollinger Bands, RSI extremes
│   ├── statistical_arb.py          ← Pairs trading, cointegration
│   └── ml_based.py                 ← ML-driven signals (XGBoost, feature pipeline)
│
├── backtesting/                     ← backtesting engine
│   ├── engine.py                   ← BacktestEngine class (vectorized)
│   ├── metrics.py                  ← compute_metrics(), gate1_check()
│   └── visualization.py            ← equity curve, drawdown chart, trade log chart
│
├── data/                            ← all data fetching and preprocessing
│   ├── fetcher.py                  ← fetch_ohlcv() with disk cache
│   ├── preprocessor.py             ← feature engineering helpers
│   └── cache/                      ← parquet cache files (gitignored)
│
├── risk/                            ← risk and position management
│   ├── position_sizer.py           ← PositionSizer (fixed_fraction / kelly / vol_scaled)
│   └── portfolio_monitor.py        ← live drawdown + correlation monitor
│
├── execution/                       ← broker integration
│   ├── paper_trader.py             ← Alpaca paper trading
│   └── live_trader.py              ← Alpaca live trading (⚠️ REAL MONEY)
│
├── configs/                         ← YAML config files per strategy
│   └── default.yaml                ← shared defaults
│
├── notebooks/                       ← Jupyter research notebooks (exploratory only)
├── logs/                            ← trade and execution logs (gitignored)
├── reports/                         ← backtest output charts + CSVs
└── tests/                           ← pytest unit tests
```

---

## Data Sources

| Source | Use Case | Cost |
|--------|----------|------|
| yfinance | Daily OHLCV for US equities, ETFs | Free |
| Alpaca Markets | Real-time data + paper/live execution | Free |
| Alpha Vantage | Better intraday (25 req/day free tier) | Free |
| LSEG (via MCP skill) | Fundamental data, macro signals — research only, not backtest loops | Firm subscription |

**Caching rule**: Always cache fetched OHLCV to `data/cache/` as parquet. Never re-download what you already have.

---

## Broker: Alpaca Markets

- Paper trading: `execution/paper_trader.py` — `ALPACA_BASE_URL=https://paper-api.alpaca.markets`
- Live trading: `execution/live_trader.py` — `ALPACA_BASE_URL=https://api.alpaca.markets`
- API keys: set in `.env` file (never hardcode, never commit)

---

## Coding Standards

1. All strategies must inherit `strategies/base.py::BaseStrategy`
2. **No lookahead bias**: always `signals.shift(1)` before computing returns
3. **Transaction costs mandatory**: default 0.1% commission + 0.1% slippage (in BacktestEngine)
4. Log all live/paper trades to `logs/` with ISO timestamp, symbol, action, price, qty
5. Tests required for: `metrics.py`, `position_sizer.py`, and any new strategy's `generate_signals()`
6. Use `python-dotenv` + `.env` for all secrets — no hardcoded keys anywhere

---

## Claude Skills to Use (Don't Re-Invent)

| Task | Use This |
|------|----------|
| Analyze backtest result CSV | `data:analyze` |
| Build equity curve dashboard | `data:build-dashboard` |
| Create charts/visuals | `data:create-viz` |
| Strategy statistical analysis | `data:statistical-analysis` |
| Fundamental context for a stock | `lseg:equity-research` |
| Macro + rates environment | `lseg:macro-rates-monitor` |
| Options/vol surface | `lseg:option-vol-analysis` |
| Research academic strategy ideas | `deep-research` |

---

## Custom Agents & Skills (this project)

**Agents** (`.claude/agents/`) — invoke for specialized analysis:
| Agent | When to use |
|-------|-------------|
| `quant-reviewer` | Before promoting any strategy past Gate 1 — audits for lookahead/survivorship bias, data snooping, missing costs, overfitting. |
| `strategy-researcher` | Before writing a new strategy — researches academic basis, edge decay, failure modes, proposes a `BaseStrategy`-compatible design. |
| `backtest-analyst` | After a backtest — skeptical statistical review (sample size, implausible Sharpe, regime dependence) on top of the raw gate check. |

**Skills** (`.claude/skills/`) — invoke for repeatable workflows:
| Skill | What it does |
|-------|--------------|
| `new-strategy` | Scaffolds `strategies/<name>.py` + config + test stub from `BaseStrategy`, registers it in `__init__` and the dashboard. |
| `run-backtest` | Standard Gate 1 backtest: fetch → engine → `gate1_check` → save report to `reports/`. |
| `gate-review` | Go/no-go decision against Gate 1/2/3 thresholds (reads `CLAUDE.md` + `configs/`). |

---

## Connected Tools (MCP)

Configured in `.mcp.json` (secrets via env vars, never committed):
| Server | Use for | Notes |
|--------|---------|-------|
| `github` | Repo, issues, PRs, code search | Official remote; OAuth via `/mcp`. This repo is a **public portfolio project**. |
| `alpaca` | Account, quotes, bars, paper orders | Official; **pinned to paper** (`ALPACA_PAPER_TRADE=true`). Live is a deliberate, separate switch. |
| `tradingview` | Chart/indicator/Pine analysis | Community (`tradesdontlie`, drives your TradingView Desktop). **Analysis only — NOT a backtest data source.** Registered locally, not committed. |

Backtest data comes from `data/fetcher.py` (yfinance) and Alpaca — never from TradingView scraping.

---

## Dashboard

Interactive Streamlit app at `dashboard/app.py`: `streamlit run dashboard/app.py`.
Reuses `data/fetcher`, `BacktestEngine`, and `gate1_check` — do not duplicate engine logic there.
When adding a new strategy, also add it to the `STRATEGIES` dict in `dashboard/app.py`.

---

## Reference: Prior Experiments

Existing trading code is in a separate directory:
`Desktop/Summer Project/`

Contains: `project.ipynb` (XGBoost + FinBERT momentum), `backtest.py`, `tradingbot.py`, `trade_log.csv`

Use as inspiration and reference. Do not directly import — refactor into this project's structure.

---

## Session Workflow (follow this order)

1. **Research**: Use `deep-research` skill or LSEG MCP to understand the strategy's theoretical basis
2. **Implement**: Create `strategies/<name>.py` inheriting `BaseStrategy`
3. **Backtest**: Run `backtesting/engine.py` — verify Gate 1 metrics with `gate1_check()`
4. **Analyze**: Use `data:analyze` skill on the results CSV
5. **Visualize**: Use `data:create-viz` or `data:build-dashboard`
6. **Walk-forward**: Run on out-of-sample period (last 30% of data)
7. **Paper trade**: Deploy to Alpaca paper, run 30+ days
8. **Gate 2 review**: Compare live vs backtest Sharpe
9. **Go live**: Only after manual Gate 3 sign-off

---

## Environment

- Windows 11, PowerShell primary shell
- Python 3.11+ with venv in `.venv/`
- Install: `python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt`
