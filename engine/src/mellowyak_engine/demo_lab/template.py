from __future__ import annotations

import json
from pathlib import Path

DEMO_MARKER = ".mellowyak-synthetic-demo.json"
GOOD_SOURCE = '''def checkout(total: int) -> str:
    """A dependency-free synthetic protected behavior."""
    return "ok" if total >= 0 else "rejected"
'''
REGRESSION_SOURCE = '''def checkout(total: int) -> str:
    """Synthetic regression injected only inside the Demo Lab."""
    return "broken"
'''
BAD_REPAIR_SOURCE = """def checkout(total: int) -> str:
    return "still-broken"
"""


def create_template(root: Path, demo_id: str) -> None:
    root.mkdir(parents=True, mode=0o700)
    (root / DEMO_MARKER).write_text(
        json.dumps({"schema": "mellowyak.synthetic_demo.v1", "demo_id": demo_id}, sort_keys=True),
        encoding="utf-8",
    )
    (root / "checkout.py").write_text(GOOD_SOURCE, encoding="utf-8")
    (root / "README.md").write_text(
        "# Synthetic MellowYak Demo\n\nOffline, dependency-light, local-only test fixture.\n",
        encoding="utf-8",
    )
    (root / "demo-probe.json").write_text(
        json.dumps(
            {
                "schema": "mellowyak.demo_probe.v1",
                "protected_behavior": "Checkout completes successfully",
                "expected": 'return "ok"',
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
