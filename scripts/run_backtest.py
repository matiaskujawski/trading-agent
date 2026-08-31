"""Corre el motor de backtesting propio sobre un CSV de data/raw/ usando la estrategia
de referencia (cruce de medias móviles). Sirve para validar el motor antes de conectar el LLM.

Uso: venv/Scripts/python.exe scripts/run_backtest.py data/raw/binance_BTC-USDT_1d.csv
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.backtest.engine import run_backtest
from src.backtest.metrics import summarize
from src.backtest.strategy_baseline import moving_average_crossover
from src.config import RISK_PARAMS

if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/binance_BTC-USDT_1d.csv"
    df = pd.read_csv(csv_path, parse_dates=["timestamp"])

    if RISK_PARAMS["stop_loss_per_trade"] is None:
        print("ATENCION: stop_loss_per_trade sigue sin confirmar -- este backtest corre sin ese freno.\n")

    result = run_backtest(df, moving_average_crossover, RISK_PARAMS)
    stats = summarize(result.equity_curve["equity"], result.trades)

    print(f"Resultados para {csv_path}:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    halts = result.equity_curve[result.equity_curve["halted"]]
    if not halts.empty:
        print(f"  ATENCION: el sistema se frenó por drawdown máximo el {halts.iloc[0]['timestamp']}")
