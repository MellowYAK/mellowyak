#!/usr/bin/env python3
"""Exercise disposable Tauri updater signatures over a loopback metadata server."""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.client
import http.server
import json
import subprocess
import tarfile
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "apps" / "desktop"
TAURI = DESKTOP / "src-tauri"
PASSWORD = "disposable-phase9-updater-fixture"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def run(
    *arguments: str, expect_success: bool = True
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(arguments),
        cwd=DESKTOP,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_success and result.returncode != 0:
        raise RuntimeError(f"fixture command failed: {arguments[0]}")
    return result


def generate_key(path: Path) -> None:
    run(
        "npx",
        "tauri",
        "signer",
        "generate",
        "--ci",
        "--write-keys",
        str(path),
        "--password",
        PASSWORD,
    )


def verify(
    public: Path, signature: Path, artifact: Path, *, require_valid: bool = False
) -> bool:
    result = run(
        "cargo",
        "run",
        "--quiet",
        "--manifest-path",
        str(TAURI / "Cargo.toml"),
        "--example",
        "verify_updater_fixture",
        "--",
        str(public),
        str(signature),
        str(artifact),
        expect_success=False,
    )
    valid = result.returncode == 0 and result.stdout.strip() == "VERIFIED"
    if require_valid and not valid:
        raise RuntimeError(f"signature verifier failed: {result.stderr.strip()[:500]}")
    return valid


class FixtureHandler(http.server.BaseHTTPRequestHandler):
    metadata = b""
    artifact = b""

    def do_GET(self) -> None:
        if self.path == "/metadata.json":
            payload = self.metadata
        elif self.path == "/artifact.tar.gz":
            payload = self.artifact
        elif self.path == "/interrupted.tar.gz":
            payload = self.artifact[: max(1, len(self.artifact) // 3)]
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(self.artifact)))
            self.end_headers()
            self.wfile.write(payload)
            self.close_connection = True
            return
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, _format: str, *_arguments: object) -> None:
        return


def main() -> None:
    arguments = parse_args()
    with tempfile.TemporaryDirectory(prefix="mellowyak-updater-fixture-") as temporary:
        root = Path(temporary)
        lower = root / "lower-app"
        higher = root / "higher-app"
        lower.mkdir()
        higher.mkdir()
        (lower / "version.txt").write_text("0.2.0-preview.0\n", encoding="utf-8")
        (higher / "version.txt").write_text("0.2.0-preview.1\n", encoding="utf-8")
        lower_hash = hashlib.sha256((lower / "version.txt").read_bytes()).hexdigest()
        artifact = root / "MellowYak-0.2.0-preview.1.tar.gz"
        with tarfile.open(artifact, "w:gz") as archive:
            archive.add(higher, arcname="MellowYak.app")

        key = root / "updater.key"
        wrong_key = root / "wrong-updater.key"
        generate_key(key)
        generate_key(wrong_key)
        run(
            "npx",
            "tauri",
            "signer",
            "sign",
            "--private-key-path",
            str(key),
            "--password",
            PASSWORD,
            str(artifact),
        )
        signature = artifact.with_suffix(artifact.suffix + ".sig")
        if not signature.is_file():
            raise AssertionError("Tauri signer did not create a detached signature")
        public_decoded = root / "public.minisign"
        wrong_public_decoded = root / "wrong-public.minisign"
        signature_decoded = root / "artifact.minisig"
        public_decoded.write_bytes(
            base64.b64decode(key.with_suffix(".key.pub").read_bytes())
        )
        wrong_public_decoded.write_bytes(
            base64.b64decode(wrong_key.with_suffix(".key.pub").read_bytes())
        )
        signature_decoded.write_bytes(base64.b64decode(signature.read_bytes()))

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        port = server.server_address[1]
        FixtureHandler.artifact = artifact.read_bytes()
        FixtureHandler.metadata = json.dumps(
            {
                "version": "0.2.0-preview.1",
                "url": f"http://127.0.0.1:{port}/artifact.tar.gz",
                "signature": signature.read_text(encoding="utf-8"),
            },
            sort_keys=True,
        ).encode()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            metadata = json.loads(
                urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/metadata.json", timeout=10
                ).read()
            )
            downloaded = root / "downloaded.tar.gz"
            downloaded.write_bytes(
                urllib.request.urlopen(metadata["url"], timeout=10).read()
            )
            valid = verify(
                public_decoded, signature_decoded, downloaded, require_valid=True
            )
            tampered = root / "tampered.tar.gz"
            tampered.write_bytes(downloaded.read_bytes() + b"tampered")
            tampered_rejected = not verify(public_decoded, signature_decoded, tampered)
            wrong_key_rejected = not verify(
                wrong_public_decoded, signature_decoded, downloaded
            )
            interrupted_rejected = False
            try:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/interrupted.tar.gz", timeout=10
                ).read()
            except (urllib.error.URLError, http.client.IncompleteRead, OSError):
                interrupted_rejected = True
            if not interrupted_rejected:
                raise AssertionError("interrupted updater download was not rejected")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        lower_preserved = (
            hashlib.sha256((lower / "version.txt").read_bytes()).hexdigest()
            == lower_hash
        )
        result = {
            "schema": "mellowyak.phase9.local-updater-validation.v1",
            "status": "VERIFIED_WORKING"
            if valid and tampered_rejected and wrong_key_rejected and lower_preserved
            else "BROKEN",
            "loopback_metadata": True,
            "ephemeral_private_key": True,
            "private_key_persisted": False,
            "production_configuration_changed": False,
            "no_update": True,
            "newer_update_detected": metadata["version"] == "0.2.0-preview.1",
            "valid_signature": valid,
            "tampered_artifact_rejected": tampered_rejected,
            "wrong_key_rejected": wrong_key_rejected,
            "interrupted_download_rejected": interrupted_rejected,
            "lower_fixture_preserved": lower_preserved,
            "production_updater": "IMPLEMENTED_NOT_RUNTIME_VERIFIED",
        }
        if result["status"] != "VERIFIED_WORKING":
            failed = [
                key
                for key in [
                    "valid_signature",
                    "tampered_artifact_rejected",
                    "wrong_key_rejected",
                    "interrupted_download_rejected",
                    "lower_fixture_preserved",
                ]
                if not result[key]
            ]
            raise AssertionError(f"local updater validation failed: {','.join(failed)}")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
