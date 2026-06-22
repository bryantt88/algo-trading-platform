# 📈 Algorithmic Trading Research Platform

A disciplined, end-to-end framework for developing quantitative trading strategies — from research to
backtest to paper trading to live — built around a **phase-gate methodology** that refuses to let a
strategy risk capital until it has earned it.

<p>
<img alt="Python" src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white">
<img alt="Streamlit" src="https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B?logo=streamlit&logoColor=white">
<img alt="Alpaca" src="https://img.shields.io/badge/Broker-Alpaca-FFD700">
<img alt="License" src="https://img.shields.io/badge/License-MIT-green">
</p>

> **Why this exists.** Most retail backtests look brilliant and fail live — lookahead bias, ignored
> transaction costs, and overfitting. This platform is engineered to *not lie to itself*: signals are
> lagged one bar, costs are charged on every trade, and no strategy advances a phase until it clears
> explicit, pre-registered metrics.

---

## 🚦 The Phase-Gate Methodology

```
Research  →  Backtest (Gate 1)  →  Paper Trade (Gate 2)  →  Live (Gate 3)
```

| Gate | Promotes | Hard requirements |
|------|----------|-------------------|
| **Gate 1** | Backtest → Paper | Sharpe ≥ 1.0 · Max DD ≤ 20% · Profit Factor ≥ 1.5 · Win Rate ≥ 50% · ≥ 30 trades · ≥ 252 days · walk-forward validated |
| **Gate 2** | Paper → Live | ≥ 30 days live paper · live Sharpe ≥ 80% of backtest · zero operational failures |
| **Gate 3** | Live scaling | Start ≤ 10% allocation · kill switch tested · 60 days consistent |

Gate checks are **code**, not vibes — see [`backtesting/metrics.py`](backtesting/metrics.py) `gate1_check()`.

---

## 🖥️ Interactive Dashboard

A Streamlit app to backtest any strategy and see equity curve, drawdown, full metrics, and live
**Gate 1 pass/fail badges** — all with transaction costs and no lookahead bias.

```bash
streamlit run dashboard/app.py
```

> _Deployed free on Streamlit Community Cloud — point it at `dashboard/app.py`._

---

## 🏗️ Architecture

```
strategies/      BaseStrategy ABC + momentum (MACD, EMA, RSI). Signals are never pre-shifted.
backtesting/     Vectorized engine (1-bar execution lag, costs) + metrics + gate checks.
data/            yfinance fetcher with parquet cache; clean/validate helpers.
risk/            Position sizing (fixed-fraction, fractional Kelly, vol-scaled).
execution/       Alpaca paper trader; live trader with a mandatory 3%-daily kill switch.
dashboard/       Streamlit app.
configs/         YAML config (gate thresholds, risk limits, costs).
tests/           pytest for metrics & position sizing.
docs/research/   Curated academic reading list on backtest rigor & anomalies.
```

Design choices that prevent the classic backtest lies:
- **No lookahead bias** — the engine shifts signals by one bar before computing returns.
- **Costs are mandatory** — 0.1% commission + 0.1% slippage on every position change.
- **Risk is enforced, not suggested** — position caps, stop loss, and a live kill switch.

---

## 🚀 Quickstart

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt
python -m pytest tests/ -v                          # verify the engine
streamlit run dashboard/app.py                       # explore strategies
```

Paper/live trading needs free [Alpaca](https://alpaca.markets) keys — copy `.env.example` → `.env`
and fill them in. **The repo never ships secrets; live trading stays disabled until Gates 1 & 2 pass.**

---

## 🧪 Tech Stack

`pandas` · `numpy` · `yfinance` · `alpaca-py` · `pandas-ta` · `scikit-learn` / `xgboost` ·
`statsmodels` · `plotly` · `streamlit` · `quantstats` · `pytest`

---

## 📚 Further reading

See [`docs/research/reading-list.md`](docs/research/reading-list.md) for the literature this platform is
built on — backtest overfitting (Bailey & López de Prado), multiple testing (Harvey & Liu), and the
foundational anomalies (momentum, pairs trading, factors).

---

## ⚠️ Disclaimer

For research and educational purposes only. Nothing here is financial advice. Trading involves risk of
loss. Live trading is disabled by default and gated behind explicit validation.
