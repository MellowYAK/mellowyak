#!/usr/bin/env python3
"""Immutable Phase 14M public-project corpus metadata (no source redistribution)."""

from __future__ import annotations

from typing import Final

PUBLIC_PROJECTS: Final[tuple[dict[str, object], ...]] = (
    {
        "alias": "datasette",
        "url": "https://github.com/simonw/datasette",
        "commit": "0337fba234bf574629d56be631468ea060495fa0",
        "license": "Apache-2.0",
        "purpose": "Local data exploration and publishing application",
        "roles": ["PYTHON_PROJECT", "APPLICATION", "GIT_LESS_FIXTURE_SOURCE"],
        "package_manager": "pip (unlocked project dependencies)",
        "official_sources": [
            "https://github.com/simonw/datasette",
            "https://docs.datasette.io/en/stable/installation.html",
        ],
    },
    {
        "alias": "excalidraw",
        "url": "https://github.com/excalidraw/excalidraw",
        "commit": "e1bb9ff8f8931e783c11d104abb8967ac6605c9a",
        "license": "MIT",
        "purpose": "Collaborative virtual whiteboard application and workspace",
        "roles": ["NODE_TYPESCRIPT_PROJECT", "APPLICATION", "WORKSPACE"],
        "package_manager": "Yarn 1.22.22",
        "official_sources": [
            "https://github.com/excalidraw/excalidraw",
            "https://github.com/excalidraw/excalidraw/blob/master/CONTRIBUTING.md",
        ],
    },
    {
        "alias": "vite",
        "url": "https://github.com/vitejs/vite",
        "commit": "493cc7d43269860fe499a30980d729b0adc93d2c",
        "license": "MIT",
        "purpose": "Frontend build tool monorepo with large realistic playground corpus",
        "roles": ["POLYGLOT_MONOREPO", "LARGE_PROJECT", "WORKSPACE"],
        "package_manager": "pnpm 10.34.5",
        "official_sources": [
            "https://github.com/vitejs/vite",
            "https://vite.dev/guide/",
        ],
    },
    {
        "alias": "tauri",
        "url": "https://github.com/tauri-apps/tauri",
        "commit": "5e2856e3209d4ab16d21a1f828ff94b46a35a0b6",
        "license": "MIT OR Apache-2.0",
        "purpose": "Rust and TypeScript desktop application framework monorepo",
        "roles": ["POLYGLOT_MONOREPO", "LARGE_PROJECT", "WORKSPACE"],
        "package_manager": "pnpm 11.21.0 and Cargo",
        "official_sources": [
            "https://github.com/tauri-apps/tauri",
            "https://v2.tauri.app/distribute/",
        ],
    },
)

REJECTED_PROJECTS: Final[tuple[dict[str, str], ...]] = (
    {
        "name": "Supabase",
        "url": "https://github.com/supabase/supabase",
        "reason": "The representative local stack normally requires Docker and multiple services.",
    },
    {
        "name": "Airbyte",
        "url": "https://github.com/airbytehq/airbyte",
        "reason": "The setup and service graph exceed this phase's bounded local acceptance scope.",
    },
    {
        "name": "Saleor",
        "url": "https://github.com/saleor/saleor",
        "reason": "Representative application execution requires external database/service setup.",
    },
)


def by_alias(alias: str) -> dict[str, object]:
    return next(item for item in PUBLIC_PROJECTS if item["alias"] == alias)
