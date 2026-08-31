"""Descarga y guarda en data/raw/ el historial completo del universo de activos aprobado."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import CRYPTO_SYMBOLS, FOREX_PAIRS
from src.data_pipeline.crypto import save_ohlcv
from src.data_pipeline.forex import save_forex

if __name__ == "__main__":
    for symbol in CRYPTO_SYMBOLS:
        print(f"Descargando cripto: {symbol}...")
        path = save_ohlcv(symbol)
        print(f"  guardado en {path}")

    for pair in FOREX_PAIRS:
        print(f"Descargando forex: {pair}...")
        path = save_forex(pair)
        print(f"  guardado en {path}")
