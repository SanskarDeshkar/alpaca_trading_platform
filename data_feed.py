"""Fetch recent equity bars as individual UTC-indexed DataFrames."""

from datetime import datetime, timedelta, timezone
import sys

import pandas as pd
from alpaca.data.enums import DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, WATCHLIST

client = StockHistoricalDataClient(
    api_key=ALPACA_API_KEY, secret_key=ALPACA_SECRET_KEY
)

BAR_COLUMNS: list[str] = ["open", "high", "low", "close", "volume", "vwap"]


def get_recent_bars(
    symbols: list[str], timeframe_minutes: int = 15, lookback_days: int = 5
) -> dict[str, pd.DataFrame]:
    """Return sorted IEX bars for each symbol over a calendar-day lookback.

    Symbols without data receive an empty frame with the same columns and
    UTC timestamp index. SDK authentication/connection errors propagate to
    callers; the command-line entry point reports them without credentials.
    """
    if type(timeframe_minutes) is not int or not 1 <= timeframe_minutes <= 59:
        raise ValueError("timeframe_minutes must be an integer from 1 to 59.")
    if type(lookback_days) is not int or lookback_days <= 0:
        raise ValueError("lookback_days must be a positive integer.")
    if any(not isinstance(symbol, str) or not symbol.strip() for symbol in symbols):
        raise ValueError("symbols must contain non-empty ticker strings.")
    normalized_symbols = list(dict.fromkeys(symbol.strip().upper() for symbol in symbols))
    if not normalized_symbols:
        return {}

    end = datetime.now(timezone.utc)
    request = StockBarsRequest(
        symbol_or_symbols=normalized_symbols,
        start=end - timedelta(days=lookback_days),
        end=end,
        timeframe=TimeFrame(timeframe_minutes, TimeFrameUnit.Minute),
        # IEX works with basic data access; it is not consolidated SIP data.
        feed=DataFeed.IEX,
    )
    response = client.get_stock_bars(request)
    frames: dict[str, pd.DataFrame] = {}
    for symbol in normalized_symbols:
        bars = response.data.get(symbol, [])
        frame = pd.DataFrame(
            [{column: getattr(bar, column) for column in BAR_COLUMNS} for bar in bars],
            columns=BAR_COLUMNS,
            dtype=float,
        )
        frame.index = pd.DatetimeIndex(
            pd.to_datetime([bar.timestamp for bar in bars], utc=True),
            name="timestamp",
        )
        frames[symbol] = frame.sort_index()
    return frames


def main() -> int:
    """Print a small sample to verify the market data feed."""
    try:
        frames = get_recent_bars(WATCHLIST)
    except Exception:
        print(
            "Unable to fetch Alpaca bars. Check your .env credentials, "
            "internet connection, and market data access.",
            file=sys.stderr,
        )
        return 1
    for symbol in ("SPY", "NVDA"):
        print(f"\n{symbol} — latest 5 bars (15-minute, IEX, UTC)")
        frame = frames[symbol]
        print("No bars returned for this period." if frame.empty else frame.tail(5).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
