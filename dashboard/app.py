"""
Streamlit dashboard for the algorithmic trading project.

Run locally:
    streamlit run dashboard/app.py

Deploy free on Streamlit Community Cloud:
    1. Push this repo to GitHub (public)
    2. share.streamlit.io -> New app -> point at dashboard/app.py
    3. Add ALPACA keys as Secrets only if you enable live data panels

The app reuses the project's own engine (no logic duplication):
    data/fetcher.py        -> fetch OHLCV
    strategies/*.py        -> signal generation
    backtesting/engine.py  -> BacktestEngine
    backtesting/metrics.py -> gate1_check
"""
import sys
from pathlib import Path

# Make the project root importable when Streamlit runs this file directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data.fetcher import fetch_ohlcv, clean
from backtesting.engine import BacktestEngine
from strategies.momentum import MACDStrategy, EMACrossoverStrategy, RSIMomentumStrategy

STRATEGIES = {
    "MACD Crossover": MACDStrategy,
    "EMA Crossover (50/200)": EMACrossoverStrategy,
    "RSI Momentum": RSIMomentumStrategy,
}

st.set_page_config(page_title="Quant Strategy Dashboard", page_icon="📈", layout="wide")


# ── Sidebar controls ──────────────────────────────────────────────────
st.sidebar.title("⚙️ Backtest Settings")
strategy_name = st.sidebar.selectbox("Strategy", list(STRATEGIES.keys()))
symbol = st.sidebar.text_input("Symbol", value="SPY").upper().strip()
col_a, col_b = st.sidebar.columns(2)
start = col_a.text_input("Start", value="2018-01-01")
end = col_b.text_input("End (blank = today)", value="")
initial_capital = st.sidebar.number_input("Initial capital ($)", value=100_000, step=10_000)
commission = st.sidebar.number_input("Commission (%)", value=0.10, step=0.05) / 100
slippage = st.sidebar.number_input("Slippage (%)", value=0.10, step=0.05) / 100
run = st.sidebar.button("▶ Run Backtest", type="primary", use_container_width=True)


# ── Header ────────────────────────────────────────────────────────────
st.title("📈 Algorithmic Trading — Strategy Dashboard")
st.caption(
    "Phase-gate methodology: every strategy must clear Gate 1 (backtest) before paper trading. "
    "All results below include transaction costs and a 1-bar execution lag (no lookahead bias)."
)


@st.cache_data(show_spinner=False)
def load_data(sym: str, s: str, e: str) -> pd.DataFrame:
    df = fetch_ohlcv(sym, start=s, end=e or None)
    return clean(df)


def gate_badge(passed: bool) -> str:
    return "✅ PASS" if passed else "❌ FAIL"


if run:
    try:
        with st.spinner(f"Fetching {symbol} and running {strategy_name}…"):
            data = load_data(symbol, start, end)
            strategy = STRATEGIES[strategy_name](symbol)
            engine = BacktestEngine(
                initial_capital=initial_capital,
                commission=commission,
                slippage=slippage,
            )
            results = engine.run(strategy, data)
    except Exception as exc:  # noqa: BLE001 - surface any error to the user
        st.error(f"Backtest failed: {exc}")
        st.stop()

    m = results["metrics"]
    gate = results["gate1"]

    # ── Top metric row ────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Return", f"{m['total_return']:.1%}")
    c2.metric("Sharpe", f"{m['sharpe']:.2f}")
    c3.metric("Max Drawdown", f"{m['max_drawdown']:.1%}")
    c4.metric("Win Rate", f"{m['win_rate']:.1%}")
    c5.metric("Trades", f"{m['num_trades']}")

    # ── Gate 1 banner ─────────────────────────────────────────────────
    if gate["PASS"]:
        st.success("**Gate 1: PASS** — this strategy is eligible for paper trading.")
    else:
        failed = [k for k, v in gate.items() if k != "PASS" and not v]
        st.warning(f"**Gate 1: FAIL** — not yet eligible for paper trading. Failing checks: {', '.join(failed)}")

    with st.expander("Gate 1 detail"):
        st.table(pd.DataFrame(
            [(k, gate_badge(v)) for k, v in gate.items() if k != "PASS"],
            columns=["Check", "Result"],
        ))

    # ── Equity curve + drawdown ───────────────────────────────────────
    equity = results["equity_curve"]
    bench = (1 + results["benchmark_returns"]).cumprod() * initial_capital
    drawdown = (equity - equity.cummax()) / equity.cummax()

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05,
        subplot_titles=("Equity Curve vs Buy & Hold", "Drawdown"),
    )
    fig.add_trace(go.Scatter(x=equity.index, y=equity, name=strategy_name, line=dict(width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=bench.index, y=bench, name=f"{symbol} Buy & Hold",
                             line=dict(width=1, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=drawdown.index, y=drawdown, name="Drawdown", fill="tozeroy",
                             line=dict(color="#ef4444")), row=2, col=1)
    fig.update_layout(height=600, legend=dict(orientation="h", y=1.08), margin=dict(t=60, b=20))
    fig.update_yaxes(title_text="Portfolio ($)", row=1, col=1)
    fig.update_yaxes(title_text="Drawdown", tickformat=".0%", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

    # ── Secondary metrics + trade log ─────────────────────────────────
    left, right = st.columns([1, 1])
    with left:
        st.subheader("Full Metrics")
        st.dataframe(pd.Series({
            "Annual Return": f"{m['annual_return']:.1%}",
            "Annual Volatility": f"{m['annual_volatility']:.1%}",
            "Sortino": f"{m['sortino']:.2f}",
            "Calmar": f"{m['calmar']:.2f}",
            "Profit Factor": f"{m['profit_factor']:.2f}",
            "Avg Win": f"{m['avg_win']:.2%}",
            "Avg Loss": f"{m['avg_loss']:.2%}",
            "Expectancy": f"{m['expectancy']:.2%}",
        }, name="Value").to_frame(), use_container_width=True)
    with right:
        st.subheader("Trade Log")
        trades = results["trades"]
        if len(trades):
            st.dataframe(trades, use_container_width=True, height=320)
        else:
            st.info("No closed trades in this period.")
else:
    st.info("Configure a backtest in the sidebar and click **Run Backtest**.")
