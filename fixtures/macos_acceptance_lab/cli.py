#!/usr/bin/env python3
"""Dependency-free CLI surface for the synthetic macOS Acceptance Lab."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("status", "checkout"))
    arguments = parser.parse_args()
    behavior = json.loads(Path(__file__).with_name("behavior.json").read_text())
    allowed = arguments.command == "status" or bool(behavior["checkout_enabled"])
    print(json.dumps({"command": arguments.command, "ok": allowed}, sort_keys=True))
    return 0 if allowed else 2


if __name__ == "__main__":
    raise SystemExit(main())
