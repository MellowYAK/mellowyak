#!/usr/bin/env python3
"""Record local Intel macOS package, chunk, idle CPU, and idle RSS observations."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import statistics
import subprocess
import tempfile
import time
from pathlib import Path


def tree_size(root: Path) -> int:
    return sum(
        path.stat().st_size
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    )


def child_engine(parent: int) -> int | None:
    result = subprocess.run(
        ["pgrep", "-P", str(parent), "-x", "mellowyak-engine"],
        check=False,
        capture_output=True,
        text=True,
    )
    values = [int(value) for value in result.stdout.split() if value.isdigit()]
    return values[0] if len(values) == 1 else None


def sample(pid: int) -> tuple[float, int]:
    result = subprocess.run(
        ["ps", "-p", str(pid), "-o", "%cpu=,rss="],
        check=True,
        capture_output=True,
        text=True,
    )
    cpu, rss = result.stdout.split()
    return float(cpu), int(rss) * 1024


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--dmg", type=Path, required=True)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--startup", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    executable = arguments.app / "Contents/MacOS/mellowyak-desktop"
    engine_root = arguments.app / "Contents/Resources/engine/mellowyak-engine"
    browser_root = arguments.app / "Contents/Resources/browser"
    js_chunks = sorted((arguments.dist / "assets").glob("*.js"))
    chunk_rows = [
        {
            "name": path.name,
            "bytes": path.stat().st_size,
            "gzip_bytes": len(gzip.compress(path.read_bytes())),
        }
        for path in js_chunks
    ]
    acceptance_parent = Path.home() / "Library/Caches/MellowYakAcceptance"
    acceptance_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="phase11m-performance-", dir=acceptance_parent
    ) as temp:
        environment = os.environ.copy()
        environment.update(
            {
                "MELLOWYAK_DATA_ROOT": str(Path(temp) / "data"),
                "MELLOWYAK_BROWSER_HEADLESS": "1",
            }
        )
        process = subprocess.Popen(
            [str(executable)],
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        engine_pid = None
        try:
            deadline = time.monotonic() + 35
            while time.monotonic() < deadline:
                engine_pid = child_engine(process.pid)
                if engine_pid is not None:
                    break
                time.sleep(0.25)
            if engine_pid is None:
                raise RuntimeError("MACOS_ENGINE_CHILD_TIMEOUT")
            time.sleep(7)
            desktop_samples = []
            engine_samples = []
            for _ in range(3):
                desktop_samples.append(sample(process.pid))
                engine_samples.append(sample(engine_pid))
                time.sleep(2)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=15)
    startup = json.loads(arguments.startup.read_text())
    report = {
        "schema": "mellowyak.phase11m.macos-performance.v1",
        "status": "VERIFIED_WORKING",
        "scope": "local Intel macOS observation; not a universal benchmark",
        "startup": startup,
        "idle": {
            "desktop_cpu_percent_mean": round(
                statistics.mean(value[0] for value in desktop_samples), 3
            ),
            "desktop_rss_bytes_mean": round(
                statistics.mean(value[1] for value in desktop_samples)
            ),
            "engine_cpu_percent_mean": round(
                statistics.mean(value[0] for value in engine_samples), 3
            ),
            "engine_rss_bytes_mean": round(
                statistics.mean(value[1] for value in engine_samples)
            ),
            "sample_count": 3,
            "owned_children_after_quit": 0 if child_engine(process.pid) is None else 1,
        },
        "sizes": {
            "application_bytes": tree_size(arguments.app),
            "engine_directory_bytes": tree_size(engine_root),
            "browser_directory_bytes": tree_size(browser_root),
            "dmg_bytes": arguments.dmg.stat().st_size,
            "total_javascript_bytes": sum(row["bytes"] for row in chunk_rows),
            "largest_javascript_chunk": max(chunk_rows, key=lambda row: row["bytes"]),
        },
        "javascript_chunks": chunk_rows,
        "not_separately_instrumented": [
            "first_home_data",
            "first_project_overview_data",
            "diagnostics_route_load",
            "frontend_ready",
            "database_migration_component",
            "python_import_component",
        ],
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
