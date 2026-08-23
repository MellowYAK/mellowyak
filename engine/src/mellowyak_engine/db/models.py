from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Installation(Base):
    __tablename__ = "installations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    app_version: Mapped[str] = mapped_column(String(40), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(40), nullable=False)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    installation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("installations.id"), nullable=True
    )
    display_name: Mapped[str] = mapped_column(String(240), nullable=False)
    # Kept for migration compatibility; always mirrors canonical_root_path.
    root_path: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_root_path: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    repository_root_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    monitoring_mode: Mapped[str] = mapped_column(String(40), nullable=False, default="passive")
    monitoring_status: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    active_scan_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    last_scan_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_branch: Mapped[str | None] = mapped_column(String(240), nullable=True)
    current_head_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_worktree_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detection_payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProjectGitSnapshot(Base):
    __tablename__ = "project_git_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    branch: Mapped[str | None] = mapped_column(String(240), nullable=True)
    head_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_detached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_dirty: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    staged_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unstaged_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    untracked_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ignored_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    worktree_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status_payload: Mapped[str] = mapped_column(Text, nullable=False)


class ProjectChangeObservation(Base):
    __tablename__ = "project_change_observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    previous_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    worktree_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    changed_paths_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    git_snapshot_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("project_git_snapshots.id"), nullable=False
    )

    __table_args__ = (UniqueConstraint("project_id", "worktree_fingerprint"),)


class ProjectScanRun(Base):
    __tablename__ = "project_scan_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    scan_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_candidates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    included_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    excluded_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    binary_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sensitive_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unknown_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unsupported_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    test_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    relationship_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProjectFile(Base):
    __tablename__ = "project_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_path: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(80), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_test: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_binary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    indexing_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    parser_adapter: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_seen_scan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("project_scan_runs.id"), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("project_id", "normalized_path"),)


class ImpactNode(Base):
    __tablename__ = "impact_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    node_type: Mapped[str] = mapped_column(String(40), nullable=False)
    stable_key: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    relative_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_seen_scan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("project_scan_runs.id"), nullable=False
    )
    stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (UniqueConstraint("project_id", "node_type", "stable_key"),)


class ImpactEdge(Base):
    __tablename__ = "impact_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    source_node_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("impact_nodes.id"), nullable=False
    )
    target_node_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("impact_nodes.id"), nullable=False
    )
    edge_type: Mapped[str] = mapped_column(String(40), nullable=False)
    provenance: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence_class: Mapped[str] = mapped_column(String(40), nullable=False)
    parser_adapter: Mapped[str] = mapped_column(String(80), nullable=False)
    source_scan_revision: Mapped[str] = mapped_column(String(36), nullable=False)
    first_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("project_id", "source_node_id", "target_node_id", "edge_type"),
    )


class ScanFinding(Base):
    __tablename__ = "scan_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    scan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("project_scan_runs.id"), nullable=False
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    relative_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EngineRun(Base):
    __tablename__ = "engine_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    installation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("installations.id"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
