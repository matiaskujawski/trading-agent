"""Contrato de la respuesta del LLM. El LLM nunca propone montos absolutos: solo
una fracción (0 a 1) del tamaño máximo que la capa de riesgo ya autorizó de
antemano. Así, aunque el LLM proponga el máximo con total confianza -- o
directamente devuelva algo mal formado -- el riesgo real nunca supera lo que
los parámetros de riesgo ya permiten."""

import math

ALLOWED_ACTIONS = {"buy", "sell", "hold"}


def _clamp01(value) -> float:
    """Convierte a float y recorta a [0, 1] -- nunca revienta, sin importar
    qué tipo mande el LLM (string, null, NaN, lo que sea): el peor caso es
    tratarlo como 0."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(v):
        return 0.0
    return max(0.0, min(1.0, v))


def validate_decision(raw) -> dict:
    if not isinstance(raw, dict):
        raw = {}

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
        "confidence": _clamp01(raw.get("confidence", 0.0)),
        "suggested_size_fraction": _clamp01(raw.get("suggested_size_fraction", 0.0)),
        "reasoning": str(raw.get("reasoning", ""))[:500],
    }
