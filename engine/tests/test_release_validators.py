from __future__ import annotations

import importlib.util
import secrets
import shutil
import sys
from pathlib import Path

from mellowyak_engine.api.app import create_app
from mellowyak_engine.settings.config import EngineSettings


def test_macos_acceptance_lab_tracks_the_repository_database_head() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    validator_path = repository_root / "scripts/validate_macos_acceptance_lab.py"
    sys.path.insert(0, str(validator_path.parent))
    spec = importlib.util.spec_from_file_location("validate_macos_acceptance_lab", validator_path)
    assert spec is not None and spec.loader is not None
    validator = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(validator)
    finally:
        sys.path.pop(0)

    assert validator.current_database_head() == "0011_baseline_lock_and_local_proof"


def test_app_shutdown_releases_local_files(tmp_path: Path) -> None:
    app = create_app(EngineSettings(data_root=tmp_path, session_token=secrets.token_urlsafe(32)))

    for shutdown_handler in app.router.on_shutdown:
        shutdown_handler()
    shutil.rmtree(tmp_path)

    assert not tmp_path.exists()
