#!/usr/bin/env python3
"""Known-good local test command for the synthetic Acceptance Lab."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    marker = json.loads((root / ".mellowyak-synthetic-lab.json").read_text())
    behavior = json.loads((root / "behavior.json").read_text())
    passed = (
        marker.get("synthetic") is True
        and marker.get("real_project_actions_allowed") is False
        and behavior == {"checkout_enabled": True, "currency": "USD"}
    )
    print(json.dumps({"known_good": passed}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
