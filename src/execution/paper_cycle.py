"""Ciclo diario de paper trading: busca precios frescos, revisa los frenos de
riesgo (stop-loss y drawdown máximo) contra el mercado actual, evalúa gatillos
técnicos y consulta al LLM (o al mock) SOLO cuando hay un gatillo, aplica el
límite de correlación, y simula la ejecución. No usa plata real -- todo el
estado vive en paper_trading/, fuera de git."""

from datetime import date, timedelta

import pandas as pd

from src.backtest.engine import ATR_MULTIPLIER, ATR_PERIOD, COST_MODEL, STOP_DISTANCE_PCT_FALLBACK
from src.backtest.indicators import average_true_range
from src.backtest.portfolio_engine import CORRELATION_THRESHOLD, CORRELATION_WINDOW
from src.backtest.strategy_baseline import moving_average_crossover
from src.config import CRYPTO_SYMBOLS, FOREX_PAIRS, RISK_PARAMS
from src.data_pipeline.crypto import fetch_ohlcv
from src.data_pipeline.forex import fetch_forex
from src.data_pipeline.sentiment import build_sentiment_context
from src.execution.paper_state import load_state, save_state
from src.execution.trade_log import log_daily_equity, log_trade
from src.llm_decision.market_summary import build_market_summary
from src.llm_decision.mock_decision import mock_decision
from src.risk.correlation import passes_correlation_limit
from src.risk.position_sizing import position_size
from src.risk.risk_manager import RiskManager

LOOKBACK_DAYS = 150

TRIGGER_REASONS = {"buy": "cruce_alcista_medias_moviles", "sell": "cruce_bajista_medias_moviles"}


def _fetch_recent(symbol: str, asset_class: str) -> pd.DataFrame:
    since = (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()
    if asset_class == "crypto":
        return fetch_ohlcv(symbol, since=since)
    return fetch_forex(symbol, start=since)


def run_daily_cycle(decision_fn=mock_decision, dry_run: bool = False) -> dict:
    """Devuelve un resumen del ciclo (usado por el reporte diario). Con
    dry_run=True no guarda estado ni log -- para probar sin ensuciar el
    historial real."""
    state = load_state(RISK_PARAMS["starting_capital"])
    today = date.today().isoformat()

    risk = RiskManager(
        starting_capital=RISK_PARAMS["starting_capital"],
        max_drawdown=RISK_PARAMS["max_drawdown"],
        daily_loss_limit=RISK_PARAMS["daily_loss_limit"],
        stop_loss_per_trade=RISK_PARAMS["stop_loss_per_trade"],
    )
    risk.peak_equity = state["peak_equity"]
    risk.daily_loss = state["daily_loss"]
    risk.current_day = state["current_day"]
    risk.halted = state["halted"]
    risk.roll_day(today)

    cash = state["cash"]
    positions = state["positions"]

    assets = {s: "crypto" for s in CRYPTO_SYMBOLS} | {s: "forex" for s in FOREX_PAIRS}
    dfs, fetch_errors = {}, []
    for symbol, asset_class in assets.items():
        try:
            dfs[symbol] = _fetch_recent(symbol, asset_class)
        except Exception as e:
            fetch_errors.append(f"{symbol}: {e}")

    sentiment_context = build_sentiment_context()
    events = list(fetch_errors)

    # 1) stop-loss por operación, posición por posición
    for symbol in list(positions.keys()):
        if symbol not in dfs or risk.stop_loss_per_trade is None:
            continue
        pos, low = positions[symbol], dfs[symbol]["low"].iloc[-1]
        worst_case_pnl = (low - pos["entry_price"]) * pos["qty"]
        if worst_case_pnl <= -risk.stop_loss_per_trade:
            fee_bps, slippage_bps = COST_MODEL[assets[symbol]]["fee_bps"], COST_MODEL[assets[symbol]]["slippage_bps"]
            trigger_price = pos["entry_price"] - risk.stop_loss_per_trade / pos["qty"]
            exec_price = trigger_price * (1 - slippage_bps / 10_000)
            proceeds = pos["qty"] * exec_price * (1 - fee_bps / 10_000)
            pnl = proceeds - pos["qty"] * pos["entry_price"]
            cash += proceeds
            risk.register_trade_pnl(pnl, today)
            log_trade({"day": today, "symbol": symbol, "side": "stop_loss_exit", "price": exec_price, "qty": pos["qty"], "pnl": pnl})
            events.append(f"STOP-LOSS: se cerró {symbol} con pérdida de ${-pnl:.2f}")
            del positions[symbol]

    # 2) freno de portafolio (drawdown máximo) -- si se toca, se liquida todo
    worst_case_equity = cash + sum(positions[s]["qty"] * dfs[s]["low"].iloc[-1] for s in positions if s in dfs)
    if risk.check_drawdown_breach(worst_case_equity):
        for symbol in list(positions.keys()):
            if symbol not in dfs:
                continue
            pos = positions[symbol]
            fee_bps, slippage_bps = COST_MODEL[assets[symbol]]["fee_bps"], COST_MODEL[assets[symbol]]["slippage_bps"]
            exec_price = dfs[symbol]["low"].iloc[-1] * (1 - slippage_bps / 10_000)
            proceeds = pos["qty"] * exec_price * (1 - fee_bps / 10_000)
            pnl = proceeds - pos["qty"] * pos["entry_price"]
            cash += proceeds
            risk.register_trade_pnl(pnl, today)
            log_trade({"day": today, "symbol": symbol, "side": "risk_halt_exit", "price": exec_price, "qty": pos["qty"], "pnl": pnl})
            events.append(f"FRENO DE RIESGO: drawdown máximo alcanzado, se liquidó todo. {symbol}: ${pnl:.2f}")
            del positions[symbol]

    # 3) gatillos técnicos -> LLM -> correlación -> ejecución
    can_trade, block_reason = risk.can_trade()
    if can_trade:
        for symbol, df in dfs.items():
            if len(df) < 51:
                continue
            signal = moving_average_crossover(df)
            if signal not in TRIGGER_REASONS:
                continue

            asset_class = assets[symbol]
            has_position = symbol in positions
            if (signal == "buy" and has_position) or (signal == "sell" and not has_position):
                continue

            risk_state = {
                "daily_loss_used_pct": round(risk.daily_loss / risk.daily_loss_limit, 2),
                "distance_to_max_drawdown_pct": round(1 - (risk.peak_equity - worst_case_equity) / risk.max_drawdown, 2),
                "max_position_size_usd": risk.stop_loss_per_trade,
            }
            context = sentiment_context if asset_class == "crypto" else None
            summary = build_market_summary(df, symbol, TRIGGER_REASONS[signal], risk_state, context)
            decision = decision_fn(summary)
            events.append(
                f"GATILLO {symbol} ({TRIGGER_REASONS[signal]}) -> LLM: {decision['action']} "
                f"(confianza {decision['confidence']}, motivo: {decision['reasoning']})"
            )

            price = df["close"].iloc[-1]
            fee_bps, slippage_bps = COST_MODEL[asset_class]["fee_bps"], COST_MODEL[asset_class]["slippage_bps"]

            if decision["action"] == "sell" and has_position:
                pos = positions[symbol]
                exec_price = price * (1 - slippage_bps / 10_000)
                proceeds = pos["qty"] * exec_price * (1 - fee_bps / 10_000)
                pnl = proceeds - pos["qty"] * pos["entry_price"]
                cash += proceeds
                risk.register_trade_pnl(pnl, today)
                log_trade({"day": today, "symbol": symbol, "side": "sell", "price": exec_price, "qty": pos["qty"], "pnl": pnl})
                events.append(f"VENTA {symbol}: resultado ${pnl:.2f}")
                del positions[symbol]

            elif decision["action"] == "buy" and not has_position and cash > 0:
                candidate_returns = df["close"].pct_change().iloc[-CORRELATION_WINDOW:]
                open_returns = {s: dfs[s]["close"].pct_change().iloc[-CORRELATION_WINDOW:] for s in positions if s in dfs}
                ok, corr, blocker = passes_correlation_limit(candidate_returns, open_returns, CORRELATION_THRESHOLD)
                if not ok:
                    events.append(f"BLOQUEADO por correlación: {symbol} vs {blocker} ({corr:.2f})")
                    continue

                atr = average_true_range(df, period=ATR_PERIOD).iloc[-1]
                stop_distance_pct = ATR_MULTIPLIER * atr / price if pd.notna(atr) and atr > 0 else STOP_DISTANCE_PCT_FALLBACK
                exec_price = price * (1 + slippage_bps / 10_000)
                max_qty = position_size(cash, risk.stop_loss_per_trade, exec_price, stop_distance_pct)
                qty = max_qty * decision["suggested_size_fraction"]
                cost = qty * exec_price * (1 + fee_bps / 10_000)
                if cost > cash:
                    qty, cost = cash / (exec_price * (1 + fee_bps / 10_000)), cash
                if qty > 0:
                    positions[symbol] = {"qty": qty, "entry_price": exec_price, "opened_at": today}
                    cash -= cost
                    log_trade({"day": today, "symbol": symbol, "side": "buy", "price": exec_price, "qty": qty})
                    events.append(f"COMPRA {symbol}: {qty:.6f} unidades a ${exec_price:.2f}")
    else:
        events.append(f"Sin operaciones nuevas hoy: {block_reason}")

    equity = cash + sum(positions[s]["qty"] * dfs[s]["close"].iloc[-1] for s in positions if s in dfs)
    risk.update_peak(equity)

    state.update(
        {
            "cash": cash,
            "positions": positions,
            "peak_equity": risk.peak_equity,
            "daily_loss": risk.daily_loss,
            "current_day": today,
            "halted": risk.halted,
        }
    )

    if not dry_run:
        save_state(state)
        log_daily_equity({"day": today, "equity": equity, "cash": cash, "n_posiciones": len(positions), "halted": risk.halted})

    return {"day": today, "equity": equity, "state": state, "events": events, "sentiment_context": sentiment_context}
