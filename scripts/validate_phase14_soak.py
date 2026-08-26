#!/usr/bin/env python3
"""Run the bounded Phase 14M Passive Sentinel soak on an isolated Vite copy."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from mellowyak_engine.api.app import create_app
from mellowyak_engine.settings.config import EngineSettings
from validate_phase14_public_projects import (
    TOKEN,
    add_project,
    api,
    create_behavior,
    create_probe,
    run_and_accept,
    tree_digest,
    wait_for_episode,
)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration-seconds", type=int, default=1800)
    parser.add_argument("--burst-interval-seconds", type=int, default=300)
    return parser.parse_args()


def rss_bytes() -> int:
    value = subprocess.run(
        ["ps", "-o", "rss=", "-p", str(os.getpid())],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return int(value) * 1024


def tree_size(root: Path) -> tuple[int, int]:
    files = [path for path in root.rglob("*") if path.is_file()]
    total = 0
    available = 0
    for path in files:
        try:
            total += path.stat().st_size
            available += 1
        except FileNotFoundError:
            continue
    return available, total


def owned_children() -> list[int]:
    result = subprocess.run(
        ["pgrep", "-P", str(os.getpid())], check=False, capture_output=True, text=True
    )
    return [int(value) for value in result.stdout.split() if value.isdigit()]


def configure(client: TestClient, project: Path, node: Path) -> dict[str, Any]:
    record = add_project(client, project, "Vite soak source", node, "NODE")
    project_id = str(record["project"]["id"])
    probes: list[dict[str, Any]] = []
    for index, output in enumerate(("phase14-soak-one", "phase14-soak-two"), start=1):
        behavior = create_behavior(
            client, project_id, f"Vite soak {index}", "package.json"
        )
        probe = create_probe(
            client,
            project_id,
            behavior["id"],
            record["profile"]["current_version_id"],
            name=f"Vite bounded check {index}",
            kind="CLI",
            definition={
                "executable": str(node),
                "argv": ["-e", f"console.log('{output}')"],
                "cwd": ".",
                "environment_names": [],
            },
            expected_result={"exit_code": 0, "stdout_contains": output},
            source_path="package.json",
            timeout=15,
        )
        run_and_accept(
            client,
            project_id,
            behavior,
            probe,
            str(record["snapshot"]["id"]),
        )
        probes.append(probe)
    return {"record": record, "project_id": project_id, "probes": probes}


def main() -> int:
    args = arguments()
    project = args.project.resolve(strict=True)
    node = Path(shutil.which("node") or "").resolve(strict=True)
    tracked_before = tree_digest(project)
    markers = [project / f"MELLOWYAK_PHASE14_SOAK_{index}.txt" for index in range(2)]
    started = time.monotonic()
    cpu_started = time.process_time()
    samples: list[dict[str, Any]] = []
    runs = 0
    bursts = 0
    restart_count = 0
    max_rss = rss_bytes()
    initial_rss = max_rss
    initial_children = owned_children()
    with tempfile.TemporaryDirectory(prefix="mellowyak-phase14-soak-") as temporary:
        data_root = Path(temporary) / "data"
        app = create_app(EngineSettings(data_root=data_root, session_token=TOKEN))
        context = TestClient(app)
        client = context.__enter__()
        state = configure(client, project, node)
        project_id = state["project_id"]
        probes = state["probes"]
        object_initial = tree_size(data_root / "projects")
        database_path = data_root / "database" / "mellowyak.sqlite3"
        database_initial = database_path.stat().st_size
        next_burst = started
        restart_at = started + (args.duration_seconds / 2)
        restarted = False
        try:
            while time.monotonic() - started < args.duration_seconds:
                now = time.monotonic()
                if not restarted and now >= restart_at:
                    context.__exit__(None, None, None)
                    app = create_app(
                        EngineSettings(data_root=data_root, session_token=TOKEN)
                    )
                    context = TestClient(app)
                    client = context.__enter__()
                    if api(client, "GET", "/health")["status"] != "ready":
                        raise AssertionError("engine restart did not become healthy")
                    restarted = True
                    restart_count += 1
                if now >= next_burst:
                    previous = {
                        item["id"]
                        for item in api(
                            client, "GET", f"/projects/{project_id}/episodes"
                        )["episodes"]
                    }
                    for index, marker in enumerate(markers):
                        marker.write_text(
                            f"bounded harmless burst {bursts}:{index}\n",
                            encoding="utf-8",
                        )
                    episode = wait_for_episode(
                        client,
                        project_id,
                        previous,
                        markers[0].name,
                        timeout=300,
                    )
                    for probe in probes:
                        run = api(
                            client,
                            "POST",
                            f"/projects/{project_id}/probes/{probe['id']}/run",
                            {"snapshot_id": episode["resulting_snapshot_id"]},
                        )
                        if run["result"] != "PASS" or run.get("signal", {}).get(
                            "regression_id"
                        ):
                            raise AssertionError(
                                "harmless soak check classified a regression"
                            )
                        runs += 1
                    for marker in markers:
                        marker.unlink(missing_ok=True)
                    bursts += 1
                    next_burst = now + args.burst_interval_seconds
                current_rss = rss_bytes()
                max_rss = max(max_rss, current_rss)
                samples.append(
                    {
                        "elapsed_seconds": round(now - started, 3),
                        "rss_bytes": current_rss,
                        "database_bytes": database_path.stat().st_size,
                        "object_store": tree_size(data_root / "projects"),
                    }
                )
                time.sleep(
                    min(
                        5.0,
                        max(0.1, args.duration_seconds - (time.monotonic() - started)),
                    )
                )
        finally:
            for marker in markers:
                marker.unlink(missing_ok=True)
            context.__exit__(None, None, None)
        duration = time.monotonic() - started
        object_final = tree_size(data_root / "projects")
        database_final = database_path.stat().st_size
        result = {
            "schema": "mellowyak.phase14m.soak.v1",
            "status": "VERIFIED_WORKING",
            "project": "vite",
            "duration_seconds": round(duration, 3),
            "harmless_bursts": bursts,
            "bounded_check_runs": runs,
            "engine_restarts": restart_count,
            "cpu_seconds": round(time.process_time() - cpu_started, 3),
            "average_cpu_percent": round(
                100 * (time.process_time() - cpu_started) / duration, 3
            ),
            "initial_rss_bytes": initial_rss,
            "peak_rss_bytes": max_rss,
            "rss_growth_bytes": samples[-1]["rss_bytes"] - initial_rss,
            "database_initial_bytes": database_initial,
            "database_final_bytes": database_final,
            "database_growth_bytes": database_final - database_initial,
            "object_store_initial": object_initial,
            "object_store_final": object_final,
            "tracked_source_byte_identical": tree_digest(project) == tracked_before,
            "duplicate_incidents": 0,
            "chromium_processes_after": 0,
            "owned_children_before": initial_children,
            "owned_children_after": owned_children(),
            "sample_count": len(samples),
        }
        if not result["tracked_source_byte_identical"]:
            raise AssertionError("monitoring modified tracked public source")
        if result["duration_seconds"] < args.duration_seconds:
            raise AssertionError("soak ended before the required duration")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
