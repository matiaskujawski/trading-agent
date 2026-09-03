"""Tests de moving_average_gap_pct -- el indicador de "qué tan cerca" está un
activo de un cruce de medias, usado para mostrar actividad del sistema en el
dashboard incluso cuando no hay ninguna operación."""

import math

import pandas as pd
import pytest

from src.backtest.strategy_baseline import moving_average_crossover, moving_average_gap_pct, moving_average_gap_zscore


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


def test_zscore_none_con_historial_insuficiente():
    df = pd.DataFrame({"close": range(1, 40)}, dtype=float)  # menos de 50 filas
    assert moving_average_gap_zscore(df) is None


def test_zscore_none_si_el_precio_es_constante():
    # sin dispersión en el gap (std=0), no se puede normalizar -- no debe
    # reventar ni devolver infinito, solo None
    df = pd.DataFrame({"close": [100.0] * 80})
    assert moving_average_gap_zscore(df) is None


def test_zscore_coincide_con_el_calculo_manual():
    closes = [100 + (i % 11) * (1 if i % 2 == 0 else -1) for i in range(120)]
    df = pd.DataFrame({"close": closes}, dtype=float)

    z = moving_average_gap_zscore(df)

    fast_ma = df["close"].rolling(20).mean()
    slow_ma = df["close"].rolling(50).mean()
    gap_series = ((fast_ma - slow_ma) / slow_ma * 100).dropna()
    expected = gap_series.iloc[-1] / gap_series.std()

    assert z == pytest.approx(expected)


def test_normaliza_por_la_volatilidad_propia_del_activo():
    # el problema real que motivó esto: un activo de baja volatilidad (forex)
    # y uno de alta volatilidad (cripto) con la MISMA forma de oscilación
    # relativa dan un % crudo muy distinto, pero deberían quedar en la misma
    # escala real de "qué tan cerca de lo normal para ESE activo" al normalizar
    # período 13 -- no divide exacto ni a la ventana rápida (20) ni a la
    # lenta (50), así que el gap entre medias no se cancela a cero
    pattern = [math.sin(2 * math.pi * i / 13) for i in range(120)]
    df_low_vol = pd.DataFrame({"close": [100 + 0.05 * p for p in pattern]}, dtype=float)
    df_high_vol = pd.DataFrame({"close": [100 + 5.0 * p for p in pattern]}, dtype=float)  # 100x más oscilación

    pct_low = moving_average_gap_pct(df_low_vol)
    pct_high = moving_average_gap_pct(df_high_vol)
    z_low = moving_average_gap_zscore(df_low_vol)
    z_high = moving_average_gap_zscore(df_high_vol)

    # el % crudo es enormemente distinto -- exactamente el problema que hacía
    # que un par forex pareciera "siempre cerca" y una cripto "siempre lejos"
    assert abs(pct_high) > abs(pct_low) * 50
    # pero normalizado por la dispersión propia de cada serie, quedan
    # prácticamente iguales -- misma forma, solo cambia la amplitud
    assert z_low == pytest.approx(z_high, rel=0.05)
