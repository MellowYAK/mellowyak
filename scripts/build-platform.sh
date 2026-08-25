#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repository_root"

platform="${1:-}"
release_updater="${2:-}"
case "$platform" in
  macos-intel|macos-apple-silicon) bundles="app,dmg" ;;
  linux-x64) bundles="appimage,deb" ;;
  *) echo "Usage: $0 {macos-intel|macos-apple-silicon|linux-x64} [--release-updater]" >&2; exit 2 ;;
esac

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "Tracked source is dirty. Commit the shared source before producing a platform artifact." >&2
  exit 1
fi

python_bin="engine/.venv/bin/python"
[[ -x "$python_bin" ]] || { echo "Run the platform bootstrap first." >&2; exit 1; }

"$python_bin" scripts/export_openapi.py
npm --prefix apps/desktop run contract:generate
python3 scripts/check_ui_translation_keys.py
npm --prefix apps/desktop run typecheck
"$python_bin" scripts/stage_browser.py
"$python_bin" scripts/build_engine.py

tauri_args=(run tauri build -- --bundles "$bundles")
if [[ "$release_updater" == "--release-updater" ]]; then
  tauri_args+=(--config src-tauri/tauri.release.conf.json)
fi
npm --prefix apps/desktop "${tauri_args[@]}"

mkdir -p build-manifest
"$python_bin" scripts/write_artifact_manifest.py \
  --root apps/desktop/src-tauri/target/release/bundle \
  --output "build-manifest/${platform}-artifacts.json" \
  --platform "$platform" \
  --commit "$(git rev-parse HEAD)" \
  --validation-status NOT_RUN

echo "Built $platform from $(git rev-parse HEAD). Runtime acceptance remains NOT_RUN."
