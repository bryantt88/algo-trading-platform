---
name: gate-review
description: Evaluate whether a strategy is ready to advance to the next phase gate (Backtest -> Paper -> Live). Use when the user asks "is this ready for paper/live", "should I promote this strategy", or wants a go/no-go decision against the project's gate criteria.
---

# Phase gate review

This project promotes strategies through three gates. Never skip a gate. Read the exact thresholds
from `CLAUDE.md` and `configs/default.yaml` before deciding — do not rely on memory.

## Gate 1 — Backtest → Paper
Requires: Sharpe ≥ 1.0, MaxDD ≤ 20%, Profit Factor ≥ 1.5, Win Rate ≥ 50%, Trades ≥ 30,
backtest ≥ 252 days, walk-forward done, no lookahead bias confirmed.
- Run/locate the backtest (`run-backtest` skill) and the `quant-reviewer` agent's bias audit.
- A green gate with too few trades or an implausible Sharpe is still a FAIL — invoke `backtest-analyst`.

## Gate 2 — Paper → Live
Requires: ≥ 30 trading days on Alpaca paper, live Sharpe ≥ 80% of backtest Sharpe, no operational
failures (data gaps, missed orders).
- Pull the paper track record (Alpaca MCP) and compare to the backtest.

## Gate 3 — Live (manual sign-off)
Requires: start ≤ 10% of intended allocation, kill switch tested, 60 days consistent before scaling.
- This gate is a deliberate human decision. Present the evidence; do not auto-approve.

## Output
A go/no-go report: **Current phase** → **Gate scorecard** (each criterion pass/fail with the actual
number) → **Blocking items** → **Decision**: PROMOTE / HOLD (with what must improve) / REJECT.
State the gate thresholds you used and where you read them. When in doubt, HOLD.
