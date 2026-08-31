"""Descarga de datos históricos de pares forex vía yfinance."""

from pathlib import Path

import yfinance as yf
import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def fetch_forex(
    pair: str,
    start: str = "2018-01-01",
    end: str | None = None,
    interval: str = "1d",
) -> pd.DataFrame:
    ticker = f"{pair}=X"
    df = yf.download(ticker, start=start, end=end, interval=interval, progress=False)
    df = df.reset_index()
    df.columns = [str(c[0]).lower() if isinstance(c, tuple) else str(c).lower() for c in df.columns]
    df = df.rename(columns={"date": "timestamp", "datetime": "timestamp"})
    return df[["timestamp", "open", "high", "low", "close", "volume"]]


def fetch_current_price(pair: str) -> float:
    """Precio en vivo, sin descargar velas -- para el vigía de volatilidad."""
    return yf.Ticker(f"{pair}=X").fast_info["last_price"]


def save_forex(
    pair: str,
    start: str = "2018-01-01",
    end: str | None = None,
    interval: str = "1d",
) -> Path:
    df = fetch_forex(pair, start, end, interval)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"forex_{pair}_{interval}.csv"
    df.to_csv(path, index=False)
    return path
