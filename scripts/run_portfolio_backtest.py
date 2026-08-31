"""Prueba el motor multi-activo con un portafolio mixto (cripto correlacionada +
un activo forex, esperablemente poco correlacionado) para ver si el límite de
correlación bloquea lo que tiene que bloquear."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.backtest.portfolio_engine import run_portfolio_backtest
from src.backtest.strategy_baseline import moving_average_crossover
from src.config import RISK_PARAMS

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

ASSETS = {
    "BTC/USDT": ("data/raw/binance_BTC-USDT_1d.csv", "crypto"),
    "ETH/USDT": ("data/raw/binance_ETH-USDT_1d.csv", "crypto"),
    "LINK/USDT": ("data/raw/binance_LINK-USDT_1d.csv", "crypto"),
    "EURUSD": ("data/raw/forex_EURUSD_1d.csv", "forex"),
}

if __name__ == "__main__":
    asset_dfs = {symbol: pd.read_csv(path, parse_dates=["timestamp"]) for symbol, (path, _) in ASSETS.items()}
    asset_classes = {symbol: cls for symbol, (_, cls) in ASSETS.items()}

    t0 = time.time()
    result = run_portfolio_backtest(asset_dfs, asset_classes, moving_average_crossover, RISK_PARAMS)
    print(f"Corrida en {time.time() - t0:.1f}s\n")

    eq = result.equity_curve
    print(f"Equity final: {eq['equity'].iloc[-1]:.2f}")
    print(f"Drawdown máximo: {(eq['equity'].cummax() - eq['equity']).max():.2f}")
    print(f"Frenado alguna vez: {bool(eq['halted'].any())}")
    print(f"Máximo de posiciones simultáneas: {eq['n_posiciones'].max()}")
    print(f"Total de operaciones: {len(result.trades)}")

    print(f"\nOperaciones bloqueadas por correlación: {len(result.blocked_by_correlation)}")
    for b in result.blocked_by_correlation[:15]:
        print(f"  {b['day'].date()}  {b['symbol']} bloqueado por {b['bloqueado_por']} (correlación {b['correlacion']})")
