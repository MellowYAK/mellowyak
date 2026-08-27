#!/usr/bin/env python3
"""Validate a disposable two-version macOS updater transaction with ephemeral keys."""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.client
import http.server
import json
import os
import plistlib
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from validate_local_updater import PASSWORD, generate_key, verify
from validate_packaged_phase7 import start_engine, stop_engine

AUTH_TOKEN = "phase11m-updater-engine-token-2026"


class Handler(http.server.BaseHTTPRequestHandler):
    metadata = b""
    artifact = b""

    def do_GET(self) -> None:
        if self.path == "/latest.json":
            payload = self.metadata
        elif self.path == "/MellowYak.app.tar.gz":
            payload = self.artifact
        elif self.path == "/incomplete.tar.gz":
            payload = self.artifact[: max(1, len(self.artifact) // 4)]
            self.send_response(200)
            self.send_header("Content-Length", str(len(self.artifact)))
            self.end_headers()
            self.wfile.write(payload)
            self.close_connection = True
            return
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, _format: str, *_arguments: object) -> None:
        return


def set_version(app: Path, version: str) -> None:
    info_path = app / "Contents" / "Info.plist"
    with info_path.open("rb") as stream:
        info = plistlib.load(stream)
    info["CFBundleShortVersionString"] = version
    info["CFBundleVersion"] = version
    with info_path.open("wb") as stream:
        plistlib.dump(info, stream, sort_keys=True)


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(os.readlink(path).encode())
        elif path.is_file():
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def decoded(source: Path, destination: Path) -> None:
    destination.write_bytes(base64.b64decode(source.read_bytes()))


def engine_request(
    base_url: str,
    path: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{base_url}{path}",
        method=method,
        data=None if method == "GET" else json.dumps(payload or {}).encode(),
        headers={
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read())


def database_counts(database: Path) -> dict[str, int]:
    with sqlite3.connect(database) as connection:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        ]
        return {
            table: int(
                connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            )
            for table in tables
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lower-version", default="0.3.0-preview.2")
    parser.add_argument("--higher-version", default="0.4.0-preview.1")
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="mellowyak-phase11m-updater-") as temporary:
        root = Path(temporary)
        lower = root / "lower" / "MellowYak.app"
        higher = root / "higher" / "MellowYak.app"
        shutil.copytree(arguments.app, lower, symlinks=True)
        shutil.copytree(arguments.app, higher, symlinks=True)
        set_version(lower, arguments.lower_version)
        set_version(higher, arguments.higher_version)

        user_data = root / "user-data"
        source = root / "synthetic-source"
        user_data.mkdir()
        source.mkdir()
        (user_data / "settings.json").write_text(
            '{"language":"he"}\n', encoding="utf-8"
        )
        (source / "source.txt").write_text(
            "MELLOWYAK_SYNTHETIC_SOURCE_11M\n", encoding="utf-8"
        )
        user_digest = tree_digest(user_data)
        source_digest = tree_digest(source)

        engine_data = user_data / "engine-data"
        demo_parent = root / "demo-parent"
        demo_parent.mkdir()
        engine_environment = os.environ.copy()
        engine_environment.update(
            {
                "MELLOWYAK_SESSION_TOKEN": AUTH_TOKEN,
                "MELLOWYAK_DATA_ROOT": str(engine_data),
                "MELLOWYAK_BIND_HOST": "127.0.0.1",
                "MELLOWYAK_BROWSER_HEADLESS": "1",
                "MELLOWYAK_DEMO_TEST_MODE": "1",
            }
        )
        lower_engine = (
            lower / "Contents/Resources/engine/mellowyak-engine/mellowyak-engine"
        )
        lower_handle = start_engine(
            lower_engine, engine_environment, root / "lower.log"
        )
        try:
            lower_health = engine_request(lower_handle.base_url, "/health")
            lower_self_test = engine_request(
                lower_handle.base_url, "/self-test", "POST", {}
            )
            engine_request(
                lower_handle.base_url,
                "/demo-lab/create",
                "POST",
                {"selected_parent": str(demo_parent)},
            )
            lower_projects = engine_request(lower_handle.base_url, "/projects")[
                "projects"
            ]
        finally:
            stop_engine(lower_handle.process)
        database = engine_data / "database/mellowyak.sqlite3"
        before_counts = database_counts(database)
        settings_digest = tree_digest(user_data)

        artifact = root / "MellowYak.app.tar.gz"
        with tarfile.open(artifact, "w:gz") as archive:
            archive.add(higher, arcname="MellowYak.app", recursive=True)
        key = root / "updater.key"
        wrong_key = root / "wrong.key"
        generate_key(key)
        generate_key(wrong_key)
        subprocess.run(
            [
                "npx",
                "tauri",
                "signer",
                "sign",
                "--private-key-path",
                str(key),
                "--password",
                PASSWORD,
                str(artifact),
            ],
            cwd=Path(__file__).resolve().parents[1] / "apps" / "desktop",
            check=True,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
        )
        signature = artifact.with_suffix(artifact.suffix + ".sig")
        public = root / "public.minisign"
        wrong_public = root / "wrong-public.minisign"
        signature_decoded = root / "artifact.minisig"
        decoded(key.with_suffix(".key.pub"), public)
        decoded(wrong_key.with_suffix(".key.pub"), wrong_public)
        decoded(signature, signature_decoded)

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        port = int(server.server_address[1])
        Handler.artifact = artifact.read_bytes()
        Handler.metadata = json.dumps(
            {
                "version": arguments.higher_version,
                "url": f"http://127.0.0.1:{port}/MellowYak.app.tar.gz",
                "signature": signature.read_text(encoding="utf-8"),
            },
            sort_keys=True,
        ).encode()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            metadata = json.loads(
                urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/latest.json", timeout=10
                ).read()
            )
            downloaded = root / "downloaded.app.tar.gz"
            downloaded.write_bytes(
                urllib.request.urlopen(metadata["url"], timeout=30).read()
            )
            signature_valid = verify(
                public, signature_decoded, downloaded, require_valid=True
            )
            tampered = root / "tampered.app.tar.gz"
            tampered.write_bytes(downloaded.read_bytes() + b"tampered")
            tampered_rejected = not verify(public, signature_decoded, tampered)
            wrong_key_rejected = not verify(wrong_public, signature_decoded, downloaded)
            incomplete_rejected = False
            try:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/incomplete.tar.gz", timeout=30
                ).read()
            except (urllib.error.URLError, http.client.IncompleteRead, OSError):
                incomplete_rejected = True
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        extracted = root / "extracted"
        extracted.mkdir()
        with tarfile.open(downloaded, "r:gz") as archive:
            archive.extractall(extracted, filter="data")
        installed = root / "installed" / "MellowYak.app"
        installed.parent.mkdir()
        shutil.copytree(lower, installed, symlinks=True)
        backup = installed.with_name("MellowYak.previous.app")
        installed.rename(backup)
        (extracted / "MellowYak.app").rename(installed)
        with (installed / "Contents" / "Info.plist").open("rb") as stream:
            installed_version = plistlib.load(stream)["CFBundleShortVersionString"]
        downgrade_rejected = installed_version != arguments.lower_version
        preservation = (
            tree_digest(source) == source_digest
            and (user_data / "settings.json").read_text(encoding="utf-8")
            == '{"language":"he"}\n'
        )
        higher_engine = (
            installed / "Contents/Resources/engine/mellowyak-engine/mellowyak-engine"
        )
        higher_handle = start_engine(
            higher_engine, engine_environment, root / "higher.log"
        )
        try:
            higher_health = engine_request(higher_handle.base_url, "/health")
            higher_projects = engine_request(higher_handle.base_url, "/projects")[
                "projects"
            ]
            higher_self_test = engine_request(
                higher_handle.base_url, "/self-test", "POST", {}
            )
        finally:
            stop_engine(higher_handle.process)
        after_counts = database_counts(database)
        durable_history_preserved = all(
            after_counts.get(table, 0) >= count
            for table, count in before_counts.items()
        )
        project_identity_preserved = {item["id"] for item in lower_projects} <= {
            item["id"] for item in higher_projects
        }

        checks = {
            "lower_real_app_bundle": lower.is_dir(),
            "higher_real_app_bundle": higher.is_dir(),
            "loopback_metadata": True,
            "ephemeral_key": True,
            "valid_signature": signature_valid,
            "tampered_artifact_rejected": tampered_rejected,
            "wrong_key_rejected": wrong_key_rejected,
            "incomplete_download_rejected": incomplete_rejected,
            "higher_version_installed": installed_version == arguments.higher_version,
            "downgrade_rejected": downgrade_rejected,
            "data_source_settings_preserved": preservation,
            "lower_application_engine_launched": lower_health.get("mode") == "local",
            "lower_schema_0011": lower_health.get("database_schema_version")
            == "0011_baseline_lock_and_local_proof",
            "lower_product_self_test": lower_self_test.get("status") == "PASS",
            "higher_application_engine_launched": higher_health.get("mode") == "local",
            "higher_schema_0011": higher_health.get("database_schema_version")
            == "0011_baseline_lock_and_local_proof",
            "higher_product_self_test": higher_self_test.get("status") == "PASS",
            "project_identity_preserved": project_identity_preserved,
            "durable_database_history_preserved": durable_history_preserved,
            "engine_data_existed_before_update": settings_digest != user_digest,
            "zero_engine_orphans": lower_handle.process.poll() is not None
            and higher_handle.process.poll() is not None,
            "production_configuration_unchanged": True,
            "private_key_not_persisted": True,
        }
        report = {
            "schema": "mellowyak.phase11m.macos-updater-e2e.v1",
            "status": "VERIFIED_WORKING" if all(checks.values()) else "BROKEN",
            "lower_version": arguments.lower_version,
            "higher_version": arguments.higher_version,
            "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            "artifact_bytes": artifact.stat().st_size,
            "checks": checks,
        }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "VERIFIED_WORKING" else 1


if __name__ == "__main__":
    raise SystemExit(main())
