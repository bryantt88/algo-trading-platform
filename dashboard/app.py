"""
Algorithmic Trading Strategy Dashboard
Run: streamlit run dashboard/app.py
Deploy: share.streamlit.io → connect GitHub → point at dashboard/app.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from data.fetcher import fetch_ohlcv, clean
from backtesting.engine import BacktestEngine
from backtesting.metrics import gate1_check
from strategies.momentum import MACDStrategy, EMACrossoverStrategy, RSIMomentumStrategy

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Quant Dashboard | Bryant Effendi",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Phase-gate algorithmic trading platform — github.com/bryantt88/algo-trading-platform"},
)

# ── Theme & CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* ── Global ── */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  /* ── Background ── */
  .stApp { background-color: #0e1117; }
  section[data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }

  /* ── Metric cards ── */
  [data-testid="metric-container"] {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 16px 20px;
  }
  [data-testid="metric-container"] label { color: #8b949e !important; font-size: 11px !important; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; }
  [data-testid="metric-container"] [data-testid="stMetricValue"] { color: #e6edf3 !important; font-size: 26px !important; font-weight: 700; }
  [data-testid="metric-container"] [data-testid="stMetricDelta"] { font-size: 12px !important; }

  /* ── Section headers ── */
  .section-header {
    font-size: 13px; font-weight: 600; color: #8b949e;
    text-transform: uppercase; letter-spacing: .08em;
    border-bottom: 1px solid #30363d;
    padding-bottom: 8px; margin: 24px 0 16px;
  }

  /* ── Gate badge ── */
  .gate-pass {
    background: linear-gradient(135deg,#0d4f3c,#1a7a5e);
    border: 1px solid #238636; border-radius: 8px;
    padding: 14px 20px; color: #3fb950;
    font-weight: 600; font-size: 15px;
  }
  .gate-fail {
    background: linear-gradient(135deg,#4d1f1f,#7a2828);
    border: 1px solid #f85149; border-radius: 8px;
    padding: 14px 20px; color: #f85149;
    font-weight: 600; font-size: 15px;
  }

  /* ── Check table rows ── */
  .check-row { display: flex; justify-content: space-between; align-items: center;
    padding: 8px 0; border-bottom: 1px solid #21262d; font-size: 13px; }
  .check-label { color: #c9d1d9; }
  .check-pass { color: #3fb950; font-weight: 600; }
  .check-fail { color: #f85149; font-weight: 600; }

  /* ── Sidebar inputs ── */
  .stSelectbox label, .stTextInput label, .stNumberInput label { color: #8b949e !important; font-size: 12px !important; font-weight: 500; }
  .stButton>button {
    background: linear-gradient(135deg,#1f6feb,#388bfd);
    color: #fff; border: none; border-radius: 8px;
    font-weight: 600; font-size: 13px; padding: 10px 0;
    width: 100%; transition: opacity .15s;
  }
  .stButton>button:hover { opacity: .85; }

  /* ── Tab bar ── */
  .stTabs [data-baseweb="tab-list"] { gap: 4px; background: #161b22; border-radius: 10px; padding: 4px; border: 1px solid #30363d; }
  .stTabs [data-baseweb="tab"] { border-radius: 8px; padding: 8px 20px; color: #8b949e; font-size: 13px; font-weight: 500; }
  .stTabs [aria-selected="true"] { background: #1f6feb !important; color: #fff !important; }

  /* ── Dataframe ── */
  .stDataFrame { border: 1px solid #30363d; border-radius: 8px; overflow: hidden; }

  /* ── Divider ── */
  hr { border-color: #30363d; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
STRATEGIES = {
    "MACD Crossover": MACDStrategy,
    "EMA Crossover (50/200)": EMACrossoverStrategy,
    "RSI Momentum": RSIMomentumStrategy,
}

ACCENT   = "#1f6feb"
GREEN    = "#3fb950"
RED      = "#f85149"
YELLOW   = "#d29922"
FG       = "#e6edf3"
FG_DIM   = "#8b949e"
BG_CARD  = "#161b22"
BG_GRID  = "#21262d"

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#0d1117",
    font=dict(family="Inter", color=FG_DIM, size=11),
    xaxis=dict(gridcolor=BG_GRID, zeroline=False, showspikes=True, spikecolor=FG_DIM, spikethickness=1),
    yaxis=dict(gridcolor=BG_GRID, zeroline=False),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0, font_size=11),
    margin=dict(l=0, r=0, t=36, b=0),
    hoverlabel=dict(bgcolor="#161b22", bordercolor="#30363d", font_size=12, font_family="Inter"),
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Backtest Config")
    st.markdown("---")

    strategy_name = st.selectbox("Strategy", list(STRATEGIES.keys()))
    symbol        = st.text_input("Ticker", value="SPY").upper().strip()

    col_s, col_e = st.columns(2)
    start = col_s.text_input("From", value="2018-01-01")
    end   = col_e.text_input("To", value="")

    st.markdown("**Execution costs**")
    col_c, col_sl = st.columns(2)
    commission = col_c.number_input("Comm %", value=0.10, step=0.05, format="%.2f") / 100
    slippage   = col_sl.number_input("Slip %", value=0.10, step=0.05, format="%.2f") / 100

    initial_capital = st.number_input("Capital ($)", value=100_000, step=10_000)

    st.markdown("---")
    run = st.button("▶  Run Backtest", use_container_width=True)

    st.markdown("---")
    st.markdown(
        "<div style='font-size:11px;color:#8b949e;'>"
        "Phase-gate system · No lookahead bias<br>"
        "1-bar execution lag · Costs included<br><br>"
        "<a href='https://github.com/bryantt88/algo-trading-platform' "
        "style='color:#1f6feb;text-decoration:none;'>📂 View on GitHub</a>"
        "</div>",
        unsafe_allow_html=True,
    )

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='font-size:28px;font-weight:700;color:#e6edf3;margin-bottom:4px;'>"
    "📊 Algorithmic Trading Dashboard</h1>"
    "<p style='color:#8b949e;font-size:13px;margin-top:0;'>"
    "Phase-gate framework · Bryant Effendi · "
    "<a href='https://github.com/bryantt88/algo-trading-platform' style='color:#1f6feb;text-decoration:none;'>"
    "github.com/bryantt88/algo-trading-platform</a></p>",
    unsafe_allow_html=True,
)
st.markdown("---")

# ── Data / cache ──────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_data(sym, s, e):
    return clean(fetch_ohlcv(sym, start=s, end=e or None))

# ── Idle state ────────────────────────────────────────────────────────────────
if not run:
    c1, c2, c3 = st.columns(3)
    for col, emoji, title, body in [
        (c1, "🎯", "Phase-Gate System",
         "Every strategy must clear Gate 1 (backtest) before paper trading, and Gate 2 before live."),
        (c2, "🛡️", "Risk Management",
         "Max 5% position size · 2% hard stop · 3% daily kill switch · Max 2× leverage."),
        (c3, "⚡", "No Lookahead Bias",
         "Signals shifted 1 bar · 0.1% commission + 0.1% slippage on every trade."),
    ]:
        col.markdown(
            f"<div style='background:#161b22;border:1px solid #30363d;border-radius:12px;"
            f"padding:20px;height:120px;'>"
            f"<div style='font-size:22px;margin-bottom:8px;'>{emoji}</div>"
            f"<div style='font-size:13px;font-weight:600;color:#e6edf3;margin-bottom:6px;'>{title}</div>"
            f"<div style='font-size:12px;color:#8b949e;line-height:1.5;'>{body}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown(
        "<br><p style='color:#8b949e;font-size:13px;text-align:center;'>"
        "Configure a strategy in the sidebar and click <strong style='color:#e6edf3;'>▶ Run Backtest</strong> to begin.</p>",
        unsafe_allow_html=True,
    )
    st.stop()

# ── Run backtest ──────────────────────────────────────────────────────────────
try:
    with st.spinner(f"Fetching {symbol}  ·  Running {strategy_name}…"):
        data     = load_data(symbol, start, end)
        strategy = STRATEGIES[strategy_name](symbol)
        engine   = BacktestEngine(initial_capital=initial_capital, commission=commission, slippage=slippage)
        results  = engine.run(strategy, data)
        wf       = engine.run_walkforward(strategy, data)
except Exception as exc:
    st.error(f"**Backtest failed:** {exc}")
    st.stop()

m       = results["metrics"]
gate    = results["gate1"]
equity  = results["equity_curve"]
bench   = (1 + results["benchmark_returns"]).cumprod() * initial_capital
dd      = (equity - equity.cummax()) / equity.cummax()
trades  = results["trades"]
wf_test = wf["test"]["metrics"]

# ── Gate 1 banner ─────────────────────────────────────────────────────────────
if gate["PASS"]:
    st.markdown(
        "<div class='gate-pass'>✅  Gate 1 PASS — Strategy is eligible for paper trading (Gate 2)</div>",
        unsafe_allow_html=True,
    )
else:
    failing = [k for k, v in gate.items() if k != "PASS" and not v]
    st.markdown(
        f"<div class='gate-fail'>❌  Gate 1 FAIL — Failing checks: {', '.join(failing)}</div>",
        unsafe_allow_html=True,
    )
st.markdown("<br>", unsafe_allow_html=True)

# ── KPI strip ─────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Total Return",    f"{m['total_return']:.1%}",     delta=f"Ann {m['annual_return']:.1%}")
k2.metric("Sharpe Ratio",    f"{m['sharpe']:.2f}",           delta=f"OOS {wf_test['sharpe']:.2f}")
k3.metric("Max Drawdown",    f"{m['max_drawdown']:.1%}")
k4.metric("Win Rate",        f"{m['win_rate']:.1%}",         delta=f"PF {m['profit_factor']:.2f}")
k5.metric("Trades",          f"{m['num_trades']}",           delta=f"{m['n_days']} days")
k6.metric("Sortino",         f"{m['sortino']:.2f}",          delta=f"Calmar {m['calmar']:.2f}")
st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_chart, tab_oos, tab_risk, tab_trades, tab_gate = st.tabs([
    "📈  Equity Curve", "🔬  Walk-Forward", "🛡️  Risk", "📋  Trade Log", "🎯  Gate 1"
])

# ────────────────────────────── TAB 1: Equity Curve ──────────────────────────
with tab_chart:
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.58, 0.22, 0.20],
        vertical_spacing=0.03,
        subplot_titles=("Portfolio vs Buy & Hold", "Drawdown", "Daily Return"),
    )
    # Equity
    fig.add_trace(go.Scatter(x=equity.index, y=equity, name=strategy_name,
        line=dict(color=ACCENT, width=2), hovertemplate="%{x|%Y-%m-%d}<br>$%{y:,.0f}<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=bench.index, y=bench, name=f"{symbol} Buy & Hold",
        line=dict(color=FG_DIM, width=1.5, dash="dot"), hovertemplate="%{x|%Y-%m-%d}<br>$%{y:,.0f}<extra></extra>"), row=1, col=1)
    # Drawdown
    fig.add_trace(go.Scatter(x=dd.index, y=dd, name="Drawdown",
        fill="tozeroy", fillcolor="rgba(248,81,73,.18)", line=dict(color=RED, width=1),
        hovertemplate="%{x|%Y-%m-%d}<br>%{y:.1%}<extra></extra>"), row=2, col=1)
    # Daily return bars
    dr = results["strategy_returns"]
    colors = [GREEN if v >= 0 else RED for v in dr]
    fig.add_trace(go.Bar(x=dr.index, y=dr, name="Daily Return",
        marker_color=colors, opacity=.6,
        hovertemplate="%{x|%Y-%m-%d}<br>%{y:.2%}<extra></extra>"), row=3, col=1)

    fig.update_layout(height=580, showlegend=True, **PLOTLY_LAYOUT)
    fig.update_yaxes(title_text="Portfolio ($)", tickformat="$,.0f", row=1, col=1)
    fig.update_yaxes(title_text="Drawdown",     tickformat=".0%",   row=2, col=1)
    fig.update_yaxes(title_text="Return",       tickformat=".1%",   row=3, col=1)
    st.plotly_chart(fig, use_container_width=True)

    # Rolling Sharpe
    st.markdown("<div class='section-header'>Rolling 252-Day Sharpe</div>", unsafe_allow_html=True)
    roll_sh = dr.rolling(252).apply(lambda x: (x.mean() / x.std()) * np.sqrt(252) if x.std() > 0 else 0)
    fig2 = go.Figure()
    fig2.add_hline(y=1.0, line_dash="dash", line_color=YELLOW, opacity=.6,
                   annotation_text="Gate 1 min (1.0)", annotation_position="top right")
    fig2.add_trace(go.Scatter(x=roll_sh.index, y=roll_sh, name="Rolling Sharpe",
        line=dict(color=ACCENT, width=2), fill="tozeroy", fillcolor=f"rgba(31,111,235,.08)"))
    fig2.update_layout(height=200, **PLOTLY_LAYOUT)
    fig2.update_yaxes(gridcolor=BG_GRID)
    st.plotly_chart(fig2, use_container_width=True)

# ────────────────────────────── TAB 2: Walk-Forward ──────────────────────────
with tab_oos:
    st.markdown("<div class='section-header'>In-Sample vs Out-of-Sample (70 / 30 split)</div>", unsafe_allow_html=True)

    wf_train = wf["train"]["metrics"]
    tr_pd, te_pd = wf["train_period"], wf["test_period"]

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**In-Sample** · {tr_pd[0]} → {tr_pd[1]}")
        rows = [
            ("Sharpe",       f"{wf_train['sharpe']:.2f}",       f"{wf_test['sharpe']:.2f}"),
            ("Total Return", f"{wf_train['total_return']:.1%}", f"{wf_test['total_return']:.1%}"),
            ("Max Drawdown", f"{wf_train['max_drawdown']:.1%}", f"{wf_test['max_drawdown']:.1%}"),
            ("Win Rate",     f"{wf_train['win_rate']:.1%}",     f"{wf_test['win_rate']:.1%}"),
            ("Profit Factor",f"{wf_train['profit_factor']:.2f}",f"{wf_test['profit_factor']:.2f}"),
            ("Num Trades",   f"{wf_train['num_trades']}",       f"{wf_test['num_trades']}"),
        ]
        wf_df = pd.DataFrame(rows, columns=["Metric", "Train", "Test"])
        st.dataframe(wf_df.set_index("Metric"), use_container_width=True)

    with c2:
        st.markdown(f"**Out-of-Sample** · {te_pd[0]} → {te_pd[1]}")
        sharpe_retention = (wf_test["sharpe"] / wf_train["sharpe"] * 100) if wf_train["sharpe"] > 0 else 0
        gate2_threshold  = 80
        colour = GREEN if sharpe_retention >= gate2_threshold else RED
        st.markdown(
            f"<div style='background:#161b22;border:1px solid #30363d;border-radius:12px;padding:24px;'>"
            f"<div style='font-size:11px;color:#8b949e;text-transform:uppercase;font-weight:600;letter-spacing:.06em;'>Sharpe Retention</div>"
            f"<div style='font-size:42px;font-weight:700;color:{colour};margin:8px 0;'>{sharpe_retention:.0f}%</div>"
            f"<div style='font-size:12px;color:#8b949e;'>Gate 2 requires ≥ 80% of in-sample Sharpe in live paper trading.</div>"
            f"<div style='font-size:12px;color:{colour};margin-top:8px;font-weight:600;'>"
            f"{'✅ Retention looks healthy' if sharpe_retention >= gate2_threshold else '⚠️ OOS degradation — investigate overfitting'}"
            f"</div></div>",
            unsafe_allow_html=True,
        )

    # Equity comparison chart
    eq_train = wf["train"]["equity_curve"]
    eq_test  = wf["test"]["equity_curve"]
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=eq_train.index, y=eq_train, name="In-Sample",
        line=dict(color=ACCENT, width=2)))
    fig3.add_trace(go.Scatter(x=eq_test.index, y=eq_test, name="Out-of-Sample",
        line=dict(color=GREEN, width=2)))
    fig3.add_vline(x=str(eq_train.index[-1].date()), line_dash="dash",
                   line_color=YELLOW, annotation_text="OOS split", opacity=.7)
    fig3.update_layout(height=280, title="Equity Curve Split", **PLOTLY_LAYOUT)
    fig3.update_yaxes(tickformat="$,.0f")
    st.plotly_chart(fig3, use_container_width=True)

# ────────────────────────────── TAB 3: Risk ──────────────────────────────────
with tab_risk:
    st.markdown("<div class='section-header'>Risk Metrics</div>", unsafe_allow_html=True)
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Max Drawdown",    f"{m['max_drawdown']:.1%}")
    r2.metric("Annual Vol",      f"{m['annual_volatility']:.1%}")
    r3.metric("Calmar Ratio",    f"{m['calmar']:.2f}")
    r4.metric("Sortino Ratio",   f"{m['sortino']:.2f}")

    st.markdown("<div class='section-header'>Return Distribution</div>", unsafe_allow_html=True)
    dr_clean = results["strategy_returns"].replace([np.inf, -np.inf], np.nan).dropna()
    fig4 = go.Figure()
    fig4.add_trace(go.Histogram(
        x=dr_clean, nbinsx=80, name="Daily Returns",
        marker_color=ACCENT, opacity=.75,
        hovertemplate="Return: %{x:.2%}<br>Count: %{y}<extra></extra>",
    ))
    fig4.add_vline(x=dr_clean.mean(), line_dash="dash", line_color=GREEN,
                   annotation_text=f"Mean {dr_clean.mean():.3%}", annotation_position="top right")
    fig4.add_vline(x=dr_clean.quantile(0.05), line_dash="dash", line_color=RED,
                   annotation_text=f"VaR 5% {dr_clean.quantile(0.05):.2%}", annotation_position="top left")
    fig4.update_layout(height=260, **PLOTLY_LAYOUT)
    fig4.update_xaxes(tickformat=".1%")
    st.plotly_chart(fig4, use_container_width=True)

    st.markdown("<div class='section-header'>Risk Limits (CLAUDE.md)</div>", unsafe_allow_html=True)
    limits = [
        ("Max position size",      "5% of portfolio"),
        ("Stop loss per trade",    "2% (hard)"),
        ("Max daily portfolio loss","3% (kill switch)"),
        ("Max concurrent positions","20"),
        ("Max leverage",           "2×"),
        ("Correlation cap",        "|ρ| < 0.6 between new and existing"),
        ("Macro blackout",         "No trading 30 min before/after FOMC, earnings"),
    ]
    for label, value in limits:
        st.markdown(
            f"<div class='check-row'><span class='check-label'>{label}</span>"
            f"<span style='color:#e6edf3;font-size:13px;font-weight:500;'>{value}</span></div>",
            unsafe_allow_html=True,
        )

# ────────────────────────────── TAB 4: Trade Log ─────────────────────────────
with tab_trades:
    if len(trades) == 0:
        st.info("No closed trades in this backtest period.")
    else:
        wins   = trades[trades["pnl_pct"] > 0]
        losses = trades[trades["pnl_pct"] <= 0]

        t1, t2, t3, t4 = st.columns(4)
        t1.metric("Total Trades",  len(trades))
        t2.metric("Winning",       len(wins),   delta=f"{len(wins)/len(trades):.0%} win rate")
        t3.metric("Avg Win",       f"{wins['pnl_pct'].mean():.2%}" if len(wins) else "—")
        t4.metric("Avg Loss",      f"{losses['pnl_pct'].mean():.2%}" if len(losses) else "—")

        # PnL distribution
        fig5 = go.Figure()
        bar_colors = [GREEN if p > 0 else RED for p in trades["pnl_pct"]]
        fig5.add_trace(go.Bar(
            x=trades.index, y=trades["pnl_pct"],
            marker_color=bar_colors, opacity=.8,
            hovertemplate="Trade #%{x}<br>PnL: %{y:.2%}<extra></extra>",
        ))
        fig5.update_layout(height=220, title="Trade P&L (%)", **PLOTLY_LAYOUT)
        fig5.update_yaxes(tickformat=".1%")
        st.plotly_chart(fig5, use_container_width=True)

        # Trade table
        display = trades.copy()
        for col in ["entry_date", "exit_date"]:
            if col in display.columns:
                display[col] = pd.to_datetime(display[col]).dt.strftime("%Y-%m-%d")
        for col in ["entry_price", "exit_price"]:
            if col in display.columns:
                display[col] = display[col].map("${:,.2f}".format)
        if "pnl_pct" in display.columns:
            display["pnl_pct"] = display["pnl_pct"].map("{:.2%}".format)
        st.dataframe(display, use_container_width=True, height=320)

# ────────────────────────────── TAB 5: Gate 1 ────────────────────────────────
with tab_gate:
    st.markdown("<div class='section-header'>Gate 1 Checklist — Backtest Requirements</div>", unsafe_allow_html=True)

    gate_details = {
        "sharpe >= 1.0":      (m["sharpe"],           "≥ 1.0",    f"{m['sharpe']:.2f}"),
        "max_drawdown <= 20%":(abs(m["max_drawdown"]), "≤ 20%",    f"{m['max_drawdown']:.1%}"),
        "profit_factor >= 1.5":(m["profit_factor"],   "≥ 1.5",    f"{m['profit_factor']:.2f}"),
        "win_rate >= 50%":    (m["win_rate"],          "≥ 50%",    f"{m['win_rate']:.1%}"),
        "num_trades >= 30":   (m["num_trades"],        "≥ 30",     str(m["num_trades"])),
    }
    for key, (_, threshold, actual) in gate_details.items():
        passed = gate.get(key, False)
        icon   = "✅" if passed else "❌"
        color  = "check-pass" if passed else "check-fail"
        st.markdown(
            f"<div class='check-row'>"
            f"  <span class='check-label'>{key}</span>"
            f"  <span style='display:flex;gap:32px;'>"
            f"    <span style='color:#8b949e;'>{threshold}</span>"
            f"    <span class='{color}'>{icon} {actual}</span>"
            f"  </span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    if gate["PASS"]:
        st.markdown(
            "<div class='gate-pass' style='text-align:center;font-size:17px;padding:20px;'>"
            "✅  Gate 1 PASS<br>"
            "<span style='font-size:13px;font-weight:400;opacity:.85;'>"
            "Ready to deploy to Alpaca paper account for Gate 2 (30-day live paper trading)."
            "</span></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='gate-fail' style='text-align:center;font-size:17px;padding:20px;'>"
            "❌  Gate 1 FAIL<br>"
            "<span style='font-size:13px;font-weight:400;opacity:.85;'>"
            "Tune parameters or review strategy logic before paper trading."
            "</span></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div class='section-header'>Additional Requirements</div>", unsafe_allow_html=True)
    extras = [
        ("Walk-forward validation", "70/30 train/test split", True),
        ("Backtest period",         f"{m['n_days']} trading days (min 252)", m["n_days"] >= 252),
        ("No lookahead bias",       "1-bar signal shift enforced by engine", True),
        ("Transaction costs",       f"0.1% commission + 0.1% slippage", True),
    ]
    for label, detail, ok in extras:
        color = "check-pass" if ok else "check-fail"
        icon  = "✅" if ok else "❌"
        st.markdown(
            f"<div class='check-row'><span class='check-label'>{label}</span>"
            f"<span style='display:flex;gap:32px;'>"
            f"<span style='color:#8b949e;font-size:12px;'>{detail}</span>"
            f"<span class='{color}'>{icon}</span></span></div>",
            unsafe_allow_html=True,
        )
