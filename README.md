# Alpaca Autonomous Trading Platform

An algorithmic trading platform built in Python using Alpaca's API, being developed toward an event-driven system for automated equity analysis, systematic order routing, and capital preservation. The current development milestone delivers account connectivity, historical market data ingestion, and systematic signal generation through command-line workflows.

## Architecture

The platform follows a decoupled architecture with four core pillars:

| Pillar | Responsibility | Implementation status |
| --- | --- | --- |
| Data Ingestion | Retrieve multi-asset historical OHLCV bars and normalize them into UTC-indexed pandas DataFrames. | Implemented in `data_feed.py`. |
| Signal Engine | Evaluate EMA trend filters and RSI pullback conditions on completed bars. | Implemented in `strategy.py`. |
| Risk & Execution | Apply capital limits, size positions, and route bracket orders with stop-loss and take-profit protection. | Risk constants defined in `config.py`; execution planned for Phase 4. |
| Audit Logging | Persist transactions and expose operational and performance monitoring. | SQLite persistence and a Streamlit cockpit planned for Phase 5. |

Event-driven orchestration is the target architecture; the implemented entry points currently execute on demand.

## Implementation roadmap

- [x] **Phase 1: Authentication & Account Handshake** — Secure local `.env` credentials and Alpaca paper trading client.
- [x] **Phase 2: Market Data Pipeline** — Historical OHLCV multi-asset ingestion via pandas.
- [x] **Phase 3: Systematic Strategy Engine** — EMA 9/21 trend filter and 14-period RSI pullback logic.
- [ ] **Phase 4: Execution & Risk Management** — Bracket orders, take-profit/stop-loss caps, and automated position sizing.
- [ ] **Phase 5: Audit Persistence & Performance Cockpit** — SQLite transaction logging and Streamlit monitoring.

## What is implemented

| File | Purpose |
| --- | --- |
| `config.py` | Loads and validates credentials from `.env`; exports the watchlist and risk settings. |
| `test_connection.py` | Connects to the paper account and prints account status, cash, buying power, equity, and whether the market is open. |
| `data_feed.py` | Fetches historical IEX bars and returns one pandas DataFrame per symbol. |
| `strategy.py` | Calculates EMA 9, EMA 21, and RSI 14; generates BUY, SELL, or HOLD signals and prints a watchlist table. |
| `requirements.txt` | Declares `alpaca-py`, `python-dotenv`, and `pandas`. |
| `.vscode/settings.json` | Sets the default Python interpreter to the project's `.venv`. |

Data flows from `.env` through `config.py` into `data_feed.py`, then into `strategy.py`. The account diagnostic script loads `.env` independently and uses `TradingClient(..., paper=True)`.

## Setup on macOS

You need Python 3.10 or newer, an Alpaca paper-trading account with API credentials, and an internet connection for API requests. Run the following from the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Create a file named `.env` in the project root:

```dotenv
ALPACA_API_KEY=your_paper_api_key
ALPACA_SECRET_KEY=your_paper_secret_key
```

Use your actual paper-trading credentials only in the local file. `.env` and `.venv` are excluded by `.gitignore`. Missing or empty credentials produce a configuration error. Both configuration loaders resolve `.env` relative to their Python file, and existing environment variables take precedence over values in `.env`.

## Run the project

Activate the environment in each new terminal session:

```bash
source .venv/bin/activate
```

### Check account status and cash balance

```bash
python test_connection.py
```

Prints a console table with account status, cash balance, buying power, portfolio equity, and market OPEN/CLOSED status. Missing dependencies trigger a macOS setup guide; account request failures produce a concise error without printing API exception payloads.

### Inspect market data

```bash
python data_feed.py
```

Fetches the watchlist and prints the last five rows for SPY and NVDA. Defaults are 15-minute bars over the past five calendar days, using UTC timestamps.

### Generate strategy signals

```bash
python strategy.py
```

Prints the signal, latest close, EMA 9, EMA 21, RSI 14, and bar timestamp for each watchlist asset. The command excludes the ongoing 15-minute bar before calculating signals. Each command runs once and exits; there is no background polling or trading loop.

## Configuration

Edit these constants in `config.py`:

| Constant | Default |
| --- | --- |
| `WATCHLIST` | `["SPY", "QQQ", "AAPL", "MSFT", "NVDA"]` |
| `MAX_POSITION_SIZE_USD` | `10000.0` |
| `STOP_LOSS_PCT` | `0.02` (2%) |
| `TAKE_PROFIT_PCT` | `0.04` (4%) |

The risk parameters are configuration values for future execution logic. They do not currently size positions or place stop-loss/take-profit orders.

## Market data interface

```python
from data_feed import get_recent_bars

bars = get_recent_bars(
    symbols=["SPY", "NVDA"],
    timeframe_minutes=15,
    lookback_days=5,
)
print(bars["SPY"].tail())
```

`get_recent_bars(...) -> dict[str, pd.DataFrame]` returns a frame for each requested symbol, with:

- A sorted, UTC-aware index named `timestamp`.
- Columns `open`, `high`, `low`, `close`, `volume`, and `vwap`.
- An empty frame with the same schema when a symbol has no returned bars.

Ticker strings are stripped, uppercased, and deduplicated. An empty symbol list returns an empty dictionary. Minute intervals must be integers from 1 to 59; the lookback must be a positive integer.

The feed explicitly requests IEX data, which represents IEX activity rather than consolidated SIP market data. The lookback counts calendar days, so weekends and holidays can reduce the number of available bars. The data function can include an ongoing bar; the strategy command filters it out. API errors propagate to callers of the function, while the command-line entry point displays a general diagnostic message.

## Strategy interface and rules

```python
from strategy import generate_signals

# completed_bars is a dictionary of chronological DataFrames containing
# completed bars, such as the filtered frames used in strategy.main().
signals = generate_signals(completed_bars)
print(signals["SPY"])
```

`generate_signals(data_dict: dict[str, pd.DataFrame]) -> dict[str, dict]` evaluates the final row of each input frame. Direct callers must supply chronological, completed bars; completion filtering is handled by the command-line workflow, not by this function.

For frames with at least 30 rows, the function appends `EMA_9`, `EMA_21`, and `RSI_14` columns **in place**. EMAs use pandas exponential weighting with `adjust=False`. RSI uses Wilder smoothing, initialized with the average gains and losses over the first 14 price changes. All-gain prices produce RSI 100, all-loss prices produce RSI 0, and flat prices produce RSI 50. No external technical-analysis library is required.

| Signal | Condition on the final bar |
| --- | --- |
| BUY | `EMA_9 > EMA_21` **and** `RSI_14 < 45` |
| SELL | `EMA_9 < EMA_21` **or** `RSI_14 > 70` |
| HOLD | Neither condition applies, or fewer than 30 bars are available. |

These rules compare current indicator values; they do not require an EMA crossover between consecutive bars.

Each symbol's result contains:

```python
{
    "symbol": ticker,
    "signal": "BUY",  # or "SELL" / "HOLD"
    "current_price": latest_close,
    "ema_9": latest_ema_9,
    "ema_21": latest_ema_21,
    "rsi_14": latest_rsi_14,
    "timestamp": latest_timestamp,
}
```

Insufficient data returns HOLD with a `reason` field and `None` for the indicators. An empty frame also has `None` for its price and timestamp. Unsorted indexes are rejected; frames eligible for indicator calculation must contain finite numeric close prices.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `No module named 'alpaca'`, `'dotenv'`, or `'pandas'` | Activate `.venv` and run `python -m pip install -r requirements.txt`. The Alpaca package name is `alpaca-py`. |
| Yellow import underline in the editor | Use **Python: Select Interpreter** and choose `.venv/bin/python`. |
| Missing or empty credentials | Set both credential names exactly as shown in the root `.env`; also check for empty exported environment variables. |
| Account or market data request fails | Verify paper credentials, connectivity, and market data access. |
| No bars or HOLD due to insufficient data | Check the date range and available trading sessions; increase `lookback_days` when calling the feed if needed. |

## Validation and development workflow

Integration and connectivity were validated directly against the live Alpaca Paper Trading REST API and IEX historical data endpoints using the local `.venv` environment:

| Integration check | Result |
| --- | --- |
| Paper account authentication and account retrieval | Passed. |
| Market clock retrieval | Passed. |
| IEX historical bars for SPY, QQQ, AAPL, MSFT, and NVDA | Passed; non-empty data returned for all five assets. |

These were read-only API checks; no orders were submitted. Indicator calculations and signal boundaries were also checked with sample price series, including Wilder RSI reference values, rising/falling/flat prices, and insufficient-data handling. A persistent automated test suite remains future work; connectivity validation does not establish strategy performance.

For local development, activate `.venv`, install `requirements.txt`, and run `test_connection.py`, `data_feed.py`, and `strategy.py` in sequence. Recheck connectivity after credential or dependency changes, and validate indicator behavior after strategy changes. Phases 4 and 5 track the remaining execution, risk enforcement, persistence, and monitoring work.
