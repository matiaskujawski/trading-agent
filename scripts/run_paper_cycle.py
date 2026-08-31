"""Corre un ciclo de paper trading (con datos de mercado reales y actuales,
pero decisión mock -- todavía sin la API real de Claude conectada)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.execution.paper_cycle import run_daily_cycle

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    result = run_daily_cycle(dry_run=dry_run)

    print(f"Ciclo del {result['day']} ({'prueba, no se guardó nada' if dry_run else 'guardado'})\n")
    print(f"Equity: ${result['equity']:,.2f}")
    print(f"Posiciones abiertas: {list(result['state']['positions'].keys())}")
    print(f"Cash disponible: ${result['state']['cash']:,.2f}")
    print(f"Frenado: {result['state']['halted']}\n")

    print("Eventos del ciclo:")
    for e in result["events"]:
        print(f"  - {e}")

    if not result["events"]:
        print("  (sin gatillos técnicos hoy en ningún activo)")
