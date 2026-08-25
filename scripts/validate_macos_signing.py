#!/usr/bin/env python3
"""Report macOS signing/notarization readiness without exposing credential values."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path


def run(*command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--dmg", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    identities = run("security", "find-identity", "-v", "-p", "codesigning").stdout
    identity_count = len(
        re.findall(r'^\s*\d+\)\s+[0-9A-F]{40}\s+"', identities, re.MULTILINE)
    )
    environment_ready = all(
        bool(os.environ.get(name, "").strip())
        for name in (
            "APPLE_CERTIFICATE",
            "APPLE_CERTIFICATE_PASSWORD",
            "APPLE_SIGNING_IDENTITY",
        )
    )
    app_verify = run(
        "codesign", "--verify", "--deep", "--strict", "--verbose=2", str(arguments.app)
    )
    details = run("codesign", "-dv", "--verbose=4", str(arguments.app)).stderr
    ad_hoc = "Signature=adhoc" in details or "TeamIdentifier=not set" in details
    gatekeeper = run(
        "spctl", "--assess", "--type", "execute", "--verbose=2", str(arguments.app)
    )
    stapled = run("xcrun", "stapler", "validate", str(arguments.app))
    credentials_available = identity_count > 0 and environment_ready
    report = {
        "schema": "mellowyak.phase11m.macos-signing.v1",
        "status": "VERIFIED_WORKING"
        if credentials_available
        and gatekeeper.returncode == 0
        and stapled.returncode == 0
        else "IMPLEMENTED_NOT_RUNTIME_VERIFIED",
        "credential_values_exposed": False,
        "developer_id_identity_count": identity_count,
        "required_environment_present": environment_ready,
        "codesign_structure_valid": app_verify.returncode == 0,
        "ad_hoc_signature": ad_hoc,
        "gatekeeper_accepted": gatekeeper.returncode == 0,
        "notarization_ticket_stapled": stapled.returncode == 0,
        "dmg_present": arguments.dmg.is_file(),
        "public_distribution_ready": credentials_available
        and gatekeeper.returncode == 0
        and stapled.returncode == 0,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
