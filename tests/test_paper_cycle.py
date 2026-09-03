"""El freno de riesgo por drawdown máximo tiene que reintentar liquidar
posiciones remanentes en cada ciclo mientras siga frenado, no solo en el
ciclo donde detecta la ruptura por primera vez -- ver el comentario en
paper_cycle.py sobre por qué check_drawdown_breach() no alcanza como gatillo
por sí solo."""

import pandas as pd
import pytest

import src.execution.paper_cycle as paper_cycle


def make_df(low, close, rows=5):
    return pd.DataFrame({"open": [close] * rows, "high": [close] * rows, "low": [low] * rows, "close": [close] * rows})


@pytest.fixture
def stub_environment(monkeypatch):
    """Universo de dos símbolos, sin tocar red ni el estado real en disco."""
    monkeypatch.setattr(paper_cycle, "CRYPTO_SYMBOLS", ["A", "B"])
    monkeypatch.setattr(paper_cycle, "FOREX_PAIRS", [])
    monkeypatch.setattr(paper_cycle, "build_sentiment_context", lambda: {})
    monkeypatch.setattr(paper_cycle, "record_fetch_results", lambda *a, **k: None)
    monkeypatch.setattr(paper_cycle, "save_market_snapshot", lambda *a, **k: None)
    monkeypatch.setattr(paper_cycle, "save_shock_reference", lambda *a, **k: None)
    monkeypatch.setattr(paper_cycle, "log_trade", lambda *a, **k: None)
    monkeypatch.setattr(paper_cycle, "log_daily_equity", lambda *a, **k: None)

    store = {
        "state": {
            "starting_capital": 10_000,
            "cash": 0,
            # peak_equity absurdamente alto para que el drawdown quede
            # rotundamente por encima del límite en ambos ciclos, sin
            # depender de la aritmética exacta de comisiones/slippage.
            "peak_equity": 1_000_000,
            "daily_loss": 0.0,
            "current_day": "2026-09-01",
            "halted": False,
            "positions": {
                "A": {"qty": 10, "entry_price": 50, "opened_at": "2026-09-01"},
                "B": {"qty": 100, "entry_price": 50, "opened_at": "2026-09-01"},
            },
        }
    }
    monkeypatch.setattr(paper_cycle, "load_state", lambda starting_capital: store["state"])
    monkeypatch.setattr(paper_cycle, "save_state", lambda state: store.__setitem__("state", state))
    return store


def test_freno_por_drawdown_liquida_posicion_cuyo_fetch_fallo_en_ciclos_posteriores(monkeypatch, stub_environment):
    store = stub_environment
    cycle = {"n": 0}

    def fake_fetch_recent(symbol, asset_class):
        cycle_n = cycle["n"]
        if symbol == "A":
            if cycle_n == 1:
                raise RuntimeError("rate limited")
            return make_df(low=49, close=49)  # cerca de su entry (50) -- no dispara su propio stop-loss ($25)
        # B se desploma: dispara tanto su stop-loss por operación como, de
        # todos modos, el freno de portafolio quedaría activo por el peak_equity.
        return make_df(low=20, close=20)

    monkeypatch.setattr(paper_cycle, "_fetch_recent", fake_fetch_recent)

    cycle["n"] = 1
    result1 = paper_cycle.run_daily_cycle(decision_fn=lambda *_: pytest.fail("no debería consultarse al LLM"))
    assert result1["state"]["halted"] is True
    # A no tenía precio fresco este ciclo -- sigue abierta a pesar del freno.
    assert "A" in result1["state"]["positions"]

    cycle["n"] = 2
    result2 = paper_cycle.run_daily_cycle(decision_fn=lambda *_: pytest.fail("no debería consultarse al LLM"))
    # Ahora que el fetch de A funciona, el freno (todavía activo) tiene
    # que terminar de liquidarla en vez de dejarla abierta para siempre.
    assert result2["state"]["positions"] == {}
    assert store["state"]["positions"] == {}
