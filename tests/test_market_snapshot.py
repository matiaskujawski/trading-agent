"""Tests del guardado/lectura de la foto del universo en vivo."""

import src.execution.market_snapshot as market_snapshot


def test_save_y_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(market_snapshot, "MARKET_SNAPSHOT_PATH", tmp_path / "market_snapshot.json")

    assets = {
        "BTC/USDT": {"asset_class": "crypto", "price": 65000.0, "gap_pct": 1.23, "has_position": False},
        "EURUSD": {"asset_class": "forex", "price": 1.08, "gap_pct": None, "has_position": True},
    }
    market_snapshot.save_market_snapshot(assets)
    loaded = market_snapshot.load_market_snapshot()

    assert loaded["assets"] == assets
    assert loaded["updated_at"] is not None


def test_load_sin_archivo_devuelve_vacio(tmp_path, monkeypatch):
    monkeypatch.setattr(market_snapshot, "MARKET_SNAPSHOT_PATH", tmp_path / "no_existe.json")
    loaded = market_snapshot.load_market_snapshot()
    assert loaded == {"updated_at": None, "assets": {}}
