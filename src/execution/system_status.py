"""Estado manual de pausa/reanudación del sistema -- distinto de "is_live"
(que solo dice si ya hay historial real). El sistema puede tener historial
real Y estar pausado a la vez (ej: el usuario pidió frenar todo para no
consumir tokens); el dashboard necesita poder mostrar eso. Nadie automático
escribe este archivo -- solo se toca a pedido explícito del usuario."""

import json
from datetime import datetime, timezone
from pathlib import Path

SYSTEM_STATUS_PATH = Path(__file__).resolve().parents[2] / "paper_trading" / "system_status.json"


def load_system_status() -> dict:
    if not SYSTEM_STATUS_PATH.exists():
        return {"paused": False, "paused_at": None, "note": None}
    return json.loads(SYSTEM_STATUS_PATH.read_text(encoding="utf-8"))


def set_paused(paused: bool, note: str | None = None) -> None:
    payload = {
        "paused": paused,
        "paused_at": datetime.now(timezone.utc).isoformat(timespec="seconds") if paused else None,
        "note": note,
    }
    SYSTEM_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SYSTEM_STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
