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


def _moving_average_gap_series(df: pd.DataFrame, fast: int, slow: int) -> pd.Series:
    """Serie completa del gap % entre media rápida y lenta (no solo el último
    valor) -- hace falta la serie entera para poder medir qué tan disperso es
    normalmente ese gap para este activo en particular, no solo su valor
    actual."""
    closes = df["close"]
    fast_ma = closes.rolling(fast).mean()
    slow_ma = closes.rolling(slow).mean()
    return (fast_ma - slow_ma) / slow_ma * 100


def moving_average_gap_pct(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> float | None:
    """Distancia porcentual CRUDA entre la media rápida y la lenta en el
    último dato disponible. Ojo: esto no es comparable entre activos de
    volatilidad muy distinta -- un par forex de baja volatilidad va a tener
    este % chico casi siempre, aunque no esté especialmente cerca de cruzar
    en términos de su propio comportamiento habitual (ver
    moving_average_gap_zscore, que sí es comparable entre activos). No es
    una señal de trading, solo un dato informativo. None si no hay
    suficiente historial todavía."""
    if len(df) < slow:
        return None

    gap = _moving_average_gap_series(df, fast, slow).iloc[-1]
    return None if pd.isna(gap) else float(gap)


def moving_average_gap_zscore(df: pd.DataFrame, fast: int = 20, slow: int = 50, min_samples: int = 20) -> float | None:
    """Qué tan cerca está el gap actual de un cruce, medido en desvíos
    estándar del gap histórico de ESTE activo -- no en % crudo. Así un
    activo de baja volatilidad (donde el % crudo siempre es chico) y uno de
    alta volatilidad (donde el % crudo siempre es grande) quedan en la misma
    escala real de comparación: cuánto se aleja el gap actual de lo que es
    "normal" para ese activo en particular, no en términos absolutos.
    None si no hay suficiente historial, o si el activo no tuvo dispersión
    (precio constante)."""
    if len(df) < slow:
        return None

    gap_series = _moving_average_gap_series(df, fast, slow).dropna()
    if len(gap_series) < min_samples:
        return None

    std = gap_series.std()
    if pd.isna(std) or std == 0:
        return None

    return float(gap_series.iloc[-1] / std)
