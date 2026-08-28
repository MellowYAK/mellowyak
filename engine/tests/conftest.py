from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ENGINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE_ROOT / "src"))


@pytest.fixture
def create_symlink():
    def create(link: Path, target: Path) -> None:
        try:
            link.symlink_to(target, target_is_directory=target.is_dir())
        except OSError as error:
            if os.name == "nt" and error.winerror == 1314:
                pytest.skip("Windows symlink creation requires Developer Mode or elevation")
            raise

    return create
