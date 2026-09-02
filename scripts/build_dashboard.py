"""Genera paper_trading/dashboard.html con los datos reales actuales. No
depende de pandas/ccxt/etc, solo de la librería estándar -- pensado para
poder correr en entornos livianos (como una sesión de Claude en la nube)
sin necesidad de instalar el resto de las dependencias del proyecto."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.reporting.build_dashboard import build_dashboard_html

if __name__ == "__main__":
    path = build_dashboard_html()
    print(f"Dashboard generado en {path}")
