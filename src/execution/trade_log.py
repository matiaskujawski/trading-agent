"""Registro de operaciones y de capital diario -- append-only, en formato JSONL
(una línea de JSON por evento, nunca se reescribe lo viejo). Es lo que van a
leer tanto el reporte diario del "analista" como el dashboard visual."""

import json
from pathlib import Path

TRADES_LOG_PATH = Path(__file__).resolve().parents[2] / "paper_trading" / "trades.jsonl"
EQUITY_LOG_PATH = Path(__file__).resolve().parents[2] / "paper_trading" / "equity_daily.jsonl"
ANALYST_NOTES_PATH = Path(__file__).resolve().parents[2] / "paper_trading" / "analyst_notes.jsonl"
SHOCK_EVENTS_PATH = Path(__file__).resolve().parents[2] / "paper_trading" / "shock_events.jsonl"


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_trade(record: dict, path: Path = TRADES_LOG_PATH) -> None:
    append_jsonl(path, record)


def log_daily_equity(record: dict, path: Path = EQUITY_LOG_PATH) -> None:
    """A diferencia de log_trade, acá sí puede haber más de una corrida por
    día real (ej: una corrida manual el mismo día que ya corrió el ciclo
    automático) -- si ya hay una fila para ese "day", se reemplaza en vez de
    agregar una duplicada."""
    existing = read_jsonl(path)
    if existing and existing[-1].get("day") == record.get("day"):
        existing[-1] = record
        path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in existing) + "\n", encoding="utf-8")
    else:
        append_jsonl(path, record)


def log_analyst_note(record: dict, path: Path = ANALYST_NOTES_PATH) -> None:
    append_jsonl(path, record)


def log_shock_event(record: dict, path: Path = SHOCK_EVENTS_PATH) -> None:
    """Un shock real detectado en vivo (nunca uno simulado para pruebas) --
    es uno de los hitos que definimos para evaluar si ya vale la pena hablar
    de plata real: ver un shock de verdad manejado, no solo uno fabricado."""
    append_jsonl(path, record)


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
