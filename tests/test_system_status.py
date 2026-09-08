"""Tests del estado manual de pausa/reanudación del sistema."""

import src.execution.system_status as system_status


def test_load_sin_archivo_devuelve_no_pausado(tmp_path, monkeypatch):
    monkeypatch.setattr(system_status, "SYSTEM_STATUS_PATH", tmp_path / "no_existe.json")
    status = system_status.load_system_status()
    assert status == {"paused": False, "paused_at": None, "note": None}


def test_set_paused_true_guarda_nota_y_timestamp(tmp_path, monkeypatch):
    monkeypatch.setattr(system_status, "SYSTEM_STATUS_PATH", tmp_path / "system_status.json")
    system_status.set_paused(True, note="frenado a pedido del usuario")
    status = system_status.load_system_status()
    assert status["paused"] is True
    assert status["note"] == "frenado a pedido del usuario"
    assert status["paused_at"] is not None


def test_set_paused_false_limpia_el_timestamp(tmp_path, monkeypatch):
    monkeypatch.setattr(system_status, "SYSTEM_STATUS_PATH", tmp_path / "system_status.json")
    system_status.set_paused(True, note="frenado")
    system_status.set_paused(False)
    status = system_status.load_system_status()
    assert status["paused"] is False
    assert status["paused_at"] is None
