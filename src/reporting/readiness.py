"""Snapshot objetivo del progreso hacia una eventual evaluación de capital
real. Nunca decide por sí solo pasar a plata real -- eso es siempre una
conversación explícita con el usuario (ver CONTEXTO.md). Esto solo junta
los hechos (cuántas operaciones reales, si ya hubo un shock real manejado,
hace cuánto no se encuentra un bug) para que esa conversación, cuando
llegue, parta de datos concretos -- y para que el aviso proactivo al
usuario tenga algo real que decir, no una sensación."""

from datetime import date

from src.execution.trade_log import ANALYST_NOTES_PATH, SHOCK_EVENTS_PATH, TRADES_LOG_PATH, read_jsonl

# Piso de operaciones reales cerradas para tener una muestra mínimamente
# informativa (acordado con el usuario: por debajo de esto, cualquier
# estadística es en gran parte ruido).
MIN_SAMPLE_TRADES = 30

CLOSING_SIDES = {
    "sell",
    "stop_loss_exit",
    "risk_halt_exit",
    "sell_reactivo",
    "stop_loss_exit_reactivo",
    "risk_halt_exit_reactivo",
}


def compute_readiness_snapshot() -> dict:
    trades = read_jsonl(TRADES_LOG_PATH)
    closed_trades = [t for t in trades if t.get("side") in CLOSING_SIDES]

    shock_events = read_jsonl(SHOCK_EVENTS_PATH)

    notes = read_jsonl(ANALYST_NOTES_PATH)
    bug_notes = [n for n in notes if "correccion" in n.get("tag", "").lower()]
    last_bug_day = bug_notes[-1]["day"] if bug_notes else None
    days_since_bug = (date.today() - date.fromisoformat(last_bug_day)).days if last_bug_day else None

    return {
        "closed_trades": len(closed_trades),
        "min_sample_trades": MIN_SAMPLE_TRADES,
        "sample_pct": round(100 * len(closed_trades) / MIN_SAMPLE_TRADES, 1),
        "real_shocks_handled": len(shock_events),
        "days_since_last_bug_found": days_since_bug,
        "last_bug_note": bug_notes[-1]["text"] if bug_notes else None,
    }
