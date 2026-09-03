"""Estrategia de referencia (cruce de medias móviles), solo para validar el motor
de backtesting. No es la estrategia final: esa la va a proponer el LLM en la etapa 4."""

import pandas as pd


def moving_average_crossover(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> str:
    if len(df) < slow + 1:
        return "hold"

    closes = df["close"].tail(slow + 1)
    fast_ma = closes.rolling(fast).mean()
    slow_ma = closes.rolling(slow).mean()

    crossed_up = fast_ma.iloc[-2] <= slow_ma.iloc[-2] and fast_ma.iloc[-1] > slow_ma.iloc[-1]
    crossed_down = fast_ma.iloc[-2] >= slow_ma.iloc[-2] and fast_ma.iloc[-1] < slow_ma.iloc[-1]

    if crossed_up:
        return "buy"
    if crossed_down:
        return "sell"
    return "hold"


def moving_average_gap_pct(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> float | None:
    """Distancia porcentual entre la media rápida y la lenta en el último dato
    disponible -- cuanto más cerca de 0, más cerca está el activo de un cruce
    (en cualquier dirección). No es una señal de trading, solo un indicador
    de "qué tan cerca" para mostrar en el panel. None si no hay suficiente
    historial todavía."""
    if len(df) < slow:
        return None

    closes = df["close"].tail(slow)
    fast_ma = closes.rolling(fast).mean().iloc[-1]
    slow_ma = closes.rolling(slow).mean().iloc[-1]

    if pd.isna(fast_ma) or pd.isna(slow_ma) or slow_ma == 0:
        return None

    return float((fast_ma - slow_ma) / slow_ma * 100)
