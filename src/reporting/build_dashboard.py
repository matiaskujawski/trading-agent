"""Genera el HTML final del dashboard con los datos reales inyectados, listo
para publicarse como Artifact. No lo publica -- eso lo hace Claude en la
sesión que corre el ciclo diario, con la herramienta de Artifacts."""

import json
from pathlib import Path

from src.reporting.dashboard_data import build_dashboard_data

TEMPLATE_PATH = Path(__file__).resolve().parent / "dashboard_template.html"
DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parents[2] / "paper_trading" / "dashboard.html"
PLACEHOLDER = "/*__DASHBOARD_DATA__*/"


def build_dashboard_html(output_path: Path = DEFAULT_OUTPUT_PATH) -> Path:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    data = build_dashboard_data()

    obj_start = template.index(PLACEHOLDER) + len(PLACEHOLDER)  # apunta al "{" del objeto por defecto
    obj_end = template.index("};", obj_start) + 1  # incluye el "}" de cierre, sin el ";"
    injected = template[:obj_start] + json.dumps(data, ensure_ascii=False) + template[obj_end:]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(injected, encoding="utf-8")
    return output_path
