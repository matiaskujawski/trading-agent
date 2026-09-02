"""Calcula, para cada activo, el umbral de % de movimiento diario que
corresponde a un evento realmente raro (percentil elegido sobre el desvío
máximo respecto al cierre anterior). Los valores que imprime son los que
están hardcodeados en src/execution/shock_watchdog.py -- correr de nuevo
cuando se quiera recalibrar con datos más recientes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
PERCENTILE = 0.97  # ~9 disparos/año

SYMBOL_BY_FILENAME = {
    "binance_BTC-USDT_1d": "BTC/USDT",
    "binance_ETH-USDT_1d": "ETH/USDT",
    "binance_LINK-USDT_1d": "LINK/USDT",
    "binance_UNI-USDT_1d": "UNI/USDT",
    "binance_CAKE-USDT_1d": "CAKE/USDT",
    "binance_XRP-USDT_1d": "XRP/USDT",
    "forex_EURUSD_1d": "EURUSD",
    "forex_GBPUSD_1d": "GBPUSD",
    "forex_USDJPY_1d": "USDJPY",
    "forex_USDCHF_1d": "USDCHF",
    "forex_AUDUSD_1d": "AUDUSD",
    "binance_SOL-USDT_1d": "SOL/USDT",
    "binance_ADA-USDT_1d": "ADA/USDT",
    "binance_DOT-USDT_1d": "DOT/USDT",
    "binance_AVAX-USDT_1d": "AVAX/USDT",
    "binance_LTC-USDT_1d": "LTC/USDT",
    "forex_USDCAD_1d": "USDCAD",
}

if __name__ == "__main__":
    for csv_path in sorted(RAW_DIR.glob("*.csv")):
        symbol = SYMBOL_BY_FILENAME.get(csv_path.stem)
        if symbol is None:
            continue
        df = pd.read_csv(csv_path, parse_dates=["timestamp"])
        prev_close = df["close"].shift(1)
        dev_up = (df["high"] - prev_close) / prev_close * 100
        dev_down = (prev_close - df["low"]) / prev_close * 100
        max_dev = pd.concat([dev_up, dev_down], axis=1).max(axis=1).dropna()

        threshold = max_dev.quantile(PERCENTILE)
        print(f'    "{symbol}": {threshold:.1f},')
