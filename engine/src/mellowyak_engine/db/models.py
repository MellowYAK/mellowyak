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


class ProjectChange(Base):
    __tablename__ = "project_changes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    logical_key: Mapped[str] = mapped_column(String(64), nullable=False)
    change_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    base_head_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    head_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    worktree_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    changed_paths_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    task_intent: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="change_detected")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("project_id", "logical_key"),)


class ImpactAnalysis(Base):
    __tablename__ = "impact_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    change_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("project_changes.id"), nullable=False
    )
    analysis_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    base_head_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    head_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    worktree_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    scan_revision: Mapped[str | None] = mapped_column(String(36), nullable=True)
    algorithm_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    changed_file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    impacted_node_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unknown_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stale_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    heuristic_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    truncation_reasons_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stale_reasons_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("project_id", "change_id", "analysis_revision"),)


class ImpactAnalysisInput(Base):
    __tablename__ = "impact_analysis_inputs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("impact_analyses.id"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    changed_files_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    task_intent: Mapped[str | None] = mapped_column(Text, nullable=True)
    traversal_policy_json: Mapped[str] = mapped_column(Text, nullable=False)


class ImpactAnalysisResult(Base):
    __tablename__ = "impact_analysis_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("impact_analyses.id"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    node_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("impact_nodes.id"), nullable=True
    )
    node_type: Mapped[str] = mapped_column(String(40), nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    relative_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact_class: Mapped[str] = mapped_column(String(40), nullable=False)
    minimum_depth: Mapped[int] = mapped_column(Integer, nullable=False)
    strongest_provenance: Mapped[str] = mapped_column(String(40), nullable=False)
    stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    unknown: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    path_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ranking_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    ranking_reasons_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    unknown_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class ImpactAnalysisPath(Base):
    __tablename__ = "impact_analysis_paths"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("impact_analyses.id"), nullable=False
    )
    result_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("impact_analysis_results.id"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    depth: Mapped[int] = mapped_column(Integer, nullable=False)
    path_json: Mapped[str] = mapped_column(Text, nullable=False)


class ContextReceipt(Base):
    __tablename__ = "context_receipts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    change_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("project_changes.id"), nullable=False
    )
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("impact_analyses.id"), nullable=False
    )
    receipt_key: Mapped[str] = mapped_column(String(64), nullable=False)
    request_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_revision_json: Mapped[str] = mapped_column(Text, nullable=False)
    constraints_json: Mapped[str] = mapped_column(Text, nullable=False)
    unknowns_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    excluded_context_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    relationship_paths_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    size_metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
    truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("project_id", "receipt_key"),)


class ContextReceiptItem(Base):
    __tablename__ = "context_receipt_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    receipt_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("context_receipts.id"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    item_type: Mapped[str] = mapped_column(String(40), nullable=False)
    reason_selected: Mapped[str] = mapped_column(Text, nullable=False)
    relationship_provenance: Mapped[str] = mapped_column(String(40), nullable=False)
    relevance_class: Mapped[str] = mapped_column(String(40), nullable=False)
    stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    selection_reasons_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")


class BehaviorCandidate(Base):
    __tablename__ = "behavior_candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_key: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="CANDIDATE")
    evidence_state: Mapped[str] = mapped_column(String(40), nullable=False, default="none")
    verification_state: Mapped[str] = mapped_column(
        String(40), nullable=False, default="not_configured"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    kept_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("project_id", "source_type", "source_key"),)


class BehaviorCandidateLink(Base):
    __tablename__ = "behavior_candidate_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    behavior_candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("behavior_candidates.id"), nullable=False
    )
    change_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("project_changes.id"), nullable=True
    )
    impact_node_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("impact_nodes.id"), nullable=True
    )
    relation_type: Mapped[str] = mapped_column(String(40), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "project_id", "behavior_candidate_id", "change_id", "impact_node_id", "relation_type"
        ),
    )


class ProtectedBehavior(Base):
    __tablename__ = "protected_behaviors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    stable_key: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT")
    current_version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    last_accepted_baseline_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("project_id", "stable_key"),)


class BehaviorVersion(Base):
    __tablename__ = "behavior_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    behavior_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("protected_behaviors.id"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    expected_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    criticality: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    preconditions: Mapped[str] = mapped_column(Text, nullable=False, default="")
    starting_state: Mapped[str] = mapped_column(Text, nullable=False, default="")
    environment_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    persona: Mapped[str] = mapped_column(Text, nullable=False, default="")
    runtime_configuration_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    expected_assertions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    limitations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    verification_not_configured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_type: Mapped[str] = mapped_column(String(40), nullable=False, default="HUMAN")
    source_candidate_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    content_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    supersedes_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_revision_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("behavior_id", "version_number"),)


class BehaviorLink(Base):
    __tablename__ = "behavior_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    behavior_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("protected_behaviors.id"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    link_type: Mapped[str] = mapped_column(String(40), nullable=False)
    link_key: Mapped[str] = mapped_column(Text, nullable=False)
    provenance: Mapped[str] = mapped_column(String(40), nullable=False, default="HUMAN_CONFIRMED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("behavior_id", "link_type", "link_key"),)


class RuntimeConfiguration(Base):
    __tablename__ = "runtime_configurations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_origin: Mapped[str] = mapped_column(Text, nullable=False)
    starting_path: Mapped[str] = mapped_column(Text, nullable=False, default="/")
    viewport_width: Mapped[int] = mapped_column(Integer, nullable=False, default=1280)
    viewport_height: Mapped[int] = mapped_column(Integer, nullable=False, default=800)
    locale: Mapped[str] = mapped_column(String(40), nullable=False, default="en-US")
    timezone: Mapped[str] = mapped_column(String(80), nullable=False, default="UTC")
    browser_type: Mapped[str] = mapped_column(String(40), nullable=False, default="chromium")
    capture_screenshots: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    capture_trace: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    capture_video: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    capture_network: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("project_id", "allowed_origin"),)


class BrowserCaptureSession(Base):
    __tablename__ = "browser_capture_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    behavior_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("protected_behaviors.id"), nullable=False
    )
    behavior_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("behavior_versions.id"), nullable=False
    )
    runtime_configuration_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runtime_configurations.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    entry_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_revision_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    browser_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    runtime_identity_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    expected_assertions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")


class BrowserCaptureStep(Base):
    __tablename__ = "browser_capture_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    capture_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("browser_capture_sessions.id"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    page_url: Mapped[str] = mapped_column(Text, nullable=False)
    selector: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    included: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    label: Mapped[str] = mapped_column(Text, nullable=False, default="")

    __table_args__ = (UniqueConstraint("capture_id", "ordinal"),)


class RuntimeObservation(Base):
    __tablename__ = "runtime_observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    capture_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("browser_capture_sessions.id"), nullable=False
    )
    observation_type: Mapped[str] = mapped_column(String(40), nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    included: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class EvidenceArtifact(Base):
    __tablename__ = "evidence_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    media_type: Mapped[str] = mapped_column(String(120), nullable=False)
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    redaction_state: Mapped[str] = mapped_column(String(40), nullable=False)
    capture_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    behavior_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    behavior_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_identity_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    runtime_identity_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    trust_source: Mapped[str] = mapped_column(String(40), nullable=False, default="LOCAL_CAPTURE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("project_id", "sha256"),)


class EvidenceBundle(Base):
    __tablename__ = "evidence_bundles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    capture_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("browser_capture_sessions.id"), nullable=False, unique=True
    )
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidenceBundleItem(Base):
    __tablename__ = "evidence_bundle_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    bundle_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_bundles.id"), nullable=False
    )
    artifact_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_artifacts.id"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    item_type: Mapped[str] = mapped_column(String(40), nullable=False)

    __table_args__ = (UniqueConstraint("bundle_id", "ordinal"),)


class BaselineAttestation(Base):
    __tablename__ = "baseline_attestations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    capture_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("browser_capture_sessions.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    reviewer: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BehaviorBaseline(Base):
    __tablename__ = "behavior_baselines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    behavior_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("protected_behaviors.id"), nullable=False
    )
    behavior_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("behavior_versions.id"), nullable=False
    )
    evidence_bundle_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_bundles.id"), nullable=False
    )
    attestation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("baseline_attestations.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    source_revision_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EvidenceAuditEvent(Base):
    __tablename__ = "evidence_audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(40), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
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
