"""Seguimiento y freno determinístico del gasto en la API de Claude. Mismo
principio que la capa de riesgo de trading (src/risk/risk_manager.py): nunca
se confía en que el LLM se autolimite -- el freno vive en código aparte,
totalmente independiente de lo que el modelo "decida"."""

from datetime import date
from pathlib import Path

from src.execution.trade_log import append_jsonl, read_jsonl

USAGE_LOG_PATH = Path(__file__).resolve().parents[2] / "paper_trading" / "api_usage.jsonl"

# Precios de claude-sonnet-5 por millón de tokens (verificar en
# console.anthropic.com/settings/billing si cambian).
INPUT_COST_PER_MTOK = 2.00
OUTPUT_COST_PER_MTOK = 10.00

# Techo mensual de gasto en la API de decisiones. Muy por encima del uso
# esperado (unos centavos/mes, ver historial de consultas medido) -- es un
# freno de emergencia ante un bug o un loop inesperado, no un límite ajustado
# al uso normal.
MONTHLY_BUDGET_USD = 2.00


def log_api_call(day: str, symbol: str, input_tokens: int, output_tokens: int) -> float:
    cost = (input_tokens / 1_000_000) * INPUT_COST_PER_MTOK + (output_tokens / 1_000_000) * OUTPUT_COST_PER_MTOK
    append_jsonl(
        USAGE_LOG_PATH,
        {"day": day, "symbol": symbol, "input_tokens": input_tokens, "output_tokens": output_tokens, "cost_usd": cost},
    )
    return cost


def monthly_spend(month: str | None = None) -> float:
    month = month or date.today().strftime("%Y-%m")
    return sum(r["cost_usd"] for r in read_jsonl(USAGE_LOG_PATH) if r["day"].startswith(month))


def budget_exceeded() -> bool:
    return monthly_spend() >= MONTHLY_BUDGET_USD
