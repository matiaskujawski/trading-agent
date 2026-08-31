"""Vigía de volatilidad intradía: chequeo barato (sin LLM) pensado para correr
mucho más seguido que el ciclo diario completo. Compara el precio actual
contra el cierre de referencia del día y devuelve solo los activos que se
movieron más de lo normal -- eso, y solo eso, es lo que justifica escalar a
una consulta al LLM y un aviso al usuario. La inmensa mayoría de las veces
que corre, no encuentra nada y no gasta un token."""

import json
from pathlib import Path

from src.config import CRYPTO_SYMBOLS, FOREX_PAIRS
from src.data_pipeline.crypto import fetch_current_price as fetch_crypto_price
from src.data_pipeline.forex import fetch_current_price as fetch_forex_price

REFERENCE_PATH = Path(__file__).resolve().parents[2] / "paper_trading" / "shock_reference.json"

# Umbral de movimiento "violento" desde el cierre de referencia. Cripto se
# mueve normalmente más que forex en un día -- por eso el umbral es distinto
# por clase de activo, no un único número para todos.
CRYPTO_SHOCK_PCT = 5.0
FOREX_SHOCK_PCT = 1.5


def save_shock_reference(prices: dict[str, float]) -> None:
    """Se llama una vez por día, al final del ciclo diario, con el cierre de
    cada activo -- es contra lo que se compara el resto del día."""
    REFERENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    REFERENCE_PATH.write_text(json.dumps(prices, indent=2, ensure_ascii=False), encoding="utf-8")


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
        threshold = CRYPTO_SHOCK_PCT if asset_class == "crypto" else FOREX_SHOCK_PCT
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
