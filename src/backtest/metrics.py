"""Métricas de evaluación de un backtest."""

import numpy as np
import pandas as pd


def max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    return (peak - equity).max()


def sharpe_ratio(equity: pd.Series, periods_per_year: int = 365) -> float:
    returns = equity.pct_change().dropna()
    if returns.std() == 0:
        return 0.0
    return float((returns.mean() / returns.std()) * np.sqrt(periods_per_year))


def total_return_pct(equity: pd.Series) -> float:
    return float((equity.iloc[-1] / equity.iloc[0]) - 1) * 100


def summarize(equity: pd.Series, trades: list) -> dict:
    closed = [t for t in trades if t.side in ("sell", "stop_loss_exit", "risk_halt_exit")]
    wins = [t for t in closed if t.pnl > 0]
    return {
        "retorno_total_%": round(total_return_pct(equity), 2),
        "drawdown_maximo_$": round(max_drawdown(equity), 2),
        "sharpe_ratio": round(sharpe_ratio(equity), 2),
        "num_operaciones": len(closed),
        "tasa_de_acierto_%": round(100 * len(wins) / len(closed), 2) if closed else 0.0,
        "equity_final_$": round(equity.iloc[-1], 2),
    }
