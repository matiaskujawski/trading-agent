"""Tests del contrato de la respuesta del LLM. El punto central: sin importar
qué mande el LLM -- bien formado, mal formado, o directamente basura -- esto
nunca debe reventar, y el peor caso posible es "no operar" (hold, tamaño 0)."""

from src.llm_decision.decision_schema import validate_decision


def test_decision_valida_pasa_sin_cambios():
    result = validate_decision({"action": "buy", "confidence": 0.8, "suggested_size_fraction": 0.5, "reasoning": "cruce alcista"})
    assert result == {"action": "buy", "confidence": 0.8, "suggested_size_fraction": 0.5, "reasoning": "cruce alcista"}


def test_accion_invalida_cae_a_hold():
    result = validate_decision({"action": "hodl", "confidence": 0.9, "suggested_size_fraction": 1.0})
    assert result["action"] == "hold"
    assert result["confidence"] == 0.0
    assert result["suggested_size_fraction"] == 0.0


def test_accion_ausente_cae_a_hold():
    result = validate_decision({"reasoning": "sin campo action"})
    assert result["action"] == "hold"


def test_confidence_por_encima_de_uno_se_recorta():
    result = validate_decision({"action": "buy", "confidence": 5.0, "suggested_size_fraction": 0.5})
    assert result["confidence"] == 1.0


def test_suggested_size_fraction_negativo_se_recorta_a_cero():
    result = validate_decision({"action": "sell", "confidence": 0.5, "suggested_size_fraction": -3.0})
    assert result["suggested_size_fraction"] == 0.0


def test_campos_ausentes_usan_default_cero():
    result = validate_decision({"action": "buy"})
    assert result["confidence"] == 0.0
    assert result["suggested_size_fraction"] == 0.0
    assert result["reasoning"] == ""


def test_reasoning_se_trunca_a_500_caracteres():
    result = validate_decision({"action": "hold", "reasoning": "x" * 1000})
    assert len(result["reasoning"]) == 500


def test_reasoning_no_string_se_convierte_a_string():
    result = validate_decision({"action": "hold", "reasoning": 12345})
    assert result["reasoning"] == "12345"


def test_confidence_no_numerico_no_revienta_y_cae_a_cero():
    # regresión: un LLM que devuelve JSON válido pero con "confidence": "alta"
    # (string, no número) reventaba con ValueError sin capturar, tirando abajo
    # el ciclo entero -- incluyendo el guardado de estado de operaciones que
    # ya se habían ejecutado antes en el mismo ciclo (stop-loss, etc).
    result = validate_decision({"action": "buy", "confidence": "alta", "suggested_size_fraction": 0.5})
    assert result["confidence"] == 0.0
    assert result["suggested_size_fraction"] == 0.5


def test_suggested_size_fraction_null_no_revienta_y_cae_a_cero():
    result = validate_decision({"action": "buy", "confidence": 0.7, "suggested_size_fraction": None})
    assert result["suggested_size_fraction"] == 0.0


def test_confidence_nan_no_revienta_y_cae_a_cero():
    result = validate_decision({"action": "buy", "confidence": float("nan"), "suggested_size_fraction": 0.5})
    assert result["confidence"] == 0.0


def test_raw_no_es_dict_no_revienta():
    # ej: el LLM devuelve un array JSON válido en vez de un objeto
    result = validate_decision([1, 2, 3])
    assert result["action"] == "hold"
    assert result["confidence"] == 0.0
