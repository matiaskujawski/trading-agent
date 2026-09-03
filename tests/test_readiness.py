"""El conteo de 'días sin bugs' depende de reconocer las notas de bug por su
tag -- si el filtro es demasiado angosto, se pierden notas reales en
silencio y la métrica queda optimista sin que nada lo marque como error."""

import json

import src.reporting.readiness as readiness


def write_jsonl(path, records):
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


def test_reconoce_notas_de_bug_con_distintas_formas_de_tag(tmp_path, monkeypatch):
    notes_path = tmp_path / "analyst_notes.jsonl"
    write_jsonl(
        notes_path,
        [
            {"day": "2026-08-31", "tag": "Arranque", "text": "..."},
            {"day": "2026-09-01", "tag": "Correccion tecnica", "text": "..."},
            {"day": "2026-09-02", "tag": "Bug critico corregido", "text": "..."},
            {"day": "2026-09-03", "tag": "Bug de referencia de shocks corregido", "text": "hoy"},
        ],
    )
    monkeypatch.setattr(readiness, "ANALYST_NOTES_PATH", notes_path)
    monkeypatch.setattr(readiness, "TRADES_LOG_PATH", tmp_path / "no_existe_trades.jsonl")
    monkeypatch.setattr(readiness, "SHOCK_EVENTS_PATH", tmp_path / "no_existe_shocks.jsonl")

    snap = readiness.compute_readiness_snapshot()

    # La última nota de bug es la del 2026-09-03 ("...corregido", sin la
    # palabra "correccion"), no la del 2026-09-01 -- si el filtro solo
    # buscara "correccion" se quedaría (incorrectamente) con esa última.
    assert snap["last_bug_note"] == "hoy"
    assert snap["days_since_last_bug_found"] is not None


def test_sin_notas_de_bug_no_hay_dato(tmp_path, monkeypatch):
    notes_path = tmp_path / "analyst_notes.jsonl"
    write_jsonl(notes_path, [{"day": "2026-08-31", "tag": "Arranque", "text": "..."}])
    monkeypatch.setattr(readiness, "ANALYST_NOTES_PATH", notes_path)
    monkeypatch.setattr(readiness, "TRADES_LOG_PATH", tmp_path / "no_existe_trades.jsonl")
    monkeypatch.setattr(readiness, "SHOCK_EVENTS_PATH", tmp_path / "no_existe_shocks.jsonl")

    snap = readiness.compute_readiness_snapshot()

    assert snap["days_since_last_bug_found"] is None
    assert snap["last_bug_note"] is None
