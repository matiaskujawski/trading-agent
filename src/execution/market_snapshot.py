"""Foto del estado de cada activo del universo al final de cada ciclo -- para
que el dashboard pueda mostrar actividad real del sistema (qué evaluó, qué
tan cerca estuvo algún activo de un cruce de medias) incluso cuando no hubo
ninguna operación. No es historial: se pisa entera en cada corrida, siempre
representa "ahora", no el pasado."""

import json
from datetime import datetime, timezone
from pathlib import Path

MARKET_SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / "paper_trading" / "market_snapshot.json"


def save_market_snapshot(assets: dict) -> None:
    """assets: símbolo -> {"asset_class", "price", "gap_pct", "has_position"}."""
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "assets": assets,
    }
    MARKET_SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    MARKET_SNAPSHOT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_market_snapshot() -> dict:
    if not MARKET_SNAPSHOT_PATH.exists():
        return {"updated_at": None, "assets": {}}
    return json.loads(MARKET_SNAPSHOT_PATH.read_text(encoding="utf-8"))
