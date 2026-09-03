"""Tests de moving_average_gap_pct -- el indicador de "qué tan cerca" está un
activo de un cruce de medias, usado para mostrar actividad del sistema en el
dashboard incluso cuando no hay ninguna operación."""

import pandas as pd
import pytest

from src.backtest.strategy_baseline import moving_average_crossover, moving_average_gap_pct


def test_none_con_historial_insuficiente():
    df = pd.DataFrame({"close": range(1, 30)}, dtype=float)  # menos de 50 filas
    assert moving_average_gap_pct(df) is None


def test_calcula_el_gap_correctamente_con_tendencia_creciente():
    # 50 cierres 1..50: media rápida (últimos 20: 31..50) > media lenta (1..50)
    # porque la tendencia es creciente -- el gap debe ser positivo
    df = pd.DataFrame({"close": range(1, 51)}, dtype=float)
    gap = moving_average_gap_pct(df)
    fast_ma = sum(range(31, 51)) / 20  # 40.5
    slow_ma = sum(range(1, 51)) / 50  # 25.5
    expected = (fast_ma - slow_ma) / slow_ma * 100
    assert gap == pytest.approx(expected)
    assert gap > 0


def test_gap_negativo_con_tendencia_decreciente():
    df = pd.DataFrame({"close": range(50, 0, -1)}, dtype=float)
    gap = moving_average_gap_pct(df)
    assert gap < 0


def test_gap_cercano_a_cero_con_precio_constante():
    df = pd.DataFrame({"close": [100.0] * 60})
    gap = moving_average_gap_pct(df)
    assert gap == pytest.approx(0.0)


def test_no_es_una_senal_de_trading_es_independiente_del_cruce():
    # el gap es informativo -- no reemplaza a moving_average_crossover, que
    # sigue siendo la única fuente real de gatillos
    df = pd.DataFrame({"close": [100.0] * 60})
    assert moving_average_crossover(df) == "hold"
    assert moving_average_gap_pct(df) is not None
