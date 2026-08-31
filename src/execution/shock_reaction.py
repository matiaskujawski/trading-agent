"""Qué pasa cuando el vigía de volatilidad (shock_watchdog.py) encuentra algo:
revisión de riesgo inmediata y determinística, una consulta acotada al LLM
solo para el activo en cuestión, y un aviso al usuario. Se invoca solo
cuando check_shocks() devuelve algo -- la inmensa mayoría de las veces esto
nunca corre."""

from datetime import date, timedelta

import pandas as pd

from src.backtest.engine import ATR_MULTIPLIER, ATR_PERIOD, COST_MODEL, STOP_DISTANCE_PCT_FALLBACK
from src.backtest.indicators import average_true_range
from src.backtest.portfolio_engine import CORRELATION_THRESHOLD, CORRELATION_WINDOW
from src.config import RISK_PARAMS
from src.data_pipeline.crypto import fetch_ohlcv
from src.data_pipeline.forex import fetch_forex
from src.data_pipeline.sentiment import build_sentiment_context
from src.execution.paper_state import load_state, save_state
from src.execution.trade_log import log_trade
from src.llm_decision.claude_decision import claude_decision
from src.llm_decision.market_summary import build_market_summary
from src.risk.correlation import passes_correlation_limit
from src.risk.position_sizing import position_size
from src.risk.risk_manager import RiskManager

LOOKBACK_DAYS = 150

# Durante un shock, los rellenos reales suelen ser peores que en mercado
# tranquilo (ver el caso XRP: gap risk, poca liquidez momentánea). Usar el
# mismo slippage "de todos los días" acá sería optimista justo en el peor
# momento para serlo -- se multiplica, no se ignora.
SHOCK_SLIPPAGE_MULTIPLIER = 3.0


def _recent_window_with_live_price(symbol: str, asset_class: str, current_price: float) -> pd.DataFrame:
    """Historial real reciente (para que las medias móviles y la volatilidad
    tengan sentido) más una fila final con el precio en vivo del shock."""
    since = (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()
    df = fetch_ohlcv(symbol, since=since) if asset_class == "crypto" else fetch_forex(symbol, start=since)
    live_row = pd.DataFrame(
        [{"timestamp": pd.Timestamp.now(), "open": current_price, "high": current_price, "low": current_price, "close": current_price, "volume": 0}]
    )
    return pd.concat([df, live_row], ignore_index=True)


def _asset_class_of(symbol: str) -> str:
    from src.config import CRYPTO_SYMBOLS

    return "crypto" if symbol in CRYPTO_SYMBOLS else "forex"


def react_to_shock(shock: dict, dry_run: bool = False) -> dict:
    symbol, asset_class = shock["symbol"], shock["asset_class"]
    current_price = shock["current_price"]
    today = date.today().isoformat()
    events = [f"SHOCK: {symbol} se movió {shock['pct_change']}% desde el cierre de referencia ({shock['direction']})"]

    state = load_state(RISK_PARAMS["starting_capital"])
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

    def mark_to_market(exclude_symbol_price=current_price):
        return cash + sum(
            positions[s]["qty"] * (current_price if s == symbol else positions[s].get("last_known_price", positions[s]["entry_price"]))
            for s in positions
        )

    # 1) stop-loss por operación, con el precio EN VIVO (no el de ayer)
    if symbol in positions and risk.stop_loss_per_trade is not None:
        pos = positions[symbol]
        unrealized_pnl = (current_price - pos["entry_price"]) * pos["qty"]
        if unrealized_pnl <= -risk.stop_loss_per_trade:
            fee_bps = COST_MODEL[asset_class]["fee_bps"]
            slippage_bps = COST_MODEL[asset_class]["slippage_bps"] * SHOCK_SLIPPAGE_MULTIPLIER
            exec_price = current_price * (1 - slippage_bps / 10_000)
            proceeds = pos["qty"] * exec_price * (1 - fee_bps / 10_000)
            pnl = proceeds - pos["qty"] * pos["entry_price"]
            cash += proceeds
            risk.register_trade_pnl(pnl, today)
            if not dry_run:
                log_trade({"day": today, "symbol": symbol, "side": "stop_loss_exit_reactivo", "price": exec_price, "qty": pos["qty"], "pnl": pnl})
            events.append(f"STOP-LOSS REACTIVO: se cerró {symbol} con pérdida de ${-pnl:.2f}")
            del positions[symbol]

    # 2) freno de portafolio (drawdown máximo), con el resto del portafolio a
    # su último precio conocido -- si algún otro activo también se movió
    # fuerte, check_shocks() ya lo habría detectado por separado.
    risk.update_peak(mark_to_market())
    if risk.check_drawdown_breach(mark_to_market()):
        for s in list(positions.keys()):
            pos = positions[s]
            s_class = asset_class if s == symbol else _asset_class_of(s)
            mark_price = current_price if s == symbol else pos.get("last_known_price", pos["entry_price"])
            fee_bps = COST_MODEL[s_class]["fee_bps"]
            slippage_bps = COST_MODEL[s_class]["slippage_bps"] * SHOCK_SLIPPAGE_MULTIPLIER
            exec_price = mark_price * (1 - slippage_bps / 10_000)
            proceeds = pos["qty"] * exec_price * (1 - fee_bps / 10_000)
            pnl = proceeds - pos["qty"] * pos["entry_price"]
            cash += proceeds
            risk.register_trade_pnl(pnl, today)
            if not dry_run:
                log_trade({"day": today, "symbol": s, "side": "risk_halt_exit_reactivo", "price": exec_price, "qty": pos["qty"], "pnl": pnl})
            events.append(f"FRENO DE RIESGO REACTIVO: drawdown máximo alcanzado, se liquidó todo. {s}: ${pnl:.2f}")
            del positions[s]

    # 3) consulta acotada al LLM, solo para el activo del shock -- nunca para
    # todo el universo. Se hace incluso si el paso 1/2 ya cerró la posición,
    # porque puede ser una oportunidad de entrada, no solo un riesgo a cortar.
    can_trade, block_reason = risk.can_trade()
    if can_trade:
        risk_state = {
            "daily_loss_used_pct": round(risk.daily_loss / risk.daily_loss_limit, 2),
            "distance_to_max_drawdown_pct": round(1 - (risk.peak_equity - mark_to_market()) / risk.max_drawdown, 2),
            "max_position_size_usd": risk.stop_loss_per_trade,
        }
        context = build_sentiment_context() if asset_class == "crypto" else None
        window = _recent_window_with_live_price(symbol, asset_class, current_price)
        summary = build_market_summary(window, symbol, "shock_de_volatilidad", risk_state, context)
        summary["shock_pct_change"] = shock["pct_change"]

        decision = claude_decision(summary)
        events.append(f"LECTURA DEL LLM sobre el shock: {decision['action']} (confianza {decision['confidence']}) -- {decision['reasoning']}")

        fee_bps = COST_MODEL[asset_class]["fee_bps"]
        slippage_bps = COST_MODEL[asset_class]["slippage_bps"] * SHOCK_SLIPPAGE_MULTIPLIER

        if decision["action"] == "sell" and symbol in positions:
            pos = positions[symbol]
            exec_price = current_price * (1 - slippage_bps / 10_000)
            proceeds = pos["qty"] * exec_price * (1 - fee_bps / 10_000)
            pnl = proceeds - pos["qty"] * pos["entry_price"]
            cash += proceeds
            risk.register_trade_pnl(pnl, today)
            if not dry_run:
                log_trade({"day": today, "symbol": symbol, "side": "sell_reactivo", "price": exec_price, "qty": pos["qty"], "pnl": pnl})
            events.append(f"VENTA REACTIVA {symbol}: resultado ${pnl:.2f}")
            del positions[symbol]

        elif decision["action"] == "buy" and symbol not in positions and cash > 0:
            candidate_returns = window["close"].pct_change().iloc[-CORRELATION_WINDOW:]
            open_returns = {}
            for s in positions:
                s_since = (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()
                s_class = _asset_class_of(s)
                s_df = fetch_ohlcv(s, since=s_since) if s_class == "crypto" else fetch_forex(s, start=s_since)
                open_returns[s] = s_df["close"].pct_change().iloc[-CORRELATION_WINDOW:]

            ok, corr, blocker = passes_correlation_limit(candidate_returns, open_returns, CORRELATION_THRESHOLD)
            if not ok:
                events.append(f"COMPRA REACTIVA BLOQUEADA por correlación: {symbol} vs {blocker} ({corr:.2f})")
            else:
                atr = average_true_range(window, period=ATR_PERIOD).iloc[-1]
                stop_distance_pct = ATR_MULTIPLIER * atr / current_price if pd.notna(atr) and atr > 0 else STOP_DISTANCE_PCT_FALLBACK
                exec_price = current_price * (1 + slippage_bps / 10_000)
                max_qty = position_size(cash, risk.stop_loss_per_trade, exec_price, stop_distance_pct)
                qty = max_qty * decision["suggested_size_fraction"]
                cost = qty * exec_price * (1 + fee_bps / 10_000)
                if cost > cash:
                    qty, cost = cash / (exec_price * (1 + fee_bps / 10_000)), cash
                if qty > 0:
                    positions[symbol] = {"qty": qty, "entry_price": exec_price, "opened_at": today, "last_known_price": exec_price}
                    cash -= cost
                    if not dry_run:
                        log_trade({"day": today, "symbol": symbol, "side": "buy_reactivo", "price": exec_price, "qty": qty})
                    events.append(f"COMPRA REACTIVA {symbol}: {qty:.6f} unidades a ${exec_price:.2f}")
    else:
        events.append(f"No se consulta al LLM: {block_reason}")

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

    return {"events": events, "state": state}
