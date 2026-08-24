from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True)
class SourceIdentityV2:
    """Exact local source identity shared by Git and non-Git projects."""

    kind: str
    snapshot_id: str
    manifest_digest: str
    episode_id: str | None = None
    parent_snapshot_id: str | None = None
    head_sha: str | None = None
    branch: str | None = None
    worktree_fingerprint: str | None = None

    @property
    def digest(self) -> str:
        return hashlib.sha256(_canonical(asdict(self)).encode()).hexdigest()

    def public_dict(self) -> dict[str, Any]:
        return {"schema": "mellowyak.source_identity.v2", **asdict(self), "digest": self.digest}


def source_identity(
    *,
    snapshot_id: str,
    manifest_digest: str,
    episode_id: str | None,
    parent_snapshot_id: str | None,
    git_available: bool,
    head_sha: str | None,
    branch: str | None,
    worktree_fingerprint: str | None,
) -> SourceIdentityV2:
    return SourceIdentityV2(
        kind="GIT_AND_SNAPSHOT" if git_available else "SNAPSHOT",
        snapshot_id=snapshot_id,
        manifest_digest=manifest_digest,
        episode_id=episode_id,
        parent_snapshot_id=parent_snapshot_id,
        head_sha=head_sha if git_available else None,
        branch=branch if git_available else None,
        worktree_fingerprint=worktree_fingerprint if git_available else None,
    )
