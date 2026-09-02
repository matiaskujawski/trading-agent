"""Corre el vigía de volatilidad: chequea shocks y, si encuentra alguno,
dispara la reacción completa (riesgo inmediato + LLM acotado + posible
operación). Pensado para el Programador de Tareas de Windows, cada 2 horas."""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.execution.shock_reaction import react_to_shock
from src.execution.shock_watchdog import check_shocks
from src.execution.trade_log import log_shock_event

if __name__ == "__main__":
    now = datetime.now().isoformat(timespec="seconds")
    shocks = check_shocks()

    if not shocks:
        print(f"[{now}] sin shocks -- nada que hacer")
    else:
        print(f"[{now}] {len(shocks)} shock(s) detectado(s)")
        for shock in shocks:
            print(f"  {shock['symbol']}: {shock['pct_change']}% ({shock['direction']})")
            log_shock_event({"detected_at": now, **shock})
            result = react_to_shock(shock)
            for e in result["events"]:
                print(f"    - {e}")
