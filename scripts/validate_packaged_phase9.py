#!/usr/bin/env python3
"""Validate Phase 9 Technical Preview contracts against the packaged engine sidecar."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import tempfile
import time
import urllib.parse
import zipfile
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from validate_packaged_phase7 import (
    assert_authentication_required,
    request,
    start_engine,
    stop_engine,
    write_report,
)

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "packaged-phase-nine-validation-token-2026"
HEAD = "0009_technical_preview_readiness"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--temp-root", type=Path)
    return parser.parse_args()


def api(
    base_url: str,
    path: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return request(base_url, TOKEN, path, method, payload)


def environment(data_root: Path) -> dict[str, str]:
    value = os.environ.copy()
    value.update(
        {
            "MELLOWYAK_SESSION_TOKEN": TOKEN,
            "MELLOWYAK_DATA_ROOT": str(data_root),
            "MELLOWYAK_BIND_HOST": "127.0.0.1",
            "MELLOWYAK_BROWSER_HEADLESS": "1",
            "MELLOWYAK_DEMO_TEST_MODE": "1",
        }
    )
    return value


def git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def repository(parent: Path, name: str, content: str = "baseline\n") -> Path:
    root = parent / name
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "MellowYak Packaged Test")
    git(root, "config", "user.email", "packaged-test@mellowyak.invalid")
    (root / "sentinel.txt").write_text(content, encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "synthetic baseline")
    return root


def wait_for_scan(base_url: str, project_id: str) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        scan = api(base_url, f"/projects/{project_id}/scan")
        if scan and scan.get("status") != "running":
            return
        time.sleep(0.05)
    raise AssertionError("packaged project scan did not finish")


def phase8_data_root(root: Path) -> tuple[Path, str]:
    data_root = root / "phase8-data"
    database = data_root / "database" / "mellowyak.sqlite3"
    database.parent.mkdir(parents=True)
    for name in ["evidence", "projects", "cache", "logs", "runtime", "backups"]:
        (data_root / name).mkdir()
    config = Config(str(ROOT / "engine" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.upgrade(config, "0008_validated_repair_apply")
    installation_id = "phase8-upgrade-fixture-installation"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO installations(id, created_at, last_started_at, app_version, engine_version) VALUES (?, ?, ?, ?, ?)",
            (
                installation_id,
                "2026-08-24T00:00:00+00:00",
                "2026-08-24T00:00:00+00:00",
                "0.1.0",
                "0.1.0",
            ),
        )
        connection.execute(
            "INSERT INTO app_settings(key, value, updated_at) VALUES (?, ?, ?)",
            ("phase8_upgrade_canary", "preserve-me", "2026-08-24T00:00:00+00:00"),
        )
        connection.commit()
    return data_root, installation_id


def validate_clean_install(engine: Path, root: Path) -> dict[str, Any]:
    data_root = root / "clean-data"
    source_parent = root / "sources"
    source_parent.mkdir()
    source = repository(source_parent, "source")
    relocated = source_parent / "relocated"
    git(source_parent, "clone", str(source), str(relocated))
    wrong = repository(source_parent, "wrong", "different\n")
    stderr_log = root / "clean-engine-stderr.log"
    handle = start_engine(engine, environment(data_root), stderr_log)
    process = handle.process
    started_at = time.monotonic()
    try:
        assert_authentication_required(handle.base_url)
        health = api(handle.base_url, "/health")
        if health["database_schema_version"] != HEAD:
            raise AssertionError("packaged engine did not migrate to Phase 9")
        onboarding = api(handle.base_url, "/app/onboarding")
        if not onboarding["requires_first_run"]:
            raise AssertionError("clean install did not require first run")
        api(
            handle.base_url,
            "/app/onboarding",
            "PUT",
            {
                "current_step": "complete",
                "selected_path": "demo_lab",
                "completed": True,
            },
        )
        replay = api(handle.base_url, "/app/onboarding/replay", "POST", {})
        if not replay["replay_active"]:
            raise AssertionError("product tour replay was not persisted")

        created = api(
            handle.base_url,
            "/projects",
            "POST",
            {
                "path": str(source),
                "display_name": "Synthetic Preview",
                "monitoring_mode": "paused",
            },
        )
        project_id = str(created["id"])
        wait_for_scan(handle.base_url, project_id)
        api(handle.base_url, f"/projects/{project_id}/disconnect", "POST", {})
        disconnected = api(handle.base_url, "/projects/disconnected")["projects"]
        if not any(item["project_id"] == project_id for item in disconnected):
            raise AssertionError("disconnected project was absent")
        wrong_result = api(
            handle.base_url,
            f"/projects/{project_id}/identity-preview?{urllib.parse.urlencode({'path': str(wrong)})}",
        )
        if wrong_result["matched"]:
            raise AssertionError("wrong project identity was accepted")
        relocation = api(
            handle.base_url,
            f"/projects/{project_id}/relocate",
            "POST",
            {"path": str(relocated)},
        )
        if (
            relocation["source_moved"]
            or relocation["source_copied"]
            or relocation["source_deleted"]
        ):
            raise AssertionError("relocation mutated source placement")

        forged = api(
            handle.base_url,
            "/notifications/activate",
            "POST",
            {"route": {"screen": "../../private", "token": "forged"}},
        )
        stale = api(
            handle.base_url,
            "/notifications/activate",
            "POST",
            {"route": {"screen": "project", "project_id": "missing"}},
        )
        if forged["status"] != "REJECTED" or stale["status"] != "STALE":
            raise AssertionError("unsafe notification route was not rejected")

        tray = api(handle.base_url, "/tray/state")
        diagnostics = api(handle.base_url, "/diagnostics")
        integrity = api(handle.base_url, "/diagnostics/storage-integrity", "POST", {})
        if tray["private_paths_exposed"] or diagnostics["bearer_token_exposed"]:
            raise AssertionError("privacy-sensitive diagnostics were exposed")
        if integrity["status"] != "PASS":
            raise AssertionError("packaged storage integrity failed")

        canary = "PHASE9_SECRET_CANARY_782B57D0"
        (data_root / "logs" / "canary.jsonl").write_text(
            json.dumps({"authorization": f"Bearer {canary}", "path": str(source)})
            + "\n",
            encoding="utf-8",
        )
        support = api(handle.base_url, "/diagnostics/support-bundle", "POST", {})
        support_path = data_root / support["relative_path"]
        raw = support_path.read_bytes()
        if canary.encode() in raw or str(source).encode() in raw:
            raise AssertionError("support bundle leaked canary or absolute source path")
        with zipfile.ZipFile(support_path) as archive:
            names = archive.namelist()
            if not any(name.endswith("manifest.json") for name in names):
                raise AssertionError("support bundle manifest missing")
            if any("snapshot" in name or "evidence" in name for name in names):
                raise AssertionError("support bundle included private evidence")

        update_results = {
            fixture: api(
                handle.base_url,
                "/updates/test/validate",
                "POST",
                {"fixture": fixture},
            )["status"]
            for fixture in [
                "no_update",
                "valid",
                "invalid_signature",
                "tampered",
                "interrupted",
            ]
        }
        expected = {
            "no_update": "NO_UPDATE",
            "valid": "ACCEPTED",
            "invalid_signature": "REJECTED",
            "tampered": "REJECTED",
            "interrupted": "REJECTED_INCOMPLETE",
        }
        if update_results != expected:
            raise AssertionError("packaged updater fixture results differed")
        battery = api(
            handle.base_url,
            "/app/activity-mode",
            "PUT",
            {"activity_mode": "battery_saver"},
        )
        if not battery["snapshot_correctness"] or not battery["critical_alerts"]:
            raise AssertionError("battery saver disabled required protection")

        installation_id = api(handle.base_url, "/installation")["installation_id"]
        source_hash = hashlib.sha256((source / "sentinel.txt").read_bytes()).hexdigest()
        wrong_hash = hashlib.sha256((wrong / "sentinel.txt").read_bytes()).hexdigest()
    finally:
        stop_engine(process)
    handle = start_engine(engine, environment(data_root), stderr_log)
    try:
        restarted_installation = api(handle.base_url, "/installation")[
            "installation_id"
        ]
        persisted = api(handle.base_url, "/app/onboarding")
        if restarted_installation != installation_id:
            raise AssertionError("same-version restart changed installation identity")
        if not persisted["completed"] or not persisted["replay_active"]:
            raise AssertionError(
                "onboarding completion and replay state did not persist"
            )
        if (
            api(handle.base_url, "/app/activity-mode")["activity_mode"]
            != "battery_saver"
        ):
            raise AssertionError("activity preference did not persist")
    finally:
        stop_engine(handle.process)
    if (
        hashlib.sha256((source / "sentinel.txt").read_bytes()).hexdigest()
        != source_hash
    ):
        raise AssertionError("packaged Phase 9 changed original source")
    if hashlib.sha256((wrong / "sentinel.txt").read_bytes()).hexdigest() != wrong_hash:
        raise AssertionError("packaged Phase 9 changed rejected source")
    return {
        "schema": health["database_schema_version"],
        "cold_start_and_flow_seconds": round(time.monotonic() - started_at, 6),
        "installation_identity_persisted": restarted_installation == installation_id,
        "first_run_persisted": True,
        "replay_supported": True,
        "disconnected_project_visible": True,
        "wrong_reconnect_rejected": True,
        "relocate_preserved_history_without_source_move": True,
        "notification_routes_rejected_safely": True,
        "tray_private": True,
        "diagnostics_private": True,
        "support_bundle_redacted": True,
        "storage_integrity": "PASS",
        "updater_fixtures": update_results,
        "battery_saver_preserved_core": True,
        "source_modified": False,
    }


def validate_upgrade(engine: Path, root: Path) -> dict[str, Any]:
    data_root, expected_installation = phase8_data_root(root)
    stderr_log = root / "upgrade-engine-stderr.log"
    handle = start_engine(engine, environment(data_root), stderr_log)
    try:
        health = api(handle.base_url, "/health")
        installation = api(handle.base_url, "/installation")
        onboarding = api(handle.base_url, "/app/onboarding")
        if health["database_schema_version"] != HEAD:
            raise AssertionError("Phase 8 fixture did not upgrade to Phase 9")
        if installation["installation_id"] != expected_installation:
            raise AssertionError("Phase 8 installation identity was not preserved")
        if (
            onboarding["requires_first_run"]
            or onboarding["selected_path"] != "existing_installation"
        ):
            raise AssertionError(
                "existing Phase 8 installation was forced through first run"
            )
    finally:
        stop_engine(handle.process)
    with sqlite3.connect(data_root / "database" / "mellowyak.sqlite3") as connection:
        canary = connection.execute(
            "SELECT value FROM app_settings WHERE key='phase8_upgrade_canary'"
        ).fetchone()
    if canary is None or canary[0] != "preserve-me":
        raise AssertionError("Phase 8 fixture data was not preserved")
    return {
        "from": "0008_validated_repair_apply",
        "to": HEAD,
        "installation_identity_preserved": True,
        "existing_data_preserved": True,
        "existing_user_first_run_skipped": True,
    }


def main() -> None:
    arguments = parse_args()
    engine = arguments.engine.expanduser().resolve(strict=True)
    output = arguments.output.expanduser().resolve(strict=False)
    parent = (
        arguments.temp_root.expanduser().resolve()
        if arguments.temp_root
        else output.parent
    )
    parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(
            prefix="mellowyak-phase9-package-", dir=parent
        ) as temp:
            root = Path(temp)
            clean = validate_clean_install(engine, root)
            upgrade = validate_upgrade(engine, root)
        report = {
            "schema": "mellowyak.phase9.packaged-validation.v1",
            "status": "VERIFIED_WORKING",
            "clean_install": clean,
            "phase8_upgrade": upgrade,
            "production_updater": "IMPLEMENTED_NOT_RUNTIME_VERIFIED",
            "real_projects_touched": False,
            "external_network_used": False,
        }
    except Exception as error:
        write_report(
            output,
            {
                "schema": "mellowyak.phase9.packaged-validation.v1",
                "status": "FAILED",
                "failure": {"type": type(error).__name__, "message": str(error)[:500]},
            },
        )
        raise
    write_report(output, report)


if __name__ == "__main__":
    main()
