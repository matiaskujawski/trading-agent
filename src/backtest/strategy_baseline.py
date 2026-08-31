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
