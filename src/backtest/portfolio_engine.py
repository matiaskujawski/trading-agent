"""Motor de backtesting multi-activo: simula un portafolio real con varias
posiciones abiertas al mismo tiempo, aplicando el límite de correlación antes
de abrir cada posición nueva. Reutiliza la capa de riesgo y el tamaño de
posición del motor de un solo activo (src/backtest/engine.py).

Los activos no comparten calendario (cripto opera 7 días, forex 5): el día de
referencia es la unión de fechas de todos los activos, y cada uno se evalúa
solo en las fechas donde realmente tiene una vela.
"""

from dataclasses import dataclass, field

import pandas as pd

from src.backtest.engine import COST_MODEL, STOP_DISTANCE_PCT, Trade
from src.risk.correlation import passes_correlation_limit
from src.risk.position_sizing import position_size
from src.risk.risk_manager import RiskManager

CORRELATION_WINDOW = 60
# 0.5 en vez del "0.7 libro de texto": con datos reales (BTC/ETH/LINK/UNI/CAKE/XRP/EURUSD),
# el comportamiento es estable entre 0.3 y 0.6, pero salta brusco justo en 0.7 -- ahí se
# agrupan muchos pares cripto reales, así que ese umbral deja pasar de golpe demasiada
# correlación oculta. Ver commit de esta decisión para el detalle de la comparación.
CORRELATION_THRESHOLD = 0.5
STRATEGY_LOOKBACK = 100  # ventana acotada que se le pasa a la estrategia (más que suficiente para MA 20/50)


@dataclass
class PortfolioBacktestResult:
    equity_curve: pd.DataFrame
    trades: list = field(default_factory=list)
    blocked_by_correlation: list = field(default_factory=list)


def run_portfolio_backtest(
    asset_dfs: dict[str, pd.DataFrame],
    asset_classes: dict[str, str],
    strategy,
    risk_params: dict,
    correlation_window: int = CORRELATION_WINDOW,
    correlation_threshold: float = CORRELATION_THRESHOLD,
) -> PortfolioBacktestResult:
    dfs = {symbol: df.set_index("timestamp").sort_index() for symbol, df in asset_dfs.items()}
    returns = {symbol: df["close"].pct_change() for symbol, df in dfs.items()}
    costs = {symbol: COST_MODEL[asset_classes[symbol]] for symbol in dfs}

    all_dates = sorted(set().union(*[set(df.index) for df in dfs.values()]))

    cash = risk_params["starting_capital"]
    positions: dict[str, dict] = {}  # symbol -> {qty, entry_price, last_known_price}

    risk = RiskManager(
        starting_capital=risk_params["starting_capital"],
        max_drawdown=risk_params["max_drawdown"],
        daily_loss_limit=risk_params["daily_loss_limit"],
        stop_loss_per_trade=risk_params.get("stop_loss_per_trade"),
    )

    equity_rows = []
    trades = []
    blocked = []

    def price_on(symbol, day, column):
        if day in dfs[symbol].index:
            return dfs[symbol].loc[day, column]
        return positions[symbol]["last_known_price"]

    def close_position(symbol, day, exec_price, side):
        pos = positions.pop(symbol)
        fee_bps, slippage_bps = costs[symbol]["fee_bps"], costs[symbol]["slippage_bps"]
        proceeds = pos["qty"] * exec_price * (1 - fee_bps / 10_000)
        pnl = proceeds - pos["qty"] * pos["entry_price"]
        nonlocal cash
        cash += proceeds
        trades.append(Trade(day, f"{side}:{symbol}", exec_price, pos["qty"], pnl))
        risk.register_trade_pnl(pnl, day)

    for day in all_dates:
        risk.roll_day(day)

        best_case = cash + sum(positions[s]["qty"] * price_on(s, day, "high") for s in positions)
        risk.update_peak(best_case)

        # 1) stop-loss por operación, posición por posición
        for symbol in list(positions.keys()):
            if day not in dfs[symbol].index or risk.stop_loss_per_trade is None:
                continue
            pos, low = positions[symbol], dfs[symbol].loc[day, "low"]
            worst_case_pnl = (low - pos["entry_price"]) * pos["qty"]
            if worst_case_pnl <= -risk.stop_loss_per_trade:
                trigger_price = pos["entry_price"] - risk.stop_loss_per_trade / pos["qty"]
                slippage_bps = costs[symbol]["slippage_bps"]
                exec_price = trigger_price * (1 - slippage_bps / 10_000)
                close_position(symbol, day, exec_price, "stop_loss_exit")

        # 2) freno de portafolio (drawdown máximo) -- si se toca, se liquida TODO
        worst_case = cash + sum(positions[s]["qty"] * price_on(s, day, "low") for s in positions)
        if risk.check_drawdown_breach(worst_case):
            for symbol in list(positions.keys()):
                low = price_on(symbol, day, "low")
                slippage_bps = costs[symbol]["slippage_bps"]
                exec_price = low * (1 - slippage_bps / 10_000)
                close_position(symbol, day, exec_price, "risk_halt_exit")

        # 3) señales de estrategia, activo por activo
        can_trade, _ = risk.can_trade()
        if can_trade:
            for symbol, df_idx in dfs.items():
                if day not in df_idx.index:
                    continue
                pos_idx = df_idx.index.get_loc(day)
                if pos_idx < 50:
                    continue

                if symbol in positions:
                    window = df_idx.iloc[max(0, pos_idx - STRATEGY_LOOKBACK) : pos_idx + 1].reset_index()
                    if strategy(window) == "sell":
                        close_price = df_idx.loc[day, "close"]
                        slippage_bps = costs[symbol]["slippage_bps"]
                        exec_price = close_price * (1 - slippage_bps / 10_000)
                        close_position(symbol, day, exec_price, "sell")
                    continue

                window = df_idx.iloc[max(0, pos_idx - STRATEGY_LOOKBACK) : pos_idx + 1].reset_index()
                if strategy(window) != "buy" or cash <= 0:
                    continue

                start = max(0, pos_idx - correlation_window + 1)
                candidate_returns = returns[symbol].iloc[start : pos_idx + 1]
                open_returns = {
                    s: returns[s].iloc[max(0, dfs[s].index.get_loc(day) - correlation_window + 1) : dfs[s].index.get_loc(day) + 1]
                    for s in positions
                    if day in dfs[s].index
                }
                ok, corr, blocker = passes_correlation_limit(candidate_returns, open_returns, correlation_threshold)
                if not ok:
                    blocked.append({"day": day, "symbol": symbol, "correlacion": round(corr, 2), "bloqueado_por": blocker})
                    continue

                close_price = df_idx.loc[day, "close"]
                fee_bps, slippage_bps = costs[symbol]["fee_bps"], costs[symbol]["slippage_bps"]
                exec_price = close_price * (1 + slippage_bps / 10_000)

                if risk.stop_loss_per_trade is not None:
                    qty = position_size(cash, risk.stop_loss_per_trade, exec_price, STOP_DISTANCE_PCT)
                else:
                    qty = cash / exec_price
                cost = qty * exec_price * (1 + fee_bps / 10_000)
                if cost > cash:
                    qty, cost = cash / (exec_price * (1 + fee_bps / 10_000)), cash
                if qty <= 0:
                    continue

                positions[symbol] = {"qty": qty, "entry_price": exec_price, "last_known_price": exec_price}
                cash -= cost
                trades.append(Trade(day, f"buy:{symbol}", exec_price, qty))

        for symbol in positions:
            if day in dfs[symbol].index:
                positions[symbol]["last_known_price"] = dfs[symbol].loc[day, "close"]

        equity_close = cash + sum(p["qty"] * p["last_known_price"] for p in positions.values())
        risk.update_peak(equity_close)
        equity_rows.append(
            {"timestamp": day, "equity": equity_close, "halted": risk.halted, "n_posiciones": len(positions)}
        )

    return PortfolioBacktestResult(
        equity_curve=pd.DataFrame(equity_rows), trades=trades, blocked_by_correlation=blocked
    )
