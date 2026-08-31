"""Arma el dict de datos que el dashboard (src/reporting/dashboard_template.html)
necesita para renderizarse, leyendo el registro real de paper_trading/."""

from datetime import datetime, timezone

from src.config import CRYPTO_SYMBOLS, FOREX_PAIRS, RISK_PARAMS
from src.execution.trade_log import ANALYST_NOTES_PATH, EQUITY_LOG_PATH, TRADES_LOG_PATH, read_jsonl


def build_dashboard_data() -> dict:
    equity_daily = read_jsonl(EQUITY_LOG_PATH)
    trades = read_jsonl(TRADES_LOG_PATH)
    analyst_notes = read_jsonl(ANALYST_NOTES_PATH)

    return {
        "meta": {
            "starting_capital": RISK_PARAMS["starting_capital"],
            "max_drawdown": RISK_PARAMS["max_drawdown"],
            "daily_loss_limit": RISK_PARAMS["daily_loss_limit"],
            "stop_loss_per_trade": RISK_PARAMS["stop_loss_per_trade"],
            "universe_crypto": CRYPTO_SYMBOLS,
            "universe_forex": FOREX_PAIRS,
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "is_live": len(equity_daily) > 0,
        },
        "equity_daily": equity_daily,
        "trades": trades,
        "analyst_notes": analyst_notes,
    }
