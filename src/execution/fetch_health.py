"""Registro de salud de las fuentes de datos por símbolo -- para detectar
fallas silenciosas como la de Binance devolviendo 451 durante más de 21
horas sin que nada lo marcara. Un ciclo puede terminar "exitoso" aunque
varios símbolos hayan fallado en silencio (el error se atrapa y se sigue,
a propósito, para que un símbolo roto no frene a los demás); este módulo
hace visible esa falla acumulada en vez de dejarla en logs que nadie mira."""

import json
from datetime import datetime, timezone
from pathlib import Path

FETCH_HEALTH_PATH = Path(__file__).resolve().parents[2] / "paper_trading" / "fetch_health.json"

# Si un símbolo lleva más que esto sin una descarga exitosa, se considera
# "silenciosamente roto" -- bastante más que un ciclo (cada 2hs) para no
# marcar falso positivo por un error transitorio puntual.
STALE_HOURS = 6


def load_fetch_health() -> dict:
    if not FETCH_HEALTH_PATH.exists():
        return {}
    return json.loads(FETCH_HEALTH_PATH.read_text(encoding="utf-8"))


def record_fetch_results(results: dict[str, str | None]) -> dict:
    """results: símbolo -> None si la descarga salió bien, o el mensaje de
    error si falló. Actualiza y persiste el registro de salud, devuelve el
    registro completo actualizado."""
    health = load_fetch_health()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for symbol, error in results.items():
        entry = health.get(symbol, {"last_success": None, "last_error": None, "consecutive_failures": 0})
        if error is None:
            entry["last_success"] = now
            entry["last_error"] = None
            entry["consecutive_failures"] = 0
        else:
            entry["last_error"] = error
            entry["consecutive_failures"] = entry.get("consecutive_failures", 0) + 1
        health[symbol] = entry

    FETCH_HEALTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    FETCH_HEALTH_PATH.write_text(json.dumps(health, ensure_ascii=False, indent=2), encoding="utf-8")
    return health


def stale_symbols(health: dict | None = None) -> list[dict]:
    """Símbolos sin ninguna descarga exitosa registrada, o cuya última
    descarga exitosa fue hace más de STALE_HOURS -- la señal de que algo
    está fallando en silencio, no solo un error puntual de una corrida."""
    health = health if health is not None else load_fetch_health()
    now = datetime.now(timezone.utc)
    stale = []
    for symbol, entry in health.items():
        last_success = entry.get("last_success")
        if last_success is None:
            stale.append({"symbol": symbol, "hours_since_success": None, "last_error": entry.get("last_error")})
            continue
        age_hours = (now - datetime.fromisoformat(last_success)).total_seconds() / 3600
        if age_hours > STALE_HOURS:
            stale.append({"symbol": symbol, "hours_since_success": round(age_hours, 1), "last_error": entry.get("last_error")})
    return stale
