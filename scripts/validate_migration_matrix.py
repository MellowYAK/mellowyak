#!/usr/bin/env python3
"""Upgrade disposable databases from every historical MellowYak revision to head."""

from __future__ import annotations

import argparse
import json
import sqlite3
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[1]
REVISIONS = [
    "0001_local_core",
    "0002_project_git_impact",
    "0003_reverse_impact_context",
    "0004_behavior_evidence_browser",
    "0005_verification_regression_gate",
    "0006_desktop_productization",
    "0007_runtime_snapshot_probe_foundation",
    "0008_validated_repair_apply",
    "0009_technical_preview_readiness",
]
HEAD = "0010_passive_sentinel_orchestration"


def config(database: Path) -> Config:
    value = Config(str(ROOT / "engine" / "alembic.ini"))
    value.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    return value


def upgrade_case(database: Path, starting_revision: str | None) -> dict[str, object]:
    value = config(database)
    if starting_revision is not None:
        command.upgrade(value, starting_revision)
        with sqlite3.connect(database) as connection:
            connection.execute(
                "INSERT INTO app_settings(key, value, updated_at) VALUES (?, ?, ?)",
                (
                    "migration_matrix_canary",
                    starting_revision,
                    "2026-08-25T00:00:00+00:00",
                ),
            )
            connection.commit()
    command.upgrade(value, "head")
    with sqlite3.connect(database) as connection:
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0]
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        canary = (
            connection.execute(
                "SELECT value FROM app_settings WHERE key = 'migration_matrix_canary'"
            ).fetchone()
            if starting_revision is not None
            else None
        )
    required = {
        "onboarding_state",
        "technical_preview_preferences",
        "project_location_history",
        "diagnostic_runs",
        "support_bundle_records",
        "notification_activation_events",
        "update_validation_runs",
        "package_acceptance_runs",
    }
    if revision != HEAD or required - tables:
        raise AssertionError(
            f"migration from {starting_revision or 'empty'} did not reach Phase 9"
        )
    if starting_revision is not None and (
        canary is None or canary[0] != starting_revision
    ):
        raise AssertionError(
            f"migration from {starting_revision} did not preserve existing data"
        )
    return {
        "from": starting_revision or "empty",
        "to": revision,
        "existing_data_preserved": starting_revision is None
        or canary[0] == starting_revision,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="mellowyak-migration-matrix-") as temporary:
        root = Path(temporary)
        results = [upgrade_case(root / "empty.sqlite3", None)]
        results.extend(
            upgrade_case(root / f"{revision}.sqlite3", revision)
            for revision in REVISIONS
        )
    report = {
        "schema": "mellowyak.phase9.migration-matrix.v1",
        "status": "VERIFIED_WORKING",
        "head": HEAD,
        "cases": results,
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
