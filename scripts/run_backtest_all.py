"""Corre el motor de backtesting sobre todos los CSV en data/raw/, uno por uno,
para ver si el motor se comporta bien fuera del caso de BTC con el que se validó."""

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.backtest.engine import run_backtest
from src.backtest.metrics import summarize
from src.backtest.strategy_baseline import moving_average_crossover
from src.config import RISK_PARAMS

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

if __name__ == "__main__":
    rows = []
    for csv_path in sorted(RAW_DIR.glob("*.csv")):
        try:
            df = pd.read_csv(csv_path, parse_dates=["timestamp"])
            result = run_backtest(df, moving_average_crossover, RISK_PARAMS)
            stats = summarize(result.equity_curve["equity"], result.trades)
            halted = bool(result.equity_curve["halted"].any())
            rows.append({"activo": csv_path.stem, "halted": halted, **stats})
        except Exception:
            print(f"ERROR en {csv_path.name}:")
            traceback.print_exc()
            rows.append({"activo": csv_path.stem, "halted": "ERROR"})

    resumen = pd.DataFrame(rows)
    pd.set_option("display.width", 160)
    print(resumen.to_string(index=False))
