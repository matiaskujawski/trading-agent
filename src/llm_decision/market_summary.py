"""Arma el resumen estructurado de mercado que recibe el LLM al decidir.
Compacto a propósito: cada campo de más es texto que hay que pagar (en tokens)
y que puede distraer al modelo de lo importante."""

import pandas as pd


def build_market_summary(
    df: pd.DataFrame, symbol: str, trigger_reason: str, risk_state: dict, sentiment_context: dict | None = None
) -> dict:
    """
    df: histórico hasta el momento actual (incluye la última vela).
    risk_state: estado actual de la capa de riesgo, ej:
        {"daily_loss_used_pct": 0.4, "distance_to_max_drawdown_pct": 0.85, "max_position_size_usd": 25.0}
    sentiment_context: salida de src.data_pipeline.sentiment.build_sentiment_context().
        Solo aplica a cripto -- forex no tiene equivalente, se omite (None) para esos activos.
        Es contexto de bajo peso: nunca reemplaza a la señal técnica de precio.
    """
    last = df.iloc[-1]
    closes = df["close"]

    ma_fast = closes.tail(20).mean()
    ma_slow = closes.tail(50).mean()
    volatility_20d = closes.tail(20).pct_change().std()

    summary = {
        "symbol": symbol,
        "timestamp": str(last["timestamp"]),
        "price": float(last["close"]),
        "trigger_reason": trigger_reason,
        "indicators": {
            "ma_fast_20": round(float(ma_fast), 4),
            "ma_slow_50": round(float(ma_slow), 4),
            "volatility_20d_pct": round(float(volatility_20d) * 100, 2),
        },
        "risk_budget": risk_state,
    }
    if sentiment_context is not None:
        summary["contexto_mercado_amplio"] = sentiment_context
    return summary
