"""EMA/RSI signals for chronological, completed price bars."""

import math
import sys

import pandas as pd


def calculate_rsi(close: pd.Series, periods: int = 14) -> pd.Series:
    """Wilder RSI, seeded with the mean of the first `periods` changes.

    All gains yield 100, all losses yield 0, and flat prices yield 50.
    """
    if periods < 1:
        raise ValueError("periods must be positive.")
    changes = close.diff()
    gains = changes.clip(lower=0)
    losses = -changes.clip(upper=0)
    if len(close) <= periods:
        return pd.Series(float("nan"), index=close.index, dtype=float)
    gains.iloc[periods] = gains.iloc[1 : periods + 1].mean()
    losses.iloc[periods] = losses.iloc[1 : periods + 1].mean()
    gains.iloc[:periods] = float("nan")
    losses.iloc[:periods] = float("nan")
    avg_gain = gains.ewm(alpha=1 / periods, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1 / periods, adjust=False).mean()
    rsi = 100 - 100 / (1 + avg_gain / avg_loss)
    return rsi.mask((avg_gain == 0) & (avg_loss == 0), 50.0)


def generate_signals(data_dict: dict[str, pd.DataFrame]) -> dict[str, dict]:
    """Append indicators in place and evaluate the final row of each frame.

    Callers must supply chronological, completed bars. Fewer than 30 rows
    produce HOLD with unavailable indicators set to None and a reason.
    """
    results: dict[str, dict] = {}
    for symbol, frame in data_dict.items():
        if not frame.index.is_monotonic_increasing:
            raise ValueError(f"{symbol}: bars must be ordered by timestamp.")
        close = pd.to_numeric(frame["close"], errors="coerce")
        result = {
            "symbol": symbol,
            "signal": "HOLD",
            "current_price": float(close.iloc[-1]) if len(close) else None,
            "ema_9": None,
            "ema_21": None,
            "rsi_14": None,
            "timestamp": frame.index[-1] if len(frame) else None,
        }
        if len(frame) < 30:
            result["reason"] = "Insufficient data (at least 30 bars required)"
            results[symbol] = result
            continue
        if not close.map(math.isfinite).all():
            raise ValueError(f"{symbol}: close prices must be finite numbers.")

        frame["EMA_9"] = close.ewm(span=9, adjust=False).mean()
        frame["EMA_21"] = close.ewm(span=21, adjust=False).mean()
        frame["RSI_14"] = calculate_rsi(close)
        ema_9 = float(frame["EMA_9"].iloc[-1])
        ema_21 = float(frame["EMA_21"].iloc[-1])
        rsi_14 = float(frame["RSI_14"].iloc[-1])
        result.update(ema_9=ema_9, ema_21=ema_21, rsi_14=rsi_14)
        if ema_9 > ema_21 and rsi_14 < 45:
            result["signal"] = "BUY"
        elif ema_9 < ema_21 or rsi_14 > 70:
            result["signal"] = "SELL"
        results[symbol] = result
    return results


def main() -> int:
    """Fetch the watchlist and display signals without placing orders."""
    try:
        from config import WATCHLIST
        from data_feed import get_recent_bars

        frames = get_recent_bars(WATCHLIST)
        # Alpaca timestamps mark bar starts; exclude the ongoing 15-minute bar.
        cutoff = pd.Timestamp.now(tz="UTC").floor("15min")
        completed = {
            symbol: frame.loc[frame.index < cutoff].copy()
            for symbol, frame in frames.items()
        }
        signals = generate_signals(completed)
    except Exception:
        print(
            "Unable to generate signals. Check dependencies, .env credentials, "
            "market data access, connectivity, and valid chronological bars.",
            file=sys.stderr,
        )
        return 1

    table = pd.DataFrame(signals.values()).rename(columns={
        "symbol": "Symbol", "signal": "Signal", "current_price": "Price ($)",
        "ema_9": "EMA 9", "ema_21": "EMA 21", "rsi_14": "RSI 14",
        "timestamp": "Timestamp (UTC)", "reason": "Reason",
    })
    print("\nStrategy signals — completed 15-minute IEX bars")
    print(table.fillna("—").to_string(index=False, float_format=lambda value: f"{value:,.2f}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
