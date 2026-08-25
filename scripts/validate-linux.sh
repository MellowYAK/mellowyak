#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repository_root"
expected_commit="${1:-$(git rev-parse HEAD)}"
lifecycle_status="${2:-SOURCE_PACKAGE_VERIFIED}"
if [[ "$lifecycle_status" == "--lifecycle-verified" ]]; then
  lifecycle_status="VERIFIED_WORKING"
fi
actual_commit="$(git rev-parse HEAD)"
[[ "$actual_commit" == "$expected_commit" ]] || { echo "Commit mismatch: expected $expected_commit, found $actual_commit" >&2; exit 1; }
[[ "$(uname -s)" == "Linux" ]] || { echo "Linux runtime acceptance must run on Linux." >&2; exit 1; }
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || { echo "Tracked tree is dirty." >&2; exit 1; }

python_bin="engine/.venv/bin/python"
"$python_bin" scripts/export_openapi.py
npm --prefix apps/desktop run contract:generate
python3 scripts/check_ui_translation_keys.py
npm --prefix apps/desktop run typecheck
cargo check --locked --manifest-path apps/desktop/src-tauri/Cargo.toml

bundle_root="apps/desktop/src-tauri/target/release/bundle"
find "$bundle_root" -type f \( -name '*.AppImage' -o -name '*.deb' \) -print -quit | grep -q . || { echo "No Linux installer artifact found." >&2; exit 1; }

mkdir -p build-manifest
"$python_bin" scripts/write_artifact_manifest.py --root "$bundle_root" --output build-manifest/linux-x64-artifacts.json --platform linux-x64 --commit "$actual_commit" --validation-status "$lifecycle_status"
echo "Linux acceptance status $lifecycle_status recorded for $actual_commit. Use --lifecycle-verified only after the documented native lifecycle succeeds."
