"""Contrato de la respuesta del LLM. El LLM nunca propone montos absolutos: solo
una fracción (0 a 1) del tamaño máximo que la capa de riesgo ya autorizó de
antemano. Así, aunque el LLM proponga el máximo con total confianza -- o
directamente devuelva algo mal formado -- el riesgo real nunca supera lo que
los parámetros de riesgo ya permiten."""

ALLOWED_ACTIONS = {"buy", "sell", "hold"}


def validate_decision(raw: dict) -> dict:
    action = raw.get("action")
    if action not in ALLOWED_ACTIONS:
        return {
            "action": "hold",
            "confidence": 0.0,
            "suggested_size_fraction": 0.0,
            "reasoning": "respuesta inválida del LLM -- se ignora y no se opera",
        }

    return {
        "action": action,
        "confidence": max(0.0, min(1.0, float(raw.get("confidence", 0.0)))),
        "suggested_size_fraction": max(0.0, min(1.0, float(raw.get("suggested_size_fraction", 0.0)))),
        "reasoning": str(raw.get("reasoning", ""))[:500],
    }
