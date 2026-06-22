# Quant Trading — Curated Reading List

A short, high-signal reading list for building strategies that survive contact with live markets.
Read the **rigor** section first — it is what separates a real strategy from a curve-fit.

---

## 1. Backtest rigor & overfitting (read these first)

- **Bailey & López de Prado (2014), "The Probability of Backtest Overfitting" (PBO).**
  The probability of selecting an overfit strategy grows rapidly with the number of configurations you
  try. Try 1,000 variants and you will find a great-looking backtest by pure chance.
  → [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253)

- **Bailey & López de Prado (2014), "The Deflated Sharpe Ratio."**
  Corrects a reported Sharpe for the number of trials and for non-normal returns. Use it to discount any
  Sharpe you found after searching many strategies.
  → [SSRN 2460551](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551)

- **Harvey & Liu, "Backtesting" and "…and the Cross-Section of Expected Returns."**
  Multiple-testing in finance: most published "factors" are false discoveries. Apply a higher t-stat
  hurdle (~3.0, not 2.0) and "haircut" your Sharpe for the number of tests.
  → search SSRN "Harvey Liu Backtesting"

**Takeaway for this project:** every Gate 1 result should be treated as inflated until validated
out-of-sample (walk-forward) and discounted for how many variants you tried.

---

## 2. Foundational anomalies (where edges actually come from)

- **Jegadeesh & Titman (1993), cross-sectional momentum.** Past 3–12 month winners keep outperforming
  losers over the next 3–12 months. The original momentum result.
- **Moskowitz, Ooi & Pedersen (2012), "Time Series Momentum."** An asset's own past return predicts its
  future return across asset classes — basis for trend-following / CTA strategies.
- **Gatev, Goetzmann & Rouwenhorst (2006), "Pairs Trading."** Mean-reversion between historically
  co-moving securities; the classic statistical-arbitrage reference.
- **Fama & French (1993, 2015), factor models.** Size, value, profitability, investment — the baseline
  risk factors any equity strategy should be checked against (is your "alpha" just factor exposure?).

---

## 3. Practitioner texts

- **López de Prado, "Advances in Financial Machine Learning" (2018).** The modern bible for ML in
  trading: triple-barrier labeling, purged & combinatorial cross-validation, meta-labeling, sample
  uniqueness. Directly relevant if you extend the XGBoost/FinBERT work from your Summer Project.
- **Ernest Chan, "Quantitative Trading" (2009) & "Algorithmic Trading" (2013).** The most accessible
  on-ramp: how to go from idea → backtest → execution as a solo/retail quant, with realistic caveats.

---

## 4. Transaction costs & microstructure (why paper ≠ live)

- Costs and slippage are what kill paper-profitable strategies. Before trusting any high-turnover
  backtest, model commission + slippage + bid/ask, and re-check whether the edge survives.
- Accessible references: Kissell, "The Science of Algorithmic Trading and Portfolio Management";
  and any introduction to market microstructure (limit order book, price impact).

**Takeaway:** the project's `BacktestEngine` already charges 0.1% commission + 0.1% slippage on every
position change. For higher-frequency ideas, raise these and confirm the strategy still clears Gate 1.

---

*Note: book links omitted (use your library / publisher). SSRN/arXiv links above are open access where
available. When a link 404s, search the title on SSRN or Google Scholar.*
