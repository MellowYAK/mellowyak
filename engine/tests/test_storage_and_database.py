from __future__ import annotations

import platform
import sys
from pathlib import Path

from sqlalchemy import text

from mellowyak_engine.db.database import LocalDatabase, _alembic_config_path
from mellowyak_engine.settings import config
from mellowyak_engine.storage.paths import StoragePaths


def test_platform_data_root_resolution(monkeypatch, tmp_path: Path) -> None:
    expected = tmp_path / "native" / "MellowYak"
    monkeypatch.delenv("MELLOWYAK_DATA_ROOT", raising=False)
    monkeypatch.setattr(config, "user_data_path", lambda *args, **kwargs: expected)
    assert config.resolve_data_root() == expected.resolve()


def test_documented_platform_paths_match_platformdirs_contract() -> None:
    system = platform.system().lower()
    value = str(config.resolve_data_root()).replace("\\", "/")
    if system == "darwin":
        assert value.endswith("/Library/Application Support/MellowYak")
    elif system == "windows":
        assert value.endswith("/MellowYak")
    else:
        assert value.endswith("/.local/share/MellowYak") or "/mellowyak" in value.lower()


def test_frozen_bundle_resolves_embedded_alembic_config(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert _alembic_config_path() == tmp_path / "alembic.ini"


def test_first_database_creation_migration_and_pragmas(tmp_path: Path) -> None:
    paths = StoragePaths.create(tmp_path / "data")
    database = LocalDatabase(paths)
    assert database.migrate() == "0010_passive_sentinel_orchestration"
    assert paths.sqlite_file.is_file()
    pragmas = database.sqlite_pragmas()
    assert str(pragmas["journal_mode"]).lower() == "wal"
    assert pragmas["foreign_keys"] == 1
    assert pragmas["busy_timeout"] >= 5000
    with database.engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        }
    assert {
        "alembic_version",
        "app_settings",
        "installations",
        "projects",
        "engine_runs",
        "audit_events",
        "project_changes",
        "impact_analyses",
        "context_receipts",
        "behavior_candidates",
    }.issubset(tables)


def test_installation_identity_and_settings_persist_across_restart(tmp_path: Path) -> None:
    paths = StoragePaths.create(tmp_path / "data")
    first = LocalDatabase(paths)
    first.migrate()
    first_identity = first.ensure_installation().id
    first.set_setting("appearance", "system")
    first.engine.dispose()

    second = LocalDatabase(paths)
    second.migrate()
    second_identity = second.ensure_installation().id
    assert second_identity == first_identity
    assert second.get_setting("appearance") == "system"


def test_evidence_is_a_filesystem_location_not_database_blob(tmp_path: Path) -> None:
    paths = StoragePaths.create(tmp_path / "data")
    database = LocalDatabase(paths)
    database.migrate()
    with database.engine.connect() as connection:
        columns = {
            row[1]
            for table in (
                "app_settings",
                "installations",
                "projects",
                "engine_runs",
                "audit_events",
            )
            for row in connection.execute(text(f"PRAGMA table_info({table})"))
        }
    assert "screenshot" not in columns
    assert "video" not in columns
    assert "binary_evidence" not in columns
    assert paths.evidence.is_dir()
