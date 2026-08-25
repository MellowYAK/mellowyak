#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repository_root"

if [[ "${1:-}" == "--install-system" ]]; then
  sudo apt-get update
  sudo apt-get install -y build-essential curl git python3 python3-venv libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev patchelf
fi

for command in git python3 node npm rustup cargo; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "Missing required command: $command" >&2
    echo "Install Node.js 22, Python 3.12, Rustup, and the Tauri Linux prerequisites, or rerun with --install-system after Node and Rustup are available." >&2
    exit 1
  }
done

python3 -m venv engine/.venv
engine/.venv/bin/python -m pip install --upgrade pip
engine/.venv/bin/python -m pip install -e './engine[dev]'
npm ci --prefix apps/desktop
rustup toolchain install 1.98.0 --profile minimal --component rustfmt --component clippy
engine/.venv/bin/python -m playwright install --with-deps chromium
engine/.venv/bin/python scripts/export_openapi.py
npm --prefix apps/desktop run contract:generate

echo "Linux bootstrap complete for $(git rev-parse HEAD)."
