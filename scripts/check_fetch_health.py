"""Imprime los símbolos cuya fuente de datos lleva más de STALE_HOURS sin una
descarga exitosa -- la señal de una falla silenciosa como la de Binance
devolviendo 451 durante más de 21 horas sin que nada lo marcara. Salida vacía
es el caso normal: todo se está descargando bien."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.execution.fetch_health import STALE_HOURS, stale_symbols

if __name__ == "__main__":
    stale = stale_symbols()
    if not stale:
        print("Todas las fuentes de datos tienen una descarga exitosa reciente.")
    else:
        print(f"{len(stale)} símbolo(s) sin descarga exitosa hace más de {STALE_HOURS}hs:")
        for s in stale:
            age = "nunca tuvo una descarga exitosa" if s["hours_since_success"] is None else f"hace {s['hours_since_success']}hs"
            print(f"  - {s['symbol']}: {age} -- último error: {s['last_error']}")
