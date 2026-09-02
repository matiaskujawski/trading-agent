"""Corre varias estrategias candidatas sobre los 11 activos y compara
resultados lado a lado -- para decidir con datos, no a ojo, si alguna suma
señales de verdad sin arruinar la calidad."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.backtest.engine import run_backtest
from src.backtest.metrics import summarize
from src.backtest.strategy_baseline import moving_average_crossover
from src.backtest.strategy_bollinger import bollinger_bounce
from src.backtest.strategy_rsi import rsi_reversion
from src.config import RISK_PARAMS

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

STRATEGIES = {
    "cruce_medias (actual)": moving_average_crossover,
    "rsi_reversion": rsi_reversion,
    "bollinger_bounce": bollinger_bounce,
}

if __name__ == "__main__":
    rows = []
    for csv_path in sorted(RAW_DIR.glob("*.csv")):
        asset_class = "forex" if csv_path.stem.startswith("forex_") else "crypto"
        df = pd.read_csv(csv_path, parse_dates=["timestamp"])

        for strategy_name, strategy_fn in STRATEGIES.items():
            result = run_backtest(df, strategy_fn, RISK_PARAMS, asset_class=asset_class)
            stats = summarize(result.equity_curve["equity"], result.trades)
            halted = bool(result.equity_curve["halted"].any())
            rows.append({"activo": csv_path.stem, "estrategia": strategy_name, "halted": halted, **stats})

    resumen = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(resumen.to_string(index=False))

    print("\n--- promedio por estrategia (todos los activos) ---")
    avg = resumen.groupby("estrategia")[
        ["retorno_total_%", "drawdown_maximo_$", "sharpe_ratio", "num_operaciones", "tasa_de_acierto_%"]
    ].mean()
    print(avg.to_string())
