"""Estrategia candidata de rebote en bandas de Bollinger -- carácter de
volatilidad, distinto tanto del cruce de medias (tendencia) como del RSI
(momentum): opera cuando el precio toca y rebota desde el borde de su rango
"normal" reciente."""

import pandas as pd


def bollinger_bounce(df: pd.DataFrame, period: int = 20, num_std: float = 2.0) -> str:
    if len(df) < period + 2:
        return "hold"

    closes = df["close"].tail(period + 2)
    ma = closes.rolling(period).mean()
    std = closes.rolling(period).std()
    upper = ma + num_std * std
    lower = ma - num_std * std

    if pd.isna(upper.iloc[-2]) or pd.isna(lower.iloc[-2]):
        return "hold"

    prev_price, price = closes.iloc[-2], closes.iloc[-1]

    if prev_price <= lower.iloc[-2] and price > lower.iloc[-1]:
        return "buy"
    if prev_price >= upper.iloc[-2] and price < upper.iloc[-1]:
        return "sell"
    return "hold"
