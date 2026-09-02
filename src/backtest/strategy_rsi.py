"""Estrategia candidata de reversión a la media (RSI) -- carácter distinto al
cruce de medias móviles (que sigue tendencia): busca rebotes después de una
sobreventa/sobrecompra, algo que en mercados laterales o picados puede
disparar más seguido que un cruce de tendencia."""

import pandas as pd


def compute_rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def rsi_reversion(df: pd.DataFrame, period: int = 14, oversold: float = 30, overbought: float = 70) -> str:
    if len(df) < period + 2:
        return "hold"

    rsi = compute_rsi(df["close"].tail(period + 30), period)
    if len(rsi.dropna()) < 2:
        return "hold"

    prev, last = rsi.iloc[-2], rsi.iloc[-1]
    if prev < oversold <= last:
        return "buy"
    if prev > overbought >= last:
        return "sell"
    return "hold"
