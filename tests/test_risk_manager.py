"""Tests de la capa de riesgo determinística. Esto nunca depende del LLM --
ver CONTEXTO.md -- así que es lo primero que tiene que estar cubierto antes
de manejar capital real."""

from src.risk.risk_manager import RiskManager


def make_risk(**overrides):
    params = {"starting_capital": 10_000, "max_drawdown": 2_000, "daily_loss_limit": 200, "stop_loss_per_trade": 25}
    params.update(overrides)
    return RiskManager(**params)


def test_estado_inicial_no_esta_frenado():
    risk = make_risk()
    assert risk.halted is False
    assert risk.peak_equity == 10_000
    assert risk.daily_loss == 0.0


def test_roll_day_resetea_perdida_diaria_en_dia_nuevo():
    risk = make_risk()
    risk.roll_day("2026-09-01")
    risk.daily_loss = 150
    risk.roll_day("2026-09-01")  # mismo día -- no resetea
    assert risk.daily_loss == 150
    risk.roll_day("2026-09-02")  # día nuevo -- resetea
    assert risk.daily_loss == 0.0
    assert risk.current_day == "2026-09-02"


def test_update_peak_solo_sube_nunca_baja():
    risk = make_risk()
    risk.update_peak(11_000)
    assert risk.peak_equity == 11_000
    risk.update_peak(9_000)
    assert risk.peak_equity == 11_000  # no baja aunque el equity actual sea menor


def test_drawdown_breach_no_dispara_por_debajo_del_limite():
    risk = make_risk()
    assert risk.check_drawdown_breach(9_000) is False  # drawdown de 1000, límite 2000
    assert risk.halted is False


def test_drawdown_breach_dispara_solo_una_vez():
    risk = make_risk()
    assert risk.check_drawdown_breach(7_999) is True  # drawdown de 2001 >= 2000
    assert risk.halted is True
    # una segunda ruptura ya no es "evento nuevo" -- el sistema ya está frenado
    assert risk.check_drawdown_breach(5_000) is False


def test_register_trade_pnl_solo_acumula_perdidas():
    risk = make_risk()
    risk.register_trade_pnl(-50, "2026-09-01")
    risk.register_trade_pnl(200, "2026-09-01")  # una ganancia no debe reducir la pérdida acumulada
    risk.register_trade_pnl(-30, "2026-09-01")
    assert risk.daily_loss == 80


def test_register_trade_pnl_rueda_el_dia_automaticamente():
    risk = make_risk()
    risk.register_trade_pnl(-100, "2026-09-01")
    risk.register_trade_pnl(-50, "2026-09-02")
    assert risk.daily_loss == 50  # el día cambió, se resetea antes de sumar la pérdida nueva


def test_can_trade_true_en_estado_normal():
    risk = make_risk()
    can, reason = risk.can_trade()
    assert can is True
    assert reason is None


def test_can_trade_false_si_esta_frenado_por_drawdown():
    risk = make_risk()
    risk.check_drawdown_breach(7_999)
    can, reason = risk.can_trade()
    assert can is False
    assert reason == "drawdown_maximo_alcanzado"


def test_can_trade_false_si_se_alcanzo_el_limite_diario():
    risk = make_risk()
    risk.register_trade_pnl(-200, "2026-09-01")
    can, reason = risk.can_trade()
    assert can is False
    assert reason == "limite_perdida_diaria_alcanzado"


def test_drawdown_tiene_prioridad_sobre_limite_diario_en_el_motivo():
    risk = make_risk()
    risk.register_trade_pnl(-200, "2026-09-01")
    risk.check_drawdown_breach(7_999)
    can, reason = risk.can_trade()
    assert can is False
    assert reason == "drawdown_maximo_alcanzado"
