"""Descarga de datos históricos de velas (OHLCV) de exchanges cripto vía ccxt."""

import time
from pathlib import Path

import ccxt
import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def _make_exchange(exchange_id: str):
    """api.binance.com devuelve 451 ("restricted location") desde los runners de
    GitHub Actions -- confirmado en producción (ver Actions run del 2026-09-02
    01:51 UTC), lo que dejó todo el universo cripto sin datos desde el primer
    ciclo real. data-api.binance.vision es el espejo público de solo-datos-de-
    mercado que Binance documenta para este caso exacto (klines/ticker/
    exchangeInfo, sin cuenta ni auth) y no aplica la misma restricción
    geográfica. Solo afecta los endpoints públicos que usamos acá."""
    exchange = getattr(ccxt, exchange_id)()
    if exchange_id == "binance":
        exchange.urls["api"]["public"] = "https://data-api.binance.vision/api/v3"
    return exchange


def fetch_ohlcv(
    symbol: str,
    timeframe: str = "1d",
    exchange_id: str = "binance",
    since: str = "2018-01-01",
) -> pd.DataFrame:
    exchange = _make_exchange(exchange_id)
    since_ms = exchange.parse8601(f"{since}T00:00:00Z")
    all_candles = []

    while True:
        candles = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since_ms, limit=1000)
        if not candles:
            break
        all_candles += candles
        since_ms = candles[-1][0] + 1
        if len(candles) < 1000:
            break
        time.sleep(exchange.rateLimit / 1000)

    df = pd.DataFrame(all_candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def fetch_current_price(symbol: str, exchange_id: str = "binance") -> float:
    """Precio en vivo, sin descargar velas -- para el vigía de volatilidad."""
    exchange = _make_exchange(exchange_id)
    return exchange.fetch_ticker(symbol)["last"]


def save_ohlcv(
    symbol: str,
    timeframe: str = "1d",
    exchange_id: str = "binance",
    since: str = "2018-01-01",
) -> Path:
    df = fetch_ohlcv(symbol, timeframe, exchange_id, since)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{exchange_id}_{symbol.replace('/', '-')}_{timeframe}.csv"
    df.to_csv(path, index=False)
    return path
