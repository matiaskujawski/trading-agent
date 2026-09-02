"""Imprime el snapshot objetivo de progreso hacia una eventual evaluación de
capital real. No decide nada por sí solo -- ver src/reporting/readiness.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.reporting.readiness import compute_readiness_snapshot

if __name__ == "__main__":
    snap = compute_readiness_snapshot()
    print(f"Operaciones reales cerradas: {snap['closed_trades']} / {snap['min_sample_trades']} ({snap['sample_pct']}%)")
    print(f"Shocks reales manejados en vivo: {snap['real_shocks_handled']}")
    if snap["days_since_last_bug_found"] is None:
        print("Racha sin bugs encontrados: sin datos todavía (ningún bug registrado aún)")
    else:
        print(f"Días desde el último bug encontrado: {snap['days_since_last_bug_found']}")
