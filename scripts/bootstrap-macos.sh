#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repository_root"

for command in git python3 node npm rustup cargo; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "Missing required command: $command" >&2
    exit 1
  }
done

python3 -m venv engine/.venv
engine/.venv/bin/python -m pip install --upgrade pip
engine/.venv/bin/python -m pip install -e './engine[dev]'
npm ci --prefix apps/desktop
rustup toolchain install 1.98.0 --profile minimal --component rustfmt --component clippy
engine/.venv/bin/python -m playwright install chromium
engine/.venv/bin/python scripts/export_openapi.py
npm --prefix apps/desktop run contract:generate

echo "macOS bootstrap complete for $(git rev-parse HEAD)."
