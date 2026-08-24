from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from dulwich import porcelain
from dulwich.diff_tree import tree_changes
from dulwich.errors import NotGitRepository
from dulwich.repo import Repo

from mellowyak_engine.scanning.policy import DEFAULT_EXCLUDED_DIRS, is_sensitive_path

_NON_GIT_EXCLUDED_DIRECTORIES = DEFAULT_EXCLUDED_DIRS | frozenset({".mellowyak-data"})
_NON_GIT_MAX_ENTRIES = 50_000


@dataclass(frozen=True)
class GitState:
    available: bool
    repository_root: str | None
    branch: str | None
    head_sha: str | None
    is_detached: bool
    is_dirty: bool
    staged: tuple[str, ...]
    unstaged: tuple[str, ...]
    untracked: tuple[str, ...]
    ignored_count: int
    worktree_fingerprint: str
    error: str | None = None

    def public_dict(self) -> dict[str, object]:
        value = asdict(self)
        value.pop("repository_root", None)
        return value


def _text_path(value: bytes | str) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="surrogateescape").replace("\\", "/")
    return str(value).replace("\\", "/")


def discover_repository(path: Path) -> Repo | None:
    try:
        return Repo.discover(str(path))
    except (NotGitRepository, FileNotFoundError, PermissionError):
        return None


def _non_git_worktree_fingerprint(root: Path) -> str:
    """Return a bounded watcher hint for projects that have no Git repository.

    This is intentionally metadata based: authoritative Phase 7 source identity is
    the content-addressed snapshot manifest.  The hint only makes polling notice
    additions, writes, renames, and deletions without reading source contents.
    """
    rows: list[tuple[str, int, int, int]] = []
    try:
        for current, directories, files in os.walk(root, topdown=True, followlinks=False):
            directories[:] = sorted(
                directory
                for directory in directories
                if directory not in _NON_GIT_EXCLUDED_DIRECTORIES
                and not (Path(current) / directory).is_symlink()
            )
            current_path = Path(current)
            for filename in sorted(files):
                candidate = current_path / filename
                if candidate.is_symlink():
                    continue
                try:
                    stat = candidate.stat()
                    relative = candidate.relative_to(root).as_posix()
                except (OSError, ValueError):
                    continue
                rows.append((relative, stat.st_size, stat.st_mtime_ns, stat.st_mode))
                if len(rows) >= _NON_GIT_MAX_ENTRIES:
                    break
            if len(rows) >= _NON_GIT_MAX_ENTRIES:
                break
    except OSError:
        rows.append(("UNREADABLE", 0, 0, 0))
    canonical = json.dumps(rows, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8", errors="surrogatepass")).hexdigest()


def _working_hash(root: Path, relative_path: str) -> str:
    if ".mellowyak-data" in Path(relative_path).parts or is_sensitive_path(relative_path):
        return "SENSITIVE_EXCLUDED"
    candidate = (root / relative_path).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError:
        return "OUTSIDE_ROOT"
    if not candidate.is_file():
        return "DELETED"
    digest = hashlib.sha256()
    try:
        with candidate.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except (OSError, PermissionError):
        return "UNREADABLE"
    return digest.hexdigest()


def observe_git(path: Path) -> GitState:
    selected = path.expanduser().resolve(strict=True)
    repo = discover_repository(selected)
    if repo is None:
        fingerprint = _non_git_worktree_fingerprint(selected)
        return GitState(
            available=False,
            repository_root=None,
            branch=None,
            head_sha=None,
            is_detached=False,
            is_dirty=False,
            staged=(),
            unstaged=(),
            untracked=(),
            ignored_count=0,
            worktree_fingerprint=fingerprint,
            error="GIT_UNAVAILABLE",
        )

    root = Path(repo.path).resolve()
    if repo.bare:
        return GitState(
            available=False,
            repository_root=str(root),
            branch=None,
            head_sha=None,
            is_detached=False,
            is_dirty=False,
            staged=(),
            unstaged=(),
            untracked=(),
            ignored_count=0,
            worktree_fingerprint=hashlib.sha256(b"BARE_REPOSITORY").hexdigest(),
            error="BARE_REPOSITORY_UNSUPPORTED",
        )

    root = Path(repo.path).resolve()
    status = porcelain.status(repo, ignored=True, untracked_files="all")
    staged_by_class = {
        change_class: tuple(sorted(_text_path(item) for item in items))
        for change_class, items in status.staged.items()
    }
    staged = tuple(
        sorted(
            f"{change_class}:{path}"
            for change_class, paths in staged_by_class.items()
            for path in paths
        )
    )
    unstaged = tuple(sorted(_text_path(item) for item in status.unstaged))
    untracked = tuple(sorted(_text_path(item) for item in status.untracked))

    try:
        head_sha = repo.head().decode("ascii")
    except KeyError:
        head_sha = None
    raw_head_ref = repo.refs.read_ref(b"HEAD")
    head_ref = (
        raw_head_ref.removeprefix(b"ref: ")
        if raw_head_ref and raw_head_ref.startswith(b"ref: ")
        else None
    )
    is_detached = bool(raw_head_ref and head_ref is None)
    branch = None
    if head_ref and head_ref.startswith(b"refs/heads/"):
        branch = head_ref.removeprefix(b"refs/heads/").decode("utf-8", errors="replace")

    index = repo.open_index()
    fingerprint_items: list[dict[str, str]] = [
        {"class": "HEAD", "path": "", "digest": head_sha or "UNBORN"}
    ]
    for item in staged:
        change_class, relative = item.split(":", 1)
        try:
            index_entry = index[relative.encode()]
        except KeyError:
            index_entry = None
        digest = index_entry.sha.decode("ascii") if index_entry else "DELETED"
        fingerprint_items.append(
            {"class": f"STAGED_{change_class.upper()}", "path": relative, "digest": digest}
        )
    for change_class, paths in (("UNSTAGED", unstaged), ("UNTRACKED", untracked)):
        for relative in paths:
            fingerprint_items.append(
                {"class": change_class, "path": relative, "digest": _working_hash(root, relative)}
            )
    canonical = json.dumps(fingerprint_items, sort_keys=True, separators=(",", ":"))
    fingerprint = hashlib.sha256(canonical.encode()).hexdigest()
    return GitState(
        available=True,
        repository_root=str(root),
        branch=branch,
        head_sha=head_sha,
        is_detached=is_detached,
        is_dirty=bool(staged or unstaged or untracked),
        staged=staged,
        unstaged=unstaged,
        untracked=untracked,
        ignored_count=0,
        worktree_fingerprint=fingerprint,
    )


def committed_changed_paths(
    path: Path, base_sha: str | None, head_sha: str | None
) -> tuple[str, ...]:
    """Return a deterministic, read-only tree delta without invoking Git commands."""
    if not base_sha or not head_sha or base_sha == head_sha:
        return ()
    repo = discover_repository(path.expanduser().resolve(strict=True))
    if repo is None or repo.bare:
        return ()
    try:
        base = repo[base_sha.encode("ascii")]
        head = repo[head_sha.encode("ascii")]
        changes = tree_changes(repo.object_store, base.tree, head.tree)
        paths = {
            _text_path(entry.path)
            for change in changes
            for entry in (change.old, change.new)
            if entry is not None and entry.path is not None
        }
        return tuple(sorted(paths))
    except (KeyError, ValueError, TypeError):
        return ()
