"""Indicadores técnicos reutilizables entre estrategias y el cálculo de riesgo."""

import pandas as pd


def average_true_range(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ATR: promedio móvil del rango real diario (incluye gaps, no solo high-low)."""
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return true_range.rolling(period).mean()
