"""Tests del registro de salud de las fuentes de datos -- la protección
agregada después de que Binance devolviera error 451 durante más de 21 horas
sin que nada lo marcara, porque el ciclo seguía terminando "exitoso"."""

from datetime import datetime, timedelta, timezone

import src.execution.fetch_health as fetch_health


def test_record_y_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_health, "FETCH_HEALTH_PATH", tmp_path / "fetch_health.json")

    fetch_health.record_fetch_results({"BTC/USDT": None, "EURUSD": "timeout"})
    health = fetch_health.load_fetch_health()

    assert health["BTC/USDT"]["last_error"] is None
    assert health["BTC/USDT"]["consecutive_failures"] == 0
    assert health["EURUSD"]["last_error"] == "timeout"
    assert health["EURUSD"]["consecutive_failures"] == 1


def test_fallas_consecutivas_se_acumulan(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_health, "FETCH_HEALTH_PATH", tmp_path / "fetch_health.json")

    fetch_health.record_fetch_results({"BTC/USDT": "error 451"})
    fetch_health.record_fetch_results({"BTC/USDT": "error 451"})
    fetch_health.record_fetch_results({"BTC/USDT": "error 451"})
    health = fetch_health.load_fetch_health()

    assert health["BTC/USDT"]["consecutive_failures"] == 3


def test_un_exito_resetea_el_contador_de_fallas(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_health, "FETCH_HEALTH_PATH", tmp_path / "fetch_health.json")

    fetch_health.record_fetch_results({"BTC/USDT": "error 451"})
    fetch_health.record_fetch_results({"BTC/USDT": "error 451"})
    fetch_health.record_fetch_results({"BTC/USDT": None})
    health = fetch_health.load_fetch_health()

    assert health["BTC/USDT"]["consecutive_failures"] == 0
    assert health["BTC/USDT"]["last_error"] is None


def test_stale_symbols_vacio_si_todo_tuvo_exito_reciente(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_health, "FETCH_HEALTH_PATH", tmp_path / "fetch_health.json")

    fetch_health.record_fetch_results({"BTC/USDT": None})
    assert fetch_health.stale_symbols() == []


def test_stale_symbols_detecta_simbolo_sin_ningun_exito():
    health = {"BTC/USDT": {"last_success": None, "last_error": "451 restricted", "consecutive_failures": 5}}
    stale = fetch_health.stale_symbols(health)
    assert len(stale) == 1
    assert stale[0]["symbol"] == "BTC/USDT"
    assert stale[0]["hours_since_success"] is None


def test_stale_symbols_detecta_ultimo_exito_viejo():
    old_success = (datetime.now(timezone.utc) - timedelta(hours=fetch_health.STALE_HOURS + 1)).isoformat(timespec="seconds")
    health = {"BTC/USDT": {"last_success": old_success, "last_error": "451 restricted", "consecutive_failures": 4}}
    stale = fetch_health.stale_symbols(health)
    assert len(stale) == 1
    assert stale[0]["hours_since_success"] > fetch_health.STALE_HOURS


def test_stale_symbols_no_marca_exito_reciente():
    recent_success = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(timespec="seconds")
    health = {"BTC/USDT": {"last_success": recent_success, "last_error": None, "consecutive_failures": 0}}
    assert fetch_health.stale_symbols(health) == []
