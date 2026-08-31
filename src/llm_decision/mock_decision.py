"""Decisión de referencia sin LLM real: prueba que el contrato completo
(resumen de mercado -> decisión -> validación) funciona de punta a punta,
sin gastar tokens todavía. Se reemplaza por una llamada real a la API de
Claude cuando armemos paper trading (etapa 6)."""

from src.llm_decision.decision_schema import validate_decision


def mock_decision(market_summary: dict) -> dict:
    trigger = market_summary["trigger_reason"]

    if trigger == "cruce_alcista_medias_moviles":
        raw = {"action": "buy", "confidence": 0.6, "suggested_size_fraction": 1.0, "reasoning": "mock: sigue la señal técnica del gatillo"}
    elif trigger == "cruce_bajista_medias_moviles":
        raw = {"action": "sell", "confidence": 0.6, "suggested_size_fraction": 1.0, "reasoning": "mock: sigue la señal técnica del gatillo"}
    else:
        raw = {"action": "hold", "confidence": 0.0, "suggested_size_fraction": 0.0, "reasoning": "mock: sin gatillo reconocido"}

    return validate_decision(raw)
