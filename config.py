"""Environment credentials and defaults for the paper-trading system."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

ALPACA_API_KEY: str = os.getenv("ALPACA_API_KEY", "").strip()
ALPACA_SECRET_KEY: str = os.getenv("ALPACA_SECRET_KEY", "").strip()

_missing = [
    name
    for name, value in (
        ("ALPACA_API_KEY", ALPACA_API_KEY),
        ("ALPACA_SECRET_KEY", ALPACA_SECRET_KEY),
    )
    if not value
]
if _missing:
    raise ValueError(
        f"Missing or empty credentials: {', '.join(_missing)}. "
        "Set ALPACA_API_KEY=your_paper_api_key and "
        "ALPACA_SECRET_KEY=your_paper_secret_key on separate lines "
        "in the .env file beside config.py."
    )

WATCHLIST: list[str] = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA"]
MAX_POSITION_SIZE_USD: float = 10000.0
STOP_LOSS_PCT: float = 0.02
TAKE_PROFIT_PCT: float = 0.04

__all__ = [
    "ALPACA_API_KEY",
    "ALPACA_SECRET_KEY",
    "WATCHLIST",
    "MAX_POSITION_SIZE_USD",
    "STOP_LOSS_PCT",
    "TAKE_PROFIT_PCT",
]
