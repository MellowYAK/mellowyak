from __future__ import annotations

import json
import secrets
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine" / "src"))

from mellowyak_engine.api.app import create_app
from mellowyak_engine.settings.config import EngineSettings


def main() -> None:
    target = ROOT / "packages" / "contracts" / "openapi.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mellowyak-openapi-") as temporary:
        app = create_app(
            EngineSettings(
                data_root=Path(temporary),
                session_token=secrets.token_urlsafe(32),
            )
        )
        target.write_text(
            json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(target)


if __name__ == "__main__":
    main()
