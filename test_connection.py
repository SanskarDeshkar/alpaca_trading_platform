"""Display paper trading account balances and market status."""

import os
import sys
from pathlib import Path

try:
    from alpaca.trading.client import TradingClient
    from dotenv import load_dotenv
except ModuleNotFoundError as exc:
    print(
        f"\nMissing Python dependency: {exc.name}\n"
        "\nmacOS setup — run these commands from the project directory:\n"
        "  1. source .venv/bin/activate\n"
        "  2. python -m pip install alpaca-py python-dotenv\n"
        "  3. python test_connection.py\n"
        "\nIf .venv does not exist, create it first: python3 -m venv .venv\n",
        file=sys.stderr,
    )
    sys.exit(1)


def main():
    load_dotenv(Path(__file__).resolve().parent / ".env")
    api_key = os.getenv("ALPACA_API_KEY", "").strip()
    secret_key = os.getenv("ALPACA_SECRET_KEY", "").strip()
    missing = [
        name
        for name, value in (
            ("ALPACA_API_KEY", api_key),
            ("ALPACA_SECRET_KEY", secret_key),
        )
        if not value
    ]
    if missing:
        raise ValueError(
            f"Missing or empty credentials: {', '.join(missing)}. "
            "Set ALPACA_API_KEY=your_paper_api_key and "
            "ALPACA_SECRET_KEY=your_paper_secret_key on separate lines in "
            "the .env file beside test_connection.py."
        )

    try:
        client = TradingClient(api_key=api_key, secret_key=secret_key, paper=True)
        account = client.get_account()
        clock = client.get_clock()
    except Exception:
        # Avoid printing exception payloads that might contain sensitive data.
        print(
            "\nUnable to retrieve Alpaca paper account details.\n"
            "Check that your .env credentials are valid Paper Trading keys, "
            "your internet connection works, and Alpaca is available.",
            file=sys.stderr,
        )
        return 1

    rows = [
        ("Account Status", str(getattr(account.status, "value", account.status))),
        ("Cash Balance", f"${float(account.cash):,.2f}"),
        ("Buying Power", f"${float(account.buying_power):,.2f}"),
        ("Portfolio Equity", f"${float(account.equity):,.2f}"),
        ("Market Status", "OPEN" if clock.is_open else "CLOSED"),
    ]
    label_width = max(len(label) for label, _ in rows)
    value_width = max(len(value) for _, value in rows)
    border = f"+-{'-' * label_width}-+-{'-' * value_width}-+"
    print("\nAlpaca Paper Trading")
    print(border)
    for label, value in rows:
        print(f"| {label:<{label_width}} | {value:<{value_width}} |")
    print(border)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)
