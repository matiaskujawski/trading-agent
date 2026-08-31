"""Persistencia del estado del portafolio de paper trading entre corridas del
ciclo diario. El archivo de estado es la fuente de verdad de cuánto capital y
qué posiciones hay abiertas -- se lee al empezar cada ciclo y se guarda al
terminar, para que el sistema "recuerde" dónde estaba de un día al otro."""

import json
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parents[2] / "paper_trading" / "state.json"


def default_state(starting_capital: float) -> dict:
    return {
        "starting_capital": starting_capital,
        "cash": starting_capital,
        "positions": {},  # symbol -> {"qty":, "entry_price":, "opened_at":}
        "peak_equity": starting_capital,
        "daily_loss": 0.0,
        "current_day": None,
        "halted": False,
    }


def load_state(starting_capital: float, path: Path = STATE_PATH) -> dict:
    if not path.exists():
        return default_state(starting_capital)
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(state: dict, path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
