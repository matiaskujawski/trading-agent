"""Tests de sizing basado en riesgo: nunca debería poder arriesgar más del
stop-loss por operación, ni comprar más de lo que el capital permite."""

from src.risk.position_sizing import position_size


def test_sizing_normal_limitado_por_riesgo():
    # stop de $25, precio $100, stop_distance 2% ($2) -> qty = 25 / 2 = 12.5
    qty = position_size(capital=100_000, stop_loss_dollar=25, entry_price=100, stop_distance_pct=0.02)
    assert qty == 12.5


def test_sizing_limitado_por_capital_disponible():
    # con poco capital, el límite real es cuánto se puede comprar, no el riesgo
    qty = position_size(capital=50, stop_loss_dollar=25, entry_price=100, stop_distance_pct=0.02)
    assert qty == 0.5  # 50 / 100


def test_stop_distance_cero_devuelve_cero():
    assert position_size(capital=10_000, stop_loss_dollar=25, entry_price=100, stop_distance_pct=0.0) == 0.0


def test_stop_distance_negativo_devuelve_cero():
    assert position_size(capital=10_000, stop_loss_dollar=25, entry_price=100, stop_distance_pct=-0.01) == 0.0


def test_capital_cero_devuelve_cero():
    assert position_size(capital=0, stop_loss_dollar=25, entry_price=100, stop_distance_pct=0.02) == 0.0


def test_nunca_supera_lo_que_el_capital_permite_aunque_el_riesgo_lo_autorice():
    # stop grande, activo caro, poco capital: el límite de capital manda
    qty = position_size(capital=1_000, stop_loss_dollar=500, entry_price=10_000, stop_distance_pct=0.01)
    qty_by_capital = 1_000 / 10_000
    assert qty == qty_by_capital
