from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from pathspec import GitIgnoreSpec

MAX_INDEXED_FILE_SIZE = 1_000_000
MAX_PARSER_PAYLOAD = 256_000
SCAN_WORKER_CONCURRENCY = 4
WATCHER_DEBOUNCE_MS = 800
SCAN_CANCELLATION_TIMEOUT_SECONDS = 5
SCAN_PROGRESS_EVERY_FILES = 20
MAX_STORED_PARSER_ITEMS = 2_000

DEFAULT_EXCLUDED_DIRS = frozenset(
    {
        ".aws",
        ".azure",
        ".claude",
        ".codex",
        ".cursor",
        ".git",
        ".gnupg",
        ".hg",
        ".idea",
        ".mcp",
        ".ssh",
        ".svn",
        ".vscode",
        ".venv",
        "venv",
        "node_modules",
        "vendor",
        "dist",
        "build",
        "target",
        "coverage",
        "htmlcov",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "__pycache__",
        "evidence",
    }
)

EXCLUDED_EXTENSIONS = frozenset(
    {
        ".appimage",
        ".deb",
        ".dmg",
        ".exe",
        ".msi",
        ".pkg",
        ".sqlite",
        ".sqlite3",
        ".db",
        ".pyc",
        ".class",
        ".o",
        ".so",
        ".dylib",
        ".dll",
    }
)

LANGUAGES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript JSX",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript TSX",
    ".json": "JSON",
    ".php": "PHP",
    ".css": "CSS",
    ".scss": "SCSS",
    ".html": "HTML",
    ".md": "Markdown",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".rb": "Ruby",
    ".sh": "Shell",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".toml": "TOML",
}

SUPPORTED_RELATIONSHIP_LANGUAGES = frozenset(
    {"Python", "JavaScript", "JavaScript JSX", "TypeScript", "TypeScript TSX", "PHP"}
)

SENSITIVE_NAMES = frozenset(
    {
        ".env",
        ".env.local",
        ".env.production",
        "credentials",
        "credentials.json",
        "secrets.json",
        "id_rsa",
        "id_ed25519",
        "known_hosts",
        ".npmrc",
        ".pypirc",
    }
)
SENSITIVE_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".crt", ".cer")


@dataclass(frozen=True)
class Candidate:
    absolute_path: Path
    relative_path: str
    symlink_outside: bool = False


def language_for(path: Path) -> str:
    return LANGUAGES.get(path.suffix.lower(), "Unknown")


def is_sensitive_path(relative_path: str) -> bool:
    path = Path(relative_path)
    lowered = path.name.lower()
    return (
        any(part.lower() in DEFAULT_EXCLUDED_DIRS for part in path.parts[:-1])
        or lowered in SENSITIVE_NAMES
        or lowered.startswith(".env.")
        or lowered.endswith(SENSITIVE_SUFFIXES)
        or "access_token" in lowered
        or "access-token" in lowered
        or "private_key" in lowered
    )


def is_test_path(relative_path: str) -> bool:
    lowered = relative_path.lower().replace("\\", "/")
    name = Path(lowered).name
    return (
        "/tests/" in f"/{lowered}"
        or "/test/" in f"/{lowered}"
        or name.startswith("test_")
        or name.endswith("_test.py")
        or ".test." in name
        or ".spec." in name
    )


def is_generated_path(relative_path: str) -> bool:
    lowered = relative_path.lower().replace("\\", "/")
    return any(
        segment in lowered.split("/")
        for segment in ("generated", "gen", "dist", "build", "coverage")
    ) or Path(lowered).name.endswith((".min.js", ".map"))


def build_ignore_spec(root: Path) -> GitIgnoreSpec:
    lines: list[str] = []
    for name in (".gitignore", ".mellowyakignore"):
        path = root / name
        if path.is_file() and not path.is_symlink():
            try:
                lines.extend(path.read_text(encoding="utf-8", errors="replace").splitlines())
            except OSError:
                continue
    return GitIgnoreSpec.from_lines(lines)


def iter_candidates(root: Path) -> tuple[list[Candidate], int]:
    root = root.resolve(strict=True)
    ignore = build_ignore_spec(root)
    candidates: list[Candidate] = []
    ignored_count = 0
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        relative_dir = current_path.relative_to(root).as_posix()
        retained: list[str] = []
        for directory in sorted(directories):
            relative = f"{relative_dir}/{directory}".lstrip("./")
            candidate = current_path / directory
            if directory in DEFAULT_EXCLUDED_DIRS or ignore.match_file(f"{relative}/"):
                ignored_count += 1
            elif candidate.is_symlink():
                ignored_count += 1
            else:
                retained.append(directory)
        directories[:] = retained
        for filename in sorted(files):
            absolute = current_path / filename
            relative = absolute.relative_to(root).as_posix()
            if ignore.match_file(relative):
                ignored_count += 1
                continue
            if absolute.suffix.lower() in EXCLUDED_EXTENSIONS:
                candidates.append(Candidate(absolute, relative))
                continue
            if absolute.is_symlink():
                try:
                    absolute.resolve(strict=False).relative_to(root)
                    candidates.append(Candidate(absolute, relative))
                except ValueError:
                    candidates.append(Candidate(absolute, relative, symlink_outside=True))
                continue
            candidates.append(Candidate(absolute, relative))
    return candidates, ignored_count
