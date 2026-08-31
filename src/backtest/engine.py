"""Motor de backtesting propio: recorre el historial vela por vela (event-driven).

Los frenos de riesgo (stop-loss por operación y drawdown máximo) se revisan contra
el máximo y mínimo de cada vela (no solo el cierre), para aproximar mejor qué hubiera
pasado intradía. Aun así, con datos diarios queda un margen de imprecisión frente a
datos tick a tick -- se documenta explícitamente, no se oculta.

Simplificación intencional de esta primera versión: una sola posición a la vez.
El tamaño de posición se calcula por riesgo (ver src/risk/position_sizing.py);
la distancia de stop que usa ese cálculo todavía es un valor fijo (STOP_DISTANCE_PCT)
-- se espera que la etapa 4 (LLM) o una mejora basada en volatilidad lo reemplacen.
"""

from dataclasses import dataclass, field

import pandas as pd

from src.backtest.indicators import average_true_range
from src.risk.position_sizing import position_size
from src.risk.risk_manager import RiskManager

ATR_PERIOD = 14
ATR_MULTIPLIER = 2.0  # distancia de stop = ATR_MULTIPLIER x ATR -- estándar de la industria (ej. "Chandelier Exit")
STOP_DISTANCE_PCT_FALLBACK = 0.02  # solo se usa en los primeros días, antes de que haya ATR calculable

# Costos de ejecución por clase de activo. Forex no tiene comisión explícita en la
# mayoría de brokers retail (el costo va en el spread), y el spread de los pares
# mayores es mucho más chico que el fee+slippage típico de un exchange cripto.
# Son aproximaciones -- se recalibran con datos reales del bróker/exchange elegido.
COST_MODEL = {
    "crypto": {"fee_bps": 10, "slippage_bps": 5},
    "forex": {"fee_bps": 0, "slippage_bps": 2},
}


@dataclass
class Trade:
    day: object
    side: str
    price: float
    quantity: float
    pnl: float = 0.0


@dataclass
class BacktestResult:
    equity_curve: pd.DataFrame
    trades: list = field(default_factory=list)


def run_backtest(df: pd.DataFrame, strategy, risk_params: dict, asset_class: str = "crypto") -> BacktestResult:
    """
    df: columnas timestamp, open, high, low, close, volume, ordenado cronológicamente.
    strategy: función (df_hasta_hoy) -> "buy" | "sell" | "hold".
    asset_class: "crypto" | "forex", determina el modelo de costos (ver COST_MODEL).
    """
    fee_bps = COST_MODEL[asset_class]["fee_bps"]
    slippage_bps = COST_MODEL[asset_class]["slippage_bps"]
    atr_series = average_true_range(df, period=ATR_PERIOD)

    cash = risk_params["starting_capital"]
    position_qty = 0.0
    entry_price = None

    risk = RiskManager(
        starting_capital=risk_params["starting_capital"],
        max_drawdown=risk_params["max_drawdown"],
        daily_loss_limit=risk_params["daily_loss_limit"],
        stop_loss_per_trade=risk_params.get("stop_loss_per_trade"),
    )

    equity_rows = []
    trades = []

    for i in range(len(df)):
        row = df.iloc[i]
        day, high, low, close = row["timestamp"], row["high"], row["low"], row["close"]

        risk.roll_day(day)

        best_case_equity = cash + position_qty * high if position_qty > 0 else cash
        risk.update_peak(best_case_equity)

        exited = False

        if position_qty > 0 and risk.stop_loss_per_trade is not None:
            worst_case_pnl = (low - entry_price) * position_qty
            if worst_case_pnl <= -risk.stop_loss_per_trade:
                trigger_price = entry_price - risk.stop_loss_per_trade / position_qty
                exec_price = trigger_price * (1 - slippage_bps / 10_000)
                proceeds = position_qty * exec_price * (1 - fee_bps / 10_000)
                pnl = proceeds - position_qty * entry_price
                cash += proceeds
                trades.append(Trade(day, "stop_loss_exit", exec_price, position_qty, pnl))
                risk.register_trade_pnl(pnl, day)
                position_qty = 0.0
                entry_price = None
                exited = True

        worst_case_equity = cash + position_qty * low if position_qty > 0 else cash
        breached = risk.check_drawdown_breach(worst_case_equity)
        if breached and position_qty > 0:
            exec_price = low * (1 - slippage_bps / 10_000)
            proceeds = position_qty * exec_price * (1 - fee_bps / 10_000)
            pnl = proceeds - position_qty * entry_price
            cash += proceeds
            trades.append(Trade(day, "risk_halt_exit", exec_price, position_qty, pnl))
            risk.register_trade_pnl(pnl, day)
            position_qty = 0.0
            entry_price = None
            exited = True

        can_trade, _ = risk.can_trade()

        if can_trade and not exited:
            signal = strategy(df.iloc[: i + 1])

            if signal == "buy" and position_qty == 0:
                exec_price = close * (1 + slippage_bps / 10_000)
                atr = atr_series.iloc[i]
                stop_distance_pct = (
                    ATR_MULTIPLIER * atr / close if pd.notna(atr) and atr > 0 else STOP_DISTANCE_PCT_FALLBACK
                )
                if risk.stop_loss_per_trade is not None:
                    qty = position_size(cash, risk.stop_loss_per_trade, exec_price, stop_distance_pct)
                else:
                    qty = cash / exec_price
                cost = qty * exec_price * (1 + fee_bps / 10_000)
                if cost > cash:
                    qty = cash / (exec_price * (1 + fee_bps / 10_000))
                    cost = cash
                position_qty = qty
                entry_price = exec_price
                cash -= cost
                trades.append(Trade(day, "buy", exec_price, qty))

            elif signal == "sell" and position_qty > 0:
                exec_price = close * (1 - slippage_bps / 10_000)
                proceeds = position_qty * exec_price * (1 - fee_bps / 10_000)
                pnl = proceeds - position_qty * entry_price
                cash += proceeds
                trades.append(Trade(day, "sell", exec_price, position_qty, pnl))
                risk.register_trade_pnl(pnl, day)
                position_qty = 0.0
                entry_price = None

        equity_close = cash + position_qty * close
        risk.update_peak(equity_close)
        equity_rows.append({"timestamp": day, "equity": equity_close, "halted": risk.halted})

    return BacktestResult(equity_curve=pd.DataFrame(equity_rows), trades=trades)
