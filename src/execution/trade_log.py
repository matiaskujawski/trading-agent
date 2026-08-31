"""Registro de operaciones y de capital diario -- append-only, en formato JSONL
(una línea de JSON por evento, nunca se reescribe lo viejo). Es lo que van a
leer tanto el reporte diario del "analista" como el dashboard visual."""

import json
from pathlib import Path

TRADES_LOG_PATH = Path(__file__).resolve().parents[2] / "paper_trading" / "trades.jsonl"
EQUITY_LOG_PATH = Path(__file__).resolve().parents[2] / "paper_trading" / "equity_daily.jsonl"
ANALYST_NOTES_PATH = Path(__file__).resolve().parents[2] / "paper_trading" / "analyst_notes.jsonl"


def _append(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_trade(record: dict, path: Path = TRADES_LOG_PATH) -> None:
    _append(path, record)


def log_daily_equity(record: dict, path: Path = EQUITY_LOG_PATH) -> None:
    _append(path, record)


def log_analyst_note(record: dict, path: Path = ANALYST_NOTES_PATH) -> None:
    _append(path, record)


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
