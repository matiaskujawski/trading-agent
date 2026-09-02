"""Vigía de volatilidad intradía: chequeo barato (sin LLM) pensado para correr
mucho más seguido que el ciclo diario completo. Compara el precio actual
contra el cierre de referencia del día y devuelve solo los activos que se
movieron más de lo normal -- eso, y solo eso, es lo que justifica escalar a
una consulta al LLM y un aviso al usuario. La inmensa mayoría de las veces
que corre, no encuentra nada y no gasta un token."""

import json
from datetime import date
from pathlib import Path

from src.config import CRYPTO_SYMBOLS, FOREX_PAIRS
from src.data_pipeline.crypto import fetch_current_price as fetch_crypto_price
from src.data_pipeline.forex import fetch_current_price as fetch_forex_price

REFERENCE_PATH = Path(__file__).resolve().parents[2] / "paper_trading" / "shock_reference.json"

# Umbral de movimiento "violento" desde el cierre de referencia, calculado por
# activo (no un número único para todos): cada uno tiene su propio percentil
# 97 de desvío diario máximo respecto al cierre anterior, sobre 8.7 años de
# historial real (ver scripts/calibrate_shock_thresholds.py). Un solo % para
# todo cripto dispararía a diario en altcoins volátiles y casi nunca en BTC --
# el mismo problema que ya corregimos con el stop-loss fijo. Apunta a ~9
# disparos por año por activo: raro de verdad, no ruido cotidiano.
SHOCK_THRESHOLDS_PCT = {
    "BTC/USDT": 11.6,
    "ETH/USDT": 14.9,
    "LINK/USDT": 17.5,
    "UNI/USDT": 19.4,
    "CAKE/USDT": 20.3,
    "XRP/USDT": 17.6,
    "SOL/USDT": 20.2,
    "ADA/USDT": 17.0,
    "DOT/USDT": 17.6,
    "AVAX/USDT": 19.0,
    "LTC/USDT": 16.1,
    "EURUSD": 1.7,
    "GBPUSD": 1.9,
    "USDJPY": 2.2,
    "USDCHF": 1.7,
    "AUDUSD": 2.2,
    "USDCAD": 1.5,
}


def save_shock_reference(prices: dict[str, float]) -> None:
    """Se llama al final de cada corrida del ciclo, pero la referencia real
    solo se actualiza una vez por día calendario (la primera corrida del
    día) -- si el ciclo corre varias veces por día para reaccionar más
    rápido a las señales técnicas, eso NO debe correr también la vara de qué
    cuenta como "shock": tiene que seguir siendo relativo al cierre real del
    día, no a "hace un rato"."""
    today = date.today().isoformat()
    existing = load_shock_reference()
    if existing.get("_date") == today:
        return
    payload = dict(prices)
    payload["_date"] = today
    REFERENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    REFERENCE_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def load_shock_reference() -> dict[str, float]:
    if not REFERENCE_PATH.exists():
        return {}
    return json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))


def check_shocks() -> list[dict]:
    """Devuelve la lista de activos que se movieron por encima de su umbral
    desde el cierre de referencia del día. Vacía en la inmensa mayoría de
    las corridas -- es justamente el punto."""
    reference = load_shock_reference()
    assets = {s: "crypto" for s in CRYPTO_SYMBOLS} | {s: "forex" for s in FOREX_PAIRS}

    shocks = []
    for symbol, asset_class in assets.items():
        ref_price = reference.get(symbol)
        if ref_price is None:
            continue
        try:
            current = fetch_crypto_price(symbol) if asset_class == "crypto" else fetch_forex_price(symbol)
        except Exception:
            continue  # un activo que no se pudo consultar no debe frenar el chequeo de los demás

        pct_change = (current - ref_price) / ref_price * 100
        threshold = SHOCK_THRESHOLDS_PCT[symbol]
        if abs(pct_change) >= threshold:
            shocks.append(
                {
                    "symbol": symbol,
                    "asset_class": asset_class,
                    "reference_price": ref_price,
                    "current_price": current,
                    "pct_change": round(pct_change, 2),
                    "direction": "sube" if pct_change > 0 else "baja",
                }
            )

    return shocks
