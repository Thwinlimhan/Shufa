from datetime import datetime, timedelta, timezone

from backend.data import service, storage


def _set_temp_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(storage, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(storage, "CURATED_DB", tmp_path / "curated" / "workbench.duckdb")
    monkeypatch.setattr(storage, "META_DB", tmp_path / "meta" / "workbench.db")


def test_runner_state_dedupes_same_bar(monkeypatch, tmp_path) -> None:
    _set_temp_paths(monkeypatch, tmp_path)
    ts = datetime(2025, 1, 1, tzinfo=timezone.utc)

    assert service.should_process_bar("paper:test", ts) is True
    service.mark_processed("paper:test", ts)
    assert service.should_process_bar("paper:test", ts) is False
    assert service.should_process_bar("paper:test", ts + timedelta(minutes=15)) is True
