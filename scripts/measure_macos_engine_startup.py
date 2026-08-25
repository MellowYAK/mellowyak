#!/usr/bin/env python3
"""Measure packaged engine handshake time without touching live MellowYak data."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import tempfile
import time
from pathlib import Path

from validate_packaged_phase7 import start_engine, stop_engine


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--engine", action="append", nargs=2, metavar=("LABEL", "PATH"), required=True
    )
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    results: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="mellowyak-phase11m-startup-") as temporary:
        root = Path(temporary)
        for label, raw_path in arguments.engine:
            path = Path(raw_path).resolve()
            if not path.is_file():
                results[label] = {"status": "NOT_AVAILABLE", "path_recorded": False}
                continue
            timings: list[float] = []
            for index in range(arguments.runs):
                data_root = root / label / f"run-{index}" / "data"
                environment = os.environ.copy()
                environment.update(
                    {
                        "MELLOWYAK_SESSION_TOKEN": "phase11m-startup-measurement-token-2026",
                        "MELLOWYAK_DATA_ROOT": str(data_root),
                        "MELLOWYAK_BIND_HOST": "127.0.0.1",
                    }
                )
                started = time.monotonic()
                handle = start_engine(
                    path, environment, root / f"{label}-{index}.stderr"
                )
                timings.append(round(time.monotonic() - started, 6))
                stop_engine(handle.process)
            results[label] = {
                "status": "MEASURED",
                "runs_seconds": timings,
                "minimum_seconds": min(timings),
                "median_seconds": round(statistics.median(timings), 6),
                "maximum_seconds": max(timings),
                "executable_bytes": path.stat().st_size,
                "path_recorded": False,
            }
    report = {
        "schema": "mellowyak.phase11m.macos-startup.v1",
        "status": "VERIFIED_WORKING",
        "scope": "disposable_data_roots_only",
        "results": results,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
