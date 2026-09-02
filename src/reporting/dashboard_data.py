"""Arma el dict de datos que el dashboard (src/reporting/dashboard_template.html)
necesita para renderizarse, leyendo el registro real de paper_trading/."""

from datetime import datetime, timedelta, timezone

from src.config import CRYPTO_SYMBOLS, FOREX_PAIRS, RISK_PARAMS
from src.execution.api_usage import MONTHLY_BUDGET_USD, monthly_spend
from src.execution.trade_log import ANALYST_NOTES_PATH, EQUITY_LOG_PATH, TRADES_LOG_PATH, read_jsonl

# Argentina no usa horario de verano -- UTC-3 es fijo todo el año.
ARGENTINA_TZ = timezone(timedelta(hours=-3))


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
            "last_updated": datetime.now(ARGENTINA_TZ).strftime("%Y-%m-%d %H:%M ART"),
            "is_live": len(equity_daily) > 0,
            "api_spend_month_usd": round(monthly_spend(), 4),
            "api_budget_month_usd": MONTHLY_BUDGET_USD,
        },
        "equity_daily": equity_daily,
        "trades": trades,
        "analyst_notes": analyst_notes,
    }
