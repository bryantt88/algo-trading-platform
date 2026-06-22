---
name: new-strategy
description: Scaffold a new trading strategy in this project. Use when the user wants to create/add a new strategy. Generates strategies/<name>.py from the BaseStrategy template, a configs/<name>.yaml, and a tests/test_<name>.py stub, all wired to the project conventions.
---

# Scaffold a new strategy

Use this when the user wants to add a new strategy. Follow these steps exactly.

## Step 1 — Gather intent
Ask (or infer from the request) the strategy's:
- **name** (snake_case, e.g. `bollinger_reversion`)
- **class name** (PascalCase, e.g. `BollingerReversionStrategy`)
- **idea** in one sentence and the indicators/data it needs
- whether it is **long-only** or **long/short**

If the idea is non-trivial or the user is unsure of the edge, suggest running the
`strategy-researcher` agent first.

## Step 2 — Read conventions
Read `strategies/base.py` and an existing example (`strategies/momentum.py`) so the new file matches:
- inherit `BaseStrategy`
- implement `generate_signals(self, data) -> pd.Series` returning +1 / -1 / 0
- **do NOT shift signals** inside the strategy (the engine shifts by 1 bar)
- call `self.validate_data(data)` at the top of `generate_signals`
- use a `DEFAULTS` dict merged in `__init__`

## Step 3 — Create three files
1. `strategies/<name>.py` — the strategy class from the template below.
2. `configs/<name>.yaml` — parameters (mirror the `DEFAULTS`).
3. `tests/test_<name>.py` — at minimum: signals are in {-1,0,1}, length matches input, no NaN.

## Step 4 — Register and verify
- Add the class to `strategies/__init__.py` `__all__`.
- Add it to the `STRATEGIES` dict in `dashboard/app.py` so it shows in the dashboard.
- Run `python -m pytest tests/test_<name>.py -v` and confirm it passes.

## Strategy template
```python
import pandas as pd
from strategies.base import BaseStrategy


class <ClassName>(BaseStrategy):
    """<one-line description of the edge>."""

    DEFAULTS = {"param": 20, "allow_short": False}

    def __init__(self, symbol: str, config: dict = None):
        super().__init__(symbol, {**self.DEFAULTS, **(config or {})})

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        self.validate_data(data)
        # ... compute indicators from data["Close"] etc.
        # return +1 long / -1 short / 0 flat, aligned to data.index, NOT pre-shifted
        raise NotImplementedError
```

After scaffolding, remind the user the next step is a Gate 1 backtest (`run-backtest` skill).
