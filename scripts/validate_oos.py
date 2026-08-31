"""Corre cada activo dos veces: una sobre el período in-sample (70%) y otra sobre
el período out-of-sample (30%, nunca visto), con capital fresco en cada una, y
muestra los resultados lado a lado para ver si el comportamiento se sostiene."""

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.backtest.data_split import split_in_out_sample
from src.backtest.engine import run_backtest
from src.backtest.metrics import summarize
from src.backtest.strategy_baseline import moving_average_crossover
from src.config import RISK_PARAMS

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def run_and_summarize(df):
    result = run_backtest(df, moving_average_crossover, RISK_PARAMS)
    stats = summarize(result.equity_curve["equity"], result.trades)
    stats["halted"] = bool(result.equity_curve["halted"].any())
    return stats


if __name__ == "__main__":
    rows = []
    for csv_path in sorted(RAW_DIR.glob("*.csv")):
        try:
            df = pd.read_csv(csv_path, parse_dates=["timestamp"])
            df_in, df_out = split_in_out_sample(df, out_sample_frac=0.3)

            in_stats = run_and_summarize(df_in)
            out_stats = run_and_summarize(df_out)

            rows.append(
                {
                    "activo": csv_path.stem,
                    "in_desde": df_in["timestamp"].iloc[0].date(),
                    "in_hasta": df_in["timestamp"].iloc[-1].date(),
                    "in_retorno_%": in_stats["retorno_total_%"],
                    "in_dd_$": in_stats["drawdown_maximo_$"],
                    "out_desde": df_out["timestamp"].iloc[0].date(),
                    "out_retorno_%": out_stats["retorno_total_%"],
                    "out_dd_$": out_stats["drawdown_maximo_$"],
                    "out_halted": out_stats["halted"],
                }
            )
        except Exception:
            print(f"ERROR en {csv_path.name}:")
            traceback.print_exc()

    resumen = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(resumen.to_string(index=False))
