"""
Algorithmic Trading Strategy Dashboard
Run: streamlit run dashboard/app.py
Deploy: share.streamlit.io → connect GitHub → point at dashboard/app.py
"""
import sys
import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data.fetcher import fetch_ohlcv, clean
from backtesting.engine import BacktestEngine
from backtesting.metrics import compute_metrics, gate1_check
from strategies.momentum import MACDStrategy, EMACrossoverStrategy, RSIMomentumStrategy

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Quant Dashboard | Bryant Effendi",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Phase-gate algorithmic trading — github.com/bryantt88/algo-trading-platform"},
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
  html,body,[class*="css"]{ font-family:'Inter',sans-serif; }
  .stApp{ background:#0e1117; }
  section[data-testid="stSidebar"]{ background:#161b22; border-right:1px solid #30363d; }

  [data-testid="metric-container"]{
    background:#161b22; border:1px solid #30363d; border-radius:12px; padding:16px 20px;
  }
  [data-testid="metric-container"] label{
    color:#8b949e!important; font-size:11px!important; font-weight:600;
    letter-spacing:.06em; text-transform:uppercase;
  }
  [data-testid="metric-container"] [data-testid="stMetricValue"]{
    color:#e6edf3!important; font-size:26px!important; font-weight:700;
  }
  [data-testid="metric-container"] [data-testid="stMetricDelta"]{ font-size:12px!important; }

  .section-header{
    font-size:12px; font-weight:600; color:#8b949e; text-transform:uppercase;
    letter-spacing:.08em; border-bottom:1px solid #30363d; padding-bottom:8px; margin:24px 0 16px;
  }
  .gate-pass{
    background:linear-gradient(135deg,#0d4f3c,#1a7a5e); border:1px solid #238636;
    border-radius:8px; padding:14px 20px; color:#3fb950; font-weight:600; font-size:15px;
  }
  .gate-fail{
    background:linear-gradient(135deg,#4d1f1f,#7a2828); border:1px solid #f85149;
    border-radius:8px; padding:14px 20px; color:#f85149; font-weight:600; font-size:15px;
  }
  .check-row{
    display:flex; justify-content:space-between; align-items:center;
    padding:8px 0; border-bottom:1px solid #21262d; font-size:13px;
  }
  .check-label{ color:#c9d1d9; }
  .check-pass{ color:#3fb950; font-weight:600; }
  .check-fail{ color:#f85149; font-weight:600; }

  .stSelectbox label,.stTextInput label,.stNumberInput label,
  .stMultiSelect label,.stDateInput label{
    color:#8b949e!important; font-size:12px!important; font-weight:500;
  }
  div[data-testid="stRadio"] label{ color:#e6edf3!important; font-size:13px!important; }
  .stButton>button{
    background:linear-gradient(135deg,#1f6feb,#388bfd); color:#fff; border:none;
    border-radius:8px; font-weight:600; font-size:13px; padding:10px 0;
    width:100%; transition:opacity .15s;
  }
  .stButton>button:hover{ opacity:.85; }
  .stTabs [data-baseweb="tab-list"]{
    gap:4px; background:#161b22; border-radius:10px; padding:4px; border:1px solid #30363d;
  }
  .stTabs [data-baseweb="tab"]{
    border-radius:8px; padding:8px 20px; color:#8b949e; font-size:13px; font-weight:500;
  }
  .stTabs [aria-selected="true"]{ background:#1f6feb!important; color:#fff!important; }
  .stDataFrame{ border:1px solid #30363d; border-radius:8px; overflow:hidden; }
  hr{ border-color:#30363d; }
</style>""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
STRATEGIES = {
    "MACD Crossover":         MACDStrategy,
    "EMA Crossover (50/200)": EMACrossoverStrategy,
    "RSI Momentum":           RSIMomentumStrategy,
}

ACCENT  = "#1f6feb"; GREEN = "#3fb950"; RED = "#f85149"; YELLOW = "#d29922"
FG      = "#e6edf3"; FG_DIM = "#8b949e"; BG_CARD = "#161b22"; BG_GRID = "#21262d"

ASSET_COLORS = [
    "#58a6ff", "#3fb950", "#d29922", "#f85149", "#bc8cff",
    "#ff7b72", "#79c0ff", "#56d364", "#ffa657", "#f0883e",
]

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d1117",
    font=dict(family="Inter", color=FG_DIM, size=11),
    xaxis=dict(gridcolor=BG_GRID, zeroline=False, showspikes=True, spikecolor=FG_DIM, spikethickness=1),
    yaxis=dict(gridcolor=BG_GRID, zeroline=False),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0, font_size=11),
    margin=dict(l=0, r=0, t=36, b=0),
    hoverlabel=dict(bgcolor="#161b22", bordercolor="#30363d", font_size=12, font_family="Inter"),
)

# ── Asset universe ─────────────────────────────────────────────────────────────
# (ticker, name, category_emoji)
ASSET_UNIVERSE = [
    ("SPY",     "S&P 500 ETF",          "🇺🇸"),
    ("QQQ",     "Nasdaq 100 ETF",       "🇺🇸"),
    ("IWM",     "Russell 2000 ETF",     "🇺🇸"),
    ("DIA",     "Dow Jones ETF",        "🇺🇸"),
    ("XLK",     "Tech Sector ETF",      "🇺🇸"),
    ("XLF",     "Financials ETF",       "🇺🇸"),
    ("XLE",     "Energy Sector ETF",    "🇺🇸"),
    ("XLV",     "Healthcare ETF",       "🇺🇸"),
    ("TLT",     "20Y US Treasury ETF",  "🏦"),
    ("IEF",     "7-10Y Treasury ETF",   "🏦"),
    ("SHY",     "1-3Y Treasury ETF",    "🏦"),
    ("HYG",     "High Yield Corp ETF",  "🏦"),
    ("GLD",     "Gold ETF",             "🥇"),
    ("SLV",     "Silver ETF",           "🥇"),
    ("GDX",     "Gold Miners ETF",      "🥇"),
    ("USO",     "Crude Oil ETF",        "🛢️"),
    ("EFA",     "Developed Mkts ETF",   "🌍"),
    ("EEM",     "Emerging Mkts ETF",    "🌍"),
    ("FXI",     "China Large Cap ETF",  "🌏"),
    ("VNQ",     "US REITs ETF",         "🏢"),
    ("BTC-USD", "Bitcoin",              "₿"),
    ("ETH-USD", "Ethereum",             "₿"),
]

TICKER_TO_LABEL = {t: f"{e} {t}  –  {n}" for t, n, e in ASSET_UNIVERSE}
LABEL_TO_TICKER = {v: k for k, v in TICKER_TO_LABEL.items()}
ALL_LABELS      = list(TICKER_TO_LABEL.values())

QUICK_PRESETS = {
    "🎯 TSMOM Core":       ["SPY", "TLT", "GLD", "QQQ", "EEM"],
    "⚖️ Risk Parity":      ["SPY", "TLT", "GLD", "IEF"],
    "🇺🇸 US Equity Only":  ["SPY", "QQQ", "IWM", "XLK", "XLF"],
    "🌍 Diversified":      ["SPY", "TLT", "GLD", "EEM", "VNQ"],
    "₿ Crypto + Equities": ["SPY", "QQQ", "BTC-USD", "ETH-USD"],
}

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Config")
    st.markdown("---")

    mode = st.radio("Mode", ["Single Asset", "Portfolio"], horizontal=True, label_visibility="collapsed")

    st.markdown(f"**{'Ticker' if mode == 'Single Asset' else 'Portfolio Assets'}**")

    if mode == "Single Asset":
        symbol  = st.text_input("Ticker", value="SPY", placeholder="e.g. AAPL, BTC-USD, 0700.HK", label_visibility="collapsed").upper().strip()
        tickers = [symbol] if symbol else ["SPY"]
    else:
        preset_name = st.selectbox("Quick Preset", list(QUICK_PRESETS.keys()))
        default_labels = [TICKER_TO_LABEL[t] for t in QUICK_PRESETS[preset_name] if t in TICKER_TO_LABEL]

        selected_labels = st.multiselect(
            "Select assets",
            ALL_LABELS,
            default=default_labels,
            key=f"assets_{preset_name}",
            label_visibility="collapsed",
        )
        custom = st.text_input(
            "Add custom ticker",
            placeholder="e.g. CL=F, 0700.HK  (comma-separated)",
        ).upper().strip()

        tickers = [LABEL_TO_TICKER[l] for l in selected_labels if l in LABEL_TO_TICKER]
        if custom:
            tickers += [t.strip() for t in custom.split(",") if t.strip()]
        tickers = list(dict.fromkeys(tickers))

        if tickers:
            st.markdown(
                f"<div style='font-size:11px;color:{FG_DIM};margin:4px 0 2px;'>"
                f"<b style='color:{FG};'>{len(tickers)}</b> asset{'s' if len(tickers)!=1 else ''} · equal-weighted</div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown("**Strategy**")
    strategy_name = st.selectbox("Strategy", list(STRATEGIES.keys()), label_visibility="collapsed")

    st.markdown("**Date Range**")
    col_s, col_e = st.columns(2)
    start_date = col_s.date_input(
        "From", value=datetime.date(2018, 1, 1),
        min_value=datetime.date(2000, 1, 1), max_value=datetime.date.today(),
    )
    end_date = col_e.date_input(
        "To", value=datetime.date.today(),
        min_value=datetime.date(2000, 1, 1), max_value=datetime.date.today(),
    )
    start = str(start_date)
    end   = str(end_date)

    st.markdown("**Execution Costs**")
    col_c, col_sl = st.columns(2)
    commission = col_c.number_input("Comm %",  value=0.10, step=0.05, format="%.2f") / 100
    slippage   = col_sl.number_input("Slip %", value=0.10, step=0.05, format="%.2f") / 100
    initial_capital = st.number_input("Capital ($)", value=100_000, step=10_000)

    st.markdown("---")
    run = st.button("▶  Run Backtest", use_container_width=True)
    st.markdown("---")
    st.markdown(
        f"<div style='font-size:11px;color:{FG_DIM};'>"
        "Phase-gate system · No lookahead bias<br>"
        "1-bar execution lag · Costs included<br><br>"
        "<a href='https://github.com/bryantt88/algo-trading-platform' "
        f"style='color:{ACCENT};text-decoration:none;'>📂 View on GitHub</a>"
        "</div>",
        unsafe_allow_html=True,
    )

# ── Header ─────────────────────────────────────────────────────────────────────
badge_colour = "#388bfd" if mode == "Single Asset" else "#3fb950"
badge_bg     = "rgba(31,111,235,.15)" if mode == "Single Asset" else "rgba(63,185,80,.15)"
badge_border = "rgba(31,111,235,.3)"  if mode == "Single Asset" else "rgba(63,185,80,.3)"
mode_badge = (
    f"<span style='background:{badge_bg};color:{badge_colour};"
    f"border:1px solid {badge_border};border-radius:20px;"
    f"padding:2px 10px;font-size:12px;font-weight:600;margin-left:10px;'>{mode}</span>"
)
st.markdown(
    f"<h1 style='font-size:28px;font-weight:700;color:{FG};margin-bottom:4px;'>"
    f"📊 Algorithmic Trading Dashboard{mode_badge}</h1>"
    f"<p style='color:{FG_DIM};font-size:13px;margin-top:0;'>"
    "Phase-gate framework · Bryant Effendi · "
    f"<a href='https://github.com/bryantt88/algo-trading-platform' style='color:{ACCENT};text-decoration:none;'>"
    "github.com/bryantt88/algo-trading-platform</a></p>",
    unsafe_allow_html=True,
)
st.markdown("---")

# ── Cache helpers ──────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_data(sym, s, e):
    return clean(fetch_ohlcv(sym, start=s, end=e or None))


@st.cache_data(show_spinner=False)
def run_portfolio_backtest(strategy_name, tickers_tuple, start_str, end_str,
                           commission, slippage, capital):
    engine     = BacktestEngine(initial_capital=capital, commission=commission, slippage=slippage)
    per_asset  = {}
    returns_map = {}
    failed     = []

    for ticker in tickers_tuple:
        try:
            data = load_data(ticker, start_str, end_str)
            if data is None or len(data) < 50:
                failed.append(ticker)
                continue
            result = engine.run(STRATEGIES[strategy_name](ticker), data)
            returns_map[ticker] = result["strategy_returns"]
            per_asset[ticker]   = result
        except Exception:
            failed.append(ticker)

    if not returns_map:
        return None

    ret_df       = pd.DataFrame(returns_map).dropna(how="all").fillna(0)
    port_returns = ret_df.mean(axis=1)
    port_equity  = (1 + port_returns).cumprod() * capital
    metrics      = compute_metrics(port_returns, port_equity, pd.DataFrame())
    gate         = gate1_check(metrics)

    return {
        "portfolio_returns": port_returns,
        "portfolio_equity":  port_equity,
        "per_asset":         per_asset,
        "returns_df":        ret_df,
        "metrics":           metrics,
        "gate1":             gate,
        "failed":            failed,
    }


# ── Idle state ─────────────────────────────────────────────────────────────────
if not run:
    c1, c2, c3 = st.columns(3)
    for col, emoji, title, body in [
        (c1, "🎯", "Phase-Gate System",
         "Every strategy must clear Gate 1 (backtest) before paper trading, and Gate 2 before live."),
        (c2, "📊", "Portfolio Backtest",
         "Pick a preset or build a custom basket. Equal-weighted returns, correlation heatmap included."),
        (c3, "⚡", "No Lookahead Bias",
         "Signals shifted 1 bar · 0.1% commission + 0.1% slippage on every trade."),
    ]:
        col.markdown(
            f"<div style='background:{BG_CARD};border:1px solid #30363d;border-radius:12px;"
            f"padding:20px;min-height:110px;'>"
            f"<div style='font-size:22px;margin-bottom:8px;'>{emoji}</div>"
            f"<div style='font-size:13px;font-weight:600;color:{FG};margin-bottom:6px;'>{title}</div>"
            f"<div style='font-size:12px;color:{FG_DIM};line-height:1.5;'>{body}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown(
        f"<br><p style='color:{FG_DIM};font-size:13px;text-align:center;'>"
        f"Configure a strategy in the sidebar and click <strong style='color:{FG};'>▶ Run Backtest</strong> to begin.</p>",
        unsafe_allow_html=True,
    )
    st.stop()

# ── Execute ────────────────────────────────────────────────────────────────────
if mode == "Single Asset":
    try:
        with st.spinner(f"Fetching {tickers[0]}  ·  Running {strategy_name}…"):
            data     = load_data(tickers[0], start, end)
            strategy = STRATEGIES[strategy_name](tickers[0])
            engine   = BacktestEngine(initial_capital=initial_capital,
                                      commission=commission, slippage=slippage)
            results  = engine.run(strategy, data)
            wf       = engine.run_walkforward(strategy, data)
    except Exception as exc:
        st.error(f"**Backtest failed:** {exc}")
        st.stop()

    m        = results["metrics"]
    gate     = results["gate1"]
    equity   = results["equity_curve"]
    bench    = (1 + results["benchmark_returns"]).cumprod() * initial_capital
    dd       = (equity - equity.cummax()) / equity.cummax()
    trades   = results["trades"]
    wf_test  = wf["test"]["metrics"]
    wf_train = wf["train"]["metrics"]

else:
    if not tickers:
        st.warning("Select at least one asset in the sidebar.")
        st.stop()
    with st.spinner(f"Running {strategy_name} across {len(tickers)} asset{'s' if len(tickers)!=1 else ''}…"):
        port = run_portfolio_backtest(
            strategy_name, tuple(tickers), start, end,
            commission, slippage, initial_capital,
        )
    if port is None:
        st.error("All tickers failed — check ticker names and date range.")
        st.stop()
    if port["failed"]:
        st.warning(f"⚠️ Could not fetch: {', '.join(port['failed'])}")

    m      = port["metrics"]
    gate   = port["gate1"]
    equity = port["portfolio_equity"]
    dd     = (equity - equity.cummax()) / equity.cummax()

# ── Gate banner ────────────────────────────────────────────────────────────────
if gate["PASS"]:
    st.markdown(
        "<div class='gate-pass'>✅  Gate 1 PASS — Strategy is eligible for paper trading (Gate 2)</div>",
        unsafe_allow_html=True,
    )
else:
    failing = [k for k, v in gate.items() if k != "PASS" and not v]
    st.markdown(
        f"<div class='gate-fail'>❌  Gate 1 FAIL — Failing: {', '.join(failing)}</div>",
        unsafe_allow_html=True,
    )
st.markdown("<br>", unsafe_allow_html=True)

# ── KPI strip ──────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Total Return",  f"{m['total_return']:.1%}",  delta=f"Ann {m['annual_return']:.1%}")
k2.metric("Sharpe Ratio",  f"{m['sharpe']:.2f}",
          delta=(f"OOS {wf_test['sharpe']:.2f}" if mode == "Single Asset" else None))
k3.metric("Max Drawdown",  f"{m['max_drawdown']:.1%}")
k4.metric("Win Rate",      f"{m['win_rate']:.1%}",      delta=f"PF {m['profit_factor']:.2f}")
k5.metric("Trades",        f"{m['num_trades']}",        delta=f"{m['n_days']} days")
k6.metric("Sortino",       f"{m['sortino']:.2f}",       delta=f"Calmar {m['calmar']:.2f}")
st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
if mode == "Single Asset":
    tab_chart, tab_oos, tab_risk, tab_trades_tab, tab_gate = st.tabs([
        "📈  Equity Curve", "🔬  Walk-Forward", "🛡️  Risk", "📋  Trade Log", "🎯  Gate 1",
    ])
else:
    tab_chart, tab_per_asset, tab_alloc, tab_risk, tab_gate = st.tabs([
        "📈  Equity Curve", "📊  Per-Asset", "📅  Allocation", "🛡️  Risk", "🎯  Gate 1",
    ])

# ─────────────────────────────── TAB: Equity Curve ───────────────────────────
with tab_chart:
    if mode == "Single Asset":
        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True,
            row_heights=[0.58, 0.22, 0.20], vertical_spacing=0.03,
            subplot_titles=("Strategy vs Buy & Hold", "Drawdown", "Daily Return"),
        )
        fig.add_trace(go.Scatter(
            x=equity.index, y=equity, name=strategy_name,
            line=dict(color=ACCENT, width=2),
            hovertemplate="%{x|%Y-%m-%d}<br>$%{y:,.0f}<extra></extra>",
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=bench.index, y=bench, name=f"{tickers[0]} Buy & Hold",
            line=dict(color=FG_DIM, width=1.5, dash="dot"),
            hovertemplate="%{x|%Y-%m-%d}<br>$%{y:,.0f}<extra></extra>",
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=dd.index, y=dd, name="Drawdown",
            fill="tozeroy", fillcolor="rgba(248,81,73,.18)",
            line=dict(color=RED, width=1),
            hovertemplate="%{x|%Y-%m-%d}<br>%{y:.1%}<extra></extra>",
        ), row=2, col=1)
        dr = results["strategy_returns"]
        fig.add_trace(go.Bar(
            x=dr.index, y=dr, name="Daily Return",
            marker_color=[GREEN if v >= 0 else RED for v in dr], opacity=.6,
            hovertemplate="%{x|%Y-%m-%d}<br>%{y:.2%}<extra></extra>",
        ), row=3, col=1)
        fig.update_layout(height=580, showlegend=True, **PLOTLY_LAYOUT)
        fig.update_yaxes(title_text="Portfolio ($)", tickformat="$,.0f", row=1, col=1)
        fig.update_yaxes(title_text="Drawdown",      tickformat=".0%",   row=2, col=1)
        fig.update_yaxes(title_text="Return",        tickformat=".1%",   row=3, col=1)

    else:
        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.70, 0.30], vertical_spacing=0.04,
            subplot_titles=("Portfolio vs Individual Assets", "Portfolio Drawdown"),
        )
        for i, (ticker, res) in enumerate(port["per_asset"].items()):
            eq_i = res["equity_curve"]
            fig.add_trace(go.Scatter(
                x=eq_i.index, y=eq_i, name=ticker,
                line=dict(color=ASSET_COLORS[i % len(ASSET_COLORS)], width=1),
                opacity=0.45,
                hovertemplate=f"{ticker}<br>%{{x|%Y-%m-%d}}<br>${{y:,.0f}}<extra></extra>",
            ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=equity.index, y=equity, name="Portfolio (equal-wt)",
            line=dict(color=ACCENT, width=3),
            hovertemplate="Portfolio<br>%{x|%Y-%m-%d}<br>$%{y:,.0f}<extra></extra>",
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=dd.index, y=dd, name="Drawdown",
            fill="tozeroy", fillcolor="rgba(248,81,73,.18)",
            line=dict(color=RED, width=1), showlegend=False,
            hovertemplate="%{x|%Y-%m-%d}<br>%{y:.1%}<extra></extra>",
        ), row=2, col=1)
        fig.update_layout(height=520, showlegend=True, **PLOTLY_LAYOUT)
        fig.update_yaxes(title_text="Equity ($)", tickformat="$,.0f", row=1, col=1)
        fig.update_yaxes(title_text="Drawdown",   tickformat=".0%",   row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)

    # Rolling Sharpe (both modes)
    st.markdown("<div class='section-header'>Rolling 252-Day Sharpe</div>", unsafe_allow_html=True)
    dr_roll = port["portfolio_returns"] if mode == "Portfolio" else results["strategy_returns"]
    roll_sh = dr_roll.rolling(252).apply(
        lambda x: (x.mean() / x.std()) * np.sqrt(252) if x.std() > 0 else 0
    )
    fig2 = go.Figure()
    fig2.add_hline(y=1.0, line_dash="dash", line_color=YELLOW, opacity=.6,
                   annotation_text="Gate 1 min (1.0)", annotation_position="top right")
    fig2.add_trace(go.Scatter(
        x=roll_sh.index, y=roll_sh, name="Rolling Sharpe",
        line=dict(color=ACCENT, width=2),
        fill="tozeroy", fillcolor="rgba(31,111,235,.08)",
    ))
    fig2.update_layout(height=200, **PLOTLY_LAYOUT)
    st.plotly_chart(fig2, use_container_width=True)

    # Monthly returns heatmap (tearsheet-style, both modes)
    st.markdown("<div class='section-header'>Monthly Returns Heatmap</div>", unsafe_allow_html=True)
    dr_monthly_src = port["portfolio_returns"] if mode == "Portfolio" else results["strategy_returns"]
    monthly_ret = dr_monthly_src.resample("ME").apply(lambda x: (1 + x).prod() - 1)
    _MONTHS = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
               7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
    mr_df = pd.DataFrame({"ret": monthly_ret, "year": monthly_ret.index.year, "month": monthly_ret.index.month})
    mr_pivot = mr_df.pivot_table(index="year", columns="month", values="ret")
    mr_pivot.columns = [_MONTHS[c] for c in mr_pivot.columns]
    mr_text = mr_pivot.applymap(lambda v: f"{v:.1%}" if pd.notna(v) else "")
    fig_mh = go.Figure(go.Heatmap(
        z=mr_pivot.values,
        x=list(mr_pivot.columns),
        y=[str(y) for y in mr_pivot.index],
        colorscale=[[0,"#7a2828"],[0.5,"#21262d"],[1,"#0d4f3c"]],
        zmid=0,
        text=mr_text.values,
        texttemplate="%{text}",
        hovertemplate="<b>%{y} %{x}</b><br>Return: %{z:.2%}<extra></extra>",
        showscale=True,
        colorbar=dict(title="%", thickness=10, tickformat=".0%"),
    ))
    fig_mh.update_layout(
        height=max(220, len(mr_pivot) * 32 + 60),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d1117",
        font=dict(family="Inter", color=FG_DIM, size=11),
        margin=dict(l=50, r=40, t=20, b=20),
        hoverlabel=dict(bgcolor=BG_CARD, bordercolor="#30363d", font_size=12, font_family="Inter"),
    )
    st.plotly_chart(fig_mh, use_container_width=True)

# ─────────────────────────────── TAB: Walk-Forward (Single only) ─────────────
if mode == "Single Asset":
    with tab_oos:
        st.markdown(
            "<div class='section-header'>In-Sample vs Out-of-Sample (70 / 30 split)</div>",
            unsafe_allow_html=True,
        )
        tr_pd, te_pd = wf["train_period"], wf["test_period"]
        c1, c2 = st.columns(2)

        with c1:
            st.markdown(f"**In-Sample** · {tr_pd[0]} → {tr_pd[1]}")
            rows = [
                ("Sharpe",        f"{wf_train['sharpe']:.2f}",        f"{wf_test['sharpe']:.2f}"),
                ("Total Return",  f"{wf_train['total_return']:.1%}",  f"{wf_test['total_return']:.1%}"),
                ("Max Drawdown",  f"{wf_train['max_drawdown']:.1%}",  f"{wf_test['max_drawdown']:.1%}"),
                ("Win Rate",      f"{wf_train['win_rate']:.1%}",      f"{wf_test['win_rate']:.1%}"),
                ("Profit Factor", f"{wf_train['profit_factor']:.2f}", f"{wf_test['profit_factor']:.2f}"),
                ("Num Trades",    str(wf_train["num_trades"]),        str(wf_test["num_trades"])),
            ]
            st.dataframe(
                pd.DataFrame(rows, columns=["Metric", "Train", "Test"]).set_index("Metric"),
                use_container_width=True,
            )

        with c2:
            st.markdown(f"**Out-of-Sample** · {te_pd[0]} → {te_pd[1]}")
            sharpe_ret = (wf_test["sharpe"] / wf_train["sharpe"] * 100) if wf_train["sharpe"] > 0 else 0
            colour = GREEN if sharpe_ret >= 80 else RED
            st.markdown(
                f"<div style='background:{BG_CARD};border:1px solid #30363d;border-radius:12px;padding:24px;'>"
                f"<div style='font-size:11px;color:{FG_DIM};text-transform:uppercase;font-weight:600;letter-spacing:.06em;'>Sharpe Retention</div>"
                f"<div style='font-size:42px;font-weight:700;color:{colour};margin:8px 0;'>{sharpe_ret:.0f}%</div>"
                f"<div style='font-size:12px;color:{FG_DIM};'>Gate 2 requires ≥ 80% of in-sample Sharpe.</div>"
                f"<div style='font-size:12px;color:{colour};margin-top:8px;font-weight:600;'>"
                f"{'✅ Retention healthy' if sharpe_ret >= 80 else '⚠️ OOS degradation — check for overfitting'}"
                f"</div></div>",
                unsafe_allow_html=True,
            )

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

# ─────────────────────────────── TAB: Per-Asset (Portfolio only) ──────────────
if mode == "Portfolio":
    with tab_per_asset:
        st.markdown("<div class='section-header'>Per-Asset Gate 1 Breakdown</div>", unsafe_allow_html=True)

        rows = []
        for ticker, res in port["per_asset"].items():
            pm = res["metrics"]
            pg = res["gate1"]
            rows.append({
                "Ticker":        ticker,
                "Sharpe":        f"{pm['sharpe']:.2f}",
                "Ann Return":    f"{pm['annual_return']:.1%}",
                "Max Drawdown":  f"{pm['max_drawdown']:.1%}",
                "Win Rate":      f"{pm['win_rate']:.1%}",
                "Profit Factor": f"{pm['profit_factor']:.2f}",
                "Trades":        pm["num_trades"],
                "Gate 1":        "✅ PASS" if pg["PASS"] else "❌ FAIL",
            })
        st.dataframe(
            pd.DataFrame(rows).set_index("Ticker"),
            use_container_width=True,
        )

        # Individual equity curves
        st.markdown(
            "<div class='section-header'>Individual Equity Curves (all starting at $100k)</div>",
            unsafe_allow_html=True,
        )
        fig_pa = go.Figure()
        for i, (ticker, res) in enumerate(port["per_asset"].items()):
            eq_i = res["equity_curve"]
            fig_pa.add_trace(go.Scatter(
                x=eq_i.index, y=eq_i, name=ticker,
                line=dict(color=ASSET_COLORS[i % len(ASSET_COLORS)], width=1.5),
                hovertemplate=f"{ticker}<br>%{{x|%Y-%m-%d}}<br>${{y:,.0f}}<extra></extra>",
            ))
        fig_pa.add_trace(go.Scatter(
            x=equity.index, y=equity, name="Portfolio (combined)",
            line=dict(color=ACCENT, width=3, dash="dash"),
            hovertemplate="Portfolio<br>%{x|%Y-%m-%d}<br>$%{y:,.0f}<extra></extra>",
        ))
        fig_pa.update_layout(height=340, **PLOTLY_LAYOUT)
        fig_pa.update_yaxes(tickformat="$,.0f")
        st.plotly_chart(fig_pa, use_container_width=True)

        # Correlation heatmap
        if len(port["returns_df"].columns) > 1:
            st.markdown("<div class='section-header'>Return Correlation Matrix</div>", unsafe_allow_html=True)
            corr = port["returns_df"].corr()
            fig_corr = go.Figure(go.Heatmap(
                z=corr.values, x=list(corr.columns), y=list(corr.index),
                colorscale="RdBu_r", zmin=-1, zmax=1, zmid=0,
                text=np.round(corr.values, 2), texttemplate="%{text}",
                hovertemplate="<b>%{x} vs %{y}</b><br>ρ = %{z:.2f}<extra></extra>",
                colorbar=dict(title="ρ", thickness=12),
            ))
            n = len(corr)
            _corr_layout = {k: v for k, v in PLOTLY_LAYOUT.items() if k != "margin"}
            fig_corr.update_layout(
                height=max(280, n * 50),
                **_corr_layout,
                margin=dict(l=60, r=40, t=20, b=60),
            )
            st.plotly_chart(fig_corr, use_container_width=True)
            st.caption("Low / negative correlations → better diversification. Target: no pair above 0.6 (per risk rules).")

# ─────────────────────────────── TAB: Allocation (Portfolio only) ─────────────
if mode == "Portfolio":
    with tab_alloc:
        # ── 1. Monthly returns heatmap (portfolio-level) ──────────────────────
        st.markdown("<div class='section-header'>Portfolio Monthly Returns</div>", unsafe_allow_html=True)
        st.caption("Each cell is the portfolio's compounded return for that month.")
        # (reuse the pivot already computed in the equity curve tab)
        dr_alloc = port["portfolio_returns"]
        monthly_ret_a = dr_alloc.resample("ME").apply(lambda x: (1 + x).prod() - 1)
        mr_df_a = pd.DataFrame({
            "ret":   monthly_ret_a,
            "year":  monthly_ret_a.index.year,
            "month": monthly_ret_a.index.month,
        })
        mr_pivot_a = mr_df_a.pivot_table(index="year", columns="month", values="ret")
        _MONTHS = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                   7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
        mr_pivot_a.columns = [_MONTHS[c] for c in mr_pivot_a.columns]
        mr_text_a = mr_pivot_a.applymap(lambda v: f"{v:.1%}" if pd.notna(v) else "")
        # Annual return column
        annual_col = mr_pivot_a.apply(lambda row: (1 + row.dropna()).prod() - 1, axis=1)

        fig_mh2 = go.Figure(go.Heatmap(
            z=mr_pivot_a.values,
            x=list(mr_pivot_a.columns),
            y=[str(y) for y in mr_pivot_a.index],
            colorscale=[[0,"#7a2828"],[0.5,"#21262d"],[1,"#0d4f3c"]],
            zmid=0,
            text=mr_text_a.values,
            texttemplate="%{text}",
            hovertemplate="<b>%{y} %{x}</b><br>Return: %{z:.2%}<extra></extra>",
            showscale=True,
            colorbar=dict(title="%", thickness=10, tickformat=".0%"),
        ))
        fig_mh2.update_layout(
            height=max(220, len(mr_pivot_a) * 32 + 60),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d1117",
            font=dict(family="Inter", color=FG_DIM, size=11),
            margin=dict(l=50, r=40, t=20, b=20),
            hoverlabel=dict(bgcolor=BG_CARD, bordercolor="#30363d", font_size=12, font_family="Inter"),
        )
        st.plotly_chart(fig_mh2, use_container_width=True)

        # Annual summary row
        ann_cols = st.columns(min(len(annual_col), 8))
        for i, (yr, ret) in enumerate(annual_col.items()):
            clr = GREEN if ret >= 0 else RED
            ann_cols[i % len(ann_cols)].markdown(
                f"<div style='background:{BG_CARD};border:1px solid #30363d;border-radius:8px;"
                f"padding:10px 14px;text-align:center;'>"
                f"<div style='font-size:11px;color:{FG_DIM};font-weight:600;'>{yr}</div>"
                f"<div style='font-size:18px;font-weight:700;color:{clr};'>{ret:.1%}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # ── 2. Signal / position heatmap ──────────────────────────────────────
        st.markdown("<div class='section-header'>Signal Timeline — When Each Asset Was Held</div>", unsafe_allow_html=True)
        st.caption("Monthly average signal: 🟢 Long (+1)  ·  ⬜ Flat (0)  ·  🔴 Short (−1)")

        pos_monthly = {}
        for ticker, res in port["per_asset"].items():
            pos_monthly[ticker] = res["position"].resample("ME").mean()

        pos_df = pd.DataFrame(pos_monthly).T
        pos_df.columns = pos_df.columns.strftime("%Y-%m")

        # Show last 48 months max to keep it readable
        if pos_df.shape[1] > 48:
            pos_df = pos_df.iloc[:, -48:]

        fig_sig = go.Figure(go.Heatmap(
            z=pos_df.values,
            x=list(pos_df.columns),
            y=list(pos_df.index),
            colorscale=[[0,"#7a2828"],[0.5,"#30363d"],[1,"#1a7a5e"]],
            zmin=-1, zmax=1, zmid=0,
            text=np.round(pos_df.values, 1),
            texttemplate="%{text}",
            hovertemplate="<b>%{y}</b>  %{x}<br>Avg signal: %{z:.2f}<extra></extra>",
            showscale=True,
            colorbar=dict(title="Signal", thickness=10,
                          tickvals=[-1, 0, 1], ticktext=["Short","Flat","Long"]),
        ))
        n_assets = len(pos_df)
        fig_sig.update_layout(
            height=max(200, n_assets * 40 + 60),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d1117",
            font=dict(family="Inter", color=FG_DIM, size=11),
            xaxis=dict(gridcolor=BG_GRID, tickangle=-45),
            yaxis=dict(gridcolor=BG_GRID),
            margin=dict(l=80, r=40, t=20, b=60),
            hoverlabel=dict(bgcolor=BG_CARD, bordercolor="#30363d", font_size=12, font_family="Inter"),
        )
        st.plotly_chart(fig_sig, use_container_width=True)

        # ── 3. Return attribution ─────────────────────────────────────────────
        st.markdown("<div class='section-header'>Return Attribution (Annualised Contribution)</div>", unsafe_allow_html=True)
        st.caption("Each asset's annualised return × equal weight. Bars show who drove portfolio performance.")

        n_assets_in_port = len(port["per_asset"])
        attribution = {}
        for ticker, res in port["per_asset"].items():
            am = res["metrics"]
            attribution[ticker] = am["annual_return"] / n_assets_in_port

        attr_s    = pd.Series(attribution).sort_values()
        bar_clrs  = [GREEN if v >= 0 else RED for v in attr_s.values]
        fig_attr  = go.Figure(go.Bar(
            x=attr_s.values,
            y=attr_s.index,
            orientation="h",
            marker_color=bar_clrs,
            opacity=0.85,
            text=[f"{v:.1%}" for v in attr_s.values],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Contribution: %{x:.2%}<extra></extra>",
        ))
        fig_attr.add_vline(x=0, line_color=FG_DIM, line_width=1)
        fig_attr.update_layout(
            height=max(200, n_assets_in_port * 36 + 60),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d1117",
            font=dict(family="Inter", color=FG_DIM, size=11),
            xaxis=dict(gridcolor=BG_GRID, zeroline=False, tickformat=".1%"),
            yaxis=dict(gridcolor=BG_GRID),
            margin=dict(l=10, r=60, t=10, b=20),
            hoverlabel=dict(bgcolor=BG_CARD, bordercolor="#30363d", font_size=12, font_family="Inter"),
            showlegend=False,
        )
        st.plotly_chart(fig_attr, use_container_width=True)

        # ── 4. Monthly exposure ───────────────────────────────────────────────
        st.markdown("<div class='section-header'>Monthly Market Exposure (% of Assets Long)</div>", unsafe_allow_html=True)
        st.caption("How many assets had an active long signal each month. 100% = fully invested.")

        long_frac = (pd.DataFrame(pos_monthly) > 0.5).mean(axis=1).resample("ME").mean() * 100
        fig_exp = go.Figure(go.Bar(
            x=long_frac.index,
            y=long_frac.values,
            marker_color=ACCENT, opacity=0.7,
            hovertemplate="%{x|%Y-%m}<br>%{y:.0f}% of assets long<extra></extra>",
        ))
        fig_exp.add_hline(y=50, line_dash="dash", line_color=YELLOW, opacity=.5,
                          annotation_text="50% neutral", annotation_position="top right")
        fig_exp.update_layout(
            height=220,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d1117",
            font=dict(family="Inter", color=FG_DIM, size=11),
            xaxis=dict(gridcolor=BG_GRID, zeroline=False),
            yaxis=dict(gridcolor=BG_GRID, ticksuffix="%", range=[0, 105]),
            margin=dict(l=0, r=0, t=10, b=0),
            hoverlabel=dict(bgcolor=BG_CARD, bordercolor="#30363d", font_size=12, font_family="Inter"),
            showlegend=False,
        )
        st.plotly_chart(fig_exp, use_container_width=True)

# ─────────────────────────────── TAB: Risk ────────────────────────────────────
with tab_risk:
    st.markdown("<div class='section-header'>Risk Metrics</div>", unsafe_allow_html=True)
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Max Drawdown",  f"{m['max_drawdown']:.1%}")
    r2.metric("Annual Vol",    f"{m['annual_volatility']:.1%}")
    r3.metric("Calmar Ratio",  f"{m['calmar']:.2f}")
    r4.metric("Sortino Ratio", f"{m['sortino']:.2f}")

    st.markdown("<div class='section-header'>Return Distribution</div>", unsafe_allow_html=True)
    dr_plot  = port["portfolio_returns"] if mode == "Portfolio" else results["strategy_returns"]
    dr_clean = dr_plot.replace([np.inf, -np.inf], np.nan).dropna()
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

    st.markdown("<div class='section-header'>Risk Limits</div>", unsafe_allow_html=True)
    for label, value in [
        ("Max position size",        "5% of portfolio"),
        ("Stop loss per trade",      "2% (hard)"),
        ("Max daily portfolio loss", "3% (kill switch)"),
        ("Max concurrent positions", "20"),
        ("Max leverage",             "2×"),
        ("Correlation cap",          "|ρ| < 0.6 between any two positions"),
        ("Macro blackout",           "30 min before/after FOMC, earnings"),
    ]:
        st.markdown(
            f"<div class='check-row'>"
            f"<span class='check-label'>{label}</span>"
            f"<span style='color:{FG};font-size:13px;font-weight:500;'>{value}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

# ─────────────────────────────── TAB: Trade Log (Single only) ─────────────────
if mode == "Single Asset":
    with tab_trades_tab:
        if len(trades) == 0:
            st.info("No closed trades in this backtest period.")
        else:
            wins   = trades[trades["pnl_pct"] > 0]
            losses = trades[trades["pnl_pct"] <= 0]
            t1, t2, t3, t4 = st.columns(4)
            t1.metric("Total Trades", len(trades))
            t2.metric("Winning",      len(wins),
                      delta=f"{len(wins)/len(trades):.0%} win rate")
            t3.metric("Avg Win",  f"{wins['pnl_pct'].mean():.2%}"   if len(wins)   else "—")
            t4.metric("Avg Loss", f"{losses['pnl_pct'].mean():.2%}" if len(losses) else "—")

            fig5 = go.Figure()
            fig5.add_trace(go.Bar(
                x=trades.index, y=trades["pnl_pct"],
                marker_color=[GREEN if p > 0 else RED for p in trades["pnl_pct"]],
                opacity=.8,
                hovertemplate="Trade #%{x}<br>PnL: %{y:.2%}<extra></extra>",
            ))
            fig5.update_layout(height=220, title="Per-Trade P&L", **PLOTLY_LAYOUT)
            fig5.update_yaxes(tickformat=".1%")
            st.plotly_chart(fig5, use_container_width=True)

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

# ─────────────────────────────── TAB: Gate 1 ──────────────────────────────────
with tab_gate:
    st.markdown("<div class='section-header'>Gate 1 Checklist</div>", unsafe_allow_html=True)

    if mode == "Portfolio":
        st.caption(
            "Portfolio mode: Sharpe and drawdown are portfolio-level. "
            "Win rate, profit factor, and trade count reflect the return stream, not individual trades — "
            "see the Per-Asset tab for per-ticker breakdown."
        )

    gate_details = {
        "sharpe >= 1.0":        (m["sharpe"],            "≥ 1.0",  f"{m['sharpe']:.2f}"),
        "max_drawdown <= 20%":  (abs(m["max_drawdown"]), "≤ 20%",  f"{m['max_drawdown']:.1%}"),
        "profit_factor >= 1.5": (m["profit_factor"],     "≥ 1.5",  f"{m['profit_factor']:.2f}"),
        "win_rate >= 50%":      (m["win_rate"],           "≥ 50%",  f"{m['win_rate']:.1%}"),
        "num_trades >= 30":     (m["num_trades"],         "≥ 30",   str(m["num_trades"])),
    }
    for key, (_, threshold, actual) in gate_details.items():
        passed = gate.get(key, False)
        icon   = "✅" if passed else "❌"
        clr    = "check-pass" if passed else "check-fail"
        st.markdown(
            f"<div class='check-row'>"
            f"  <span class='check-label'>{key}</span>"
            f"  <span style='display:flex;gap:32px;'>"
            f"    <span style='color:{FG_DIM};'>{threshold}</span>"
            f"    <span class='{clr}'>{icon} {actual}</span>"
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
    for label, detail, ok in [
        ("Walk-forward validation", "70/30 train/test split", mode == "Single Asset"),
        ("Backtest period",         f"{m['n_days']} trading days (min 252)", m["n_days"] >= 252),
        ("No lookahead bias",       "1-bar signal shift enforced by engine", True),
        ("Transaction costs",       "0.1% commission + 0.1% slippage", True),
    ]:
        clr  = "check-pass" if ok else "check-fail"
        icon = "✅" if ok else "⚠️"
        st.markdown(
            f"<div class='check-row'><span class='check-label'>{label}</span>"
            f"<span style='display:flex;gap:32px;'>"
            f"<span style='color:{FG_DIM};font-size:12px;'>{detail}</span>"
            f"<span class='{clr}'>{icon}</span></span></div>",
            unsafe_allow_html=True,
        )
