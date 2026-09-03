"""Tests de la referencia de shocks -- en particular, que una falla parcial de
fetch en la primera corrida del día (como el 451 de Binance) no deje a un
símbolo sin vigía de shocks por el resto del día entero."""

from datetime import date

import src.execution.shock_watchdog as shock_watchdog


def test_primera_corrida_del_dia_escribe_todo(tmp_path, monkeypatch):
    monkeypatch.setattr(shock_watchdog, "REFERENCE_PATH", tmp_path / "shock_reference.json")

    shock_watchdog.save_shock_reference({"EURUSD": 1.1, "BTC/USDT": 70000.0})
    ref = shock_watchdog.load_shock_reference()

    assert ref["EURUSD"] == 1.1
    assert ref["BTC/USDT"] == 70000.0
    assert ref["_date"] == date.today().isoformat()


def test_corrida_posterior_no_pisa_simbolos_ya_guardados(tmp_path, monkeypatch):
    monkeypatch.setattr(shock_watchdog, "REFERENCE_PATH", tmp_path / "shock_reference.json")

    shock_watchdog.save_shock_reference({"EURUSD": 1.1})
    shock_watchdog.save_shock_reference({"EURUSD": 1.5})
    ref = shock_watchdog.load_shock_reference()

    assert ref["EURUSD"] == 1.1


def test_falla_parcial_en_la_primera_corrida_se_completa_despues(tmp_path, monkeypatch):
    monkeypatch.setattr(shock_watchdog, "REFERENCE_PATH", tmp_path / "shock_reference.json")

    # 1ra corrida del día: Binance devuelve 451, solo forex se guarda.
    shock_watchdog.save_shock_reference({"EURUSD": 1.1})
    # 2da corrida, más tarde el mismo día: Binance ya responde.
    shock_watchdog.save_shock_reference({"EURUSD": 1.2, "BTC/USDT": 70000.0})
    ref = shock_watchdog.load_shock_reference()

    assert ref["EURUSD"] == 1.1  # el precio original del día, no el de la 2da corrida
    assert ref["BTC/USDT"] == 70000.0  # se completó en vez de quedar ausente todo el día


def test_dia_nuevo_reemplaza_la_referencia_entera(tmp_path, monkeypatch):
    monkeypatch.setattr(shock_watchdog, "REFERENCE_PATH", tmp_path / "shock_reference.json")

    shock_watchdog.REFERENCE_PATH.write_text(
        '{"EURUSD": 1.1, "BTC/USDT": 70000.0, "_date": "2000-01-01"}', encoding="utf-8"
    )
    shock_watchdog.save_shock_reference({"EURUSD": 1.3})
    ref = shock_watchdog.load_shock_reference()

    assert ref["EURUSD"] == 1.3
    assert "BTC/USDT" not in ref
    assert ref["_date"] == date.today().isoformat()
