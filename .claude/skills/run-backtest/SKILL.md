---
name: run-backtest
description: Run a standardized Gate 1 backtest for a strategy in this project and save a report. Use when the user wants to backtest a strategy, check its metrics, or see if it passes Gate 1. Handles data fetch, engine run, gate check, and report output.
---

# Run a Gate 1 backtest

Use this to backtest a strategy the standard way so results are comparable and reproducible.

## Step 1 — Confirm inputs
- **strategy** class (from `strategies/`)
- **symbol** (default `SPY`)
- **period**: start/end (default start `2018-01-01`, end = today). Use ≥ 252 trading days.
- **costs**: default commission 0.1% + slippage 0.1% (already the engine defaults)

## Step 2 — Run it
Prefer a short Python invocation that reuses existing code (do not duplicate engine logic):
```python
from data.fetcher import fetch_ohlcv, clean
from backtesting.engine import BacktestEngine
from backtesting.metrics import print_metrics
from strategies.<module> import <ClassName>

data = clean(fetch_ohlcv("SPY", start="2018-01-01"))
res = BacktestEngine().run(<ClassName>("SPY"), data)
print_metrics(res["metrics"], res["gate1"])
```
For robustness, also run `BacktestEngine().run_walkforward(strategy, data)` and compare
out-of-sample Sharpe to in-sample (should be ≥ ~80%).

## Step 3 — Save a report
Write a CSV/PNG to `reports/<strategy>_<symbol>_<date>.csv` (metrics) so the dashboard and the
`backtest-analyst` agent can read it. Include the equity curve if producing a chart.

## Step 4 — Interpret honestly
- State the Gate 1 verdict (PASS/FAIL) using `gate1_check`.
- If it passes, hand off to the `backtest-analyst` agent for skeptical checks (sample size,
  implausible Sharpe, regime dependence) BEFORE recommending promotion to paper.
- If it fails, say which checks failed and what to investigate — do not tune parameters to fit.

Never present in-sample results as if they were out-of-sample. Never hide a failing gate.
