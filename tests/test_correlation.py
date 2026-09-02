"""Tests del límite de correlación entre posiciones abiertas. El punto clave
del diseño (encontrado como bug real y corregido durante el desarrollo): solo
bloquea correlación POSITIVA -- una posición que se mueve en la dirección
opuesta a otra abierta es una cobertura natural, no debe bloquearse."""

import pandas as pd
import pytest

from src.risk.correlation import max_correlation_with_open, passes_correlation_limit

CANDIDATE = pd.Series(range(20), dtype=float)


def test_sin_posiciones_abiertas_no_hay_correlacion():
    corr, symbol = max_correlation_with_open(CANDIDATE, {})
    assert corr == 0.0
    assert symbol is None


def test_detecta_correlacion_positiva_alta():
    open_returns = {"BTC/USDT": CANDIDATE * 2}  # transformación lineal positiva -> corr = 1.0
    corr, symbol = max_correlation_with_open(CANDIDATE, open_returns)
    assert corr == pytest.approx(1.0)
    assert symbol == "BTC/USDT"


def test_correlacion_negativa_no_se_reporta_como_bloqueante():
    # dos posiciones que se mueven en direcciones opuestas son una cobertura
    # natural, no una concentración oculta -- el diseño explícitamente no las
    # trata como "la correlación más alta" (best_corr arranca en 0.0 y solo
    # sube con corr > best_corr, nunca con una corr negativa)
    open_returns = {"BTC/USDT": -CANDIDATE}  # corr = -1.0
    corr, symbol = max_correlation_with_open(CANDIDATE, open_returns)
    assert corr == 0.0
    assert symbol is None


def test_ignora_series_con_poco_solapamiento():
    short_series = pd.Series(range(5), dtype=float)  # menos de 10 puntos alineados
    corr, symbol = max_correlation_with_open(CANDIDATE, {"BTC/USDT": short_series})
    assert corr == 0.0
    assert symbol is None


def test_elige_la_correlacion_positiva_mas_alta_entre_varias_abiertas():
    open_returns = {
        "ETH/USDT": pd.Series([1, -1] * 10, dtype=float),  # correlación baja
        "BTC/USDT": CANDIDATE * 3,  # correlación positiva perfecta
    }
    corr, symbol = max_correlation_with_open(CANDIDATE, open_returns)
    assert corr == pytest.approx(1.0)
    assert symbol == "BTC/USDT"


def test_passes_correlation_limit_bloquea_por_encima_del_umbral():
    open_returns = {"BTC/USDT": CANDIDATE * 2}  # corr 1.0
    ok, corr, blocker = passes_correlation_limit(CANDIDATE, open_returns, threshold=0.5)
    assert not ok
    assert blocker == "BTC/USDT"


def test_passes_correlation_limit_ok_por_debajo_del_umbral():
    alternating = pd.Series([1, -1] * 10, dtype=float)  # sin tendencia, baja correlación con CANDIDATE
    ok, corr, blocker = passes_correlation_limit(CANDIDATE, {"BTC/USDT": alternating}, threshold=0.5)
    assert ok
    assert corr <= 0.5
