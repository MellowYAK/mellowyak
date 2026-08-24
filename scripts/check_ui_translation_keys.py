#!/usr/bin/env python3
"""Reject static user-facing JSX text outside the translation catalog."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "apps" / "desktop" / "src"
CATALOG = SOURCE / "i18n.ts"
DIRECT_TEXT = re.compile(r"<[A-Za-z][^>]*>([^<>{}]*[A-Za-z\u0590-\u05ff][^<>{}]*)</")
HARDCODED_ATTRIBUTE = re.compile(r"\b(?:alt|aria-label|placeholder|title)\s*=\s*[\"']")
CATALOG_KEY = re.compile(r'^\s*"([A-Za-z0-9_.-]+)":', re.MULTILINE)


def catalog_keys(source: str, start: str, end: str) -> list[str]:
    block = source.split(start, 1)[1].split(end, 1)[0]
    return CATALOG_KEY.findall(block)


def main() -> None:
    violations: list[str] = []
    catalog = CATALOG.read_text(encoding="utf-8")
    english = catalog_keys(catalog, "const en = {", "} as const;")
    hebrew = catalog_keys(catalog, "const he:", "};\n\nconst dictionaries")
    if len(english) != len(set(english)):
        violations.append("apps/desktop/src/i18n.ts:duplicate English translation key")
    if len(hebrew) != len(set(hebrew)):
        violations.append("apps/desktop/src/i18n.ts:duplicate Hebrew translation key")
    missing_hebrew = sorted(set(english) - set(hebrew))
    extra_hebrew = sorted(set(hebrew) - set(english))
    if missing_hebrew:
        violations.append(
            f"apps/desktop/src/i18n.ts:missing Hebrew keys: {missing_hebrew}"
        )
    if extra_hebrew:
        violations.append(
            f"apps/desktop/src/i18n.ts:unknown Hebrew keys: {extra_hebrew}"
        )
    for path in sorted(SOURCE.rglob("*.tsx")):
        if path.name.endswith(".test.tsx"):
            continue
        source = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(source.splitlines(), 1):
            if DIRECT_TEXT.search(line) or HARDCODED_ATTRIBUTE.search(line):
                violations.append(
                    f"{path.relative_to(ROOT)}:{line_number}:{line.strip()}"
                )
    if violations:
        raise SystemExit("Hardcoded UI text found:\n" + "\n".join(violations))
    print("UI_TRANSLATION_KEYS_ONLY")


if __name__ == "__main__":
    main()
