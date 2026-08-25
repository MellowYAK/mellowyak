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
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notifications_muted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    project_type: Mapped[str] = mapped_column(String(40), nullable=False, default="OTHER")
    runtime_setup_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="INCOMPLETE"
    )
    observation_level: Mapped[str] = mapped_column(String(40), nullable=False, default="LIGHT")
    snapshot_retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    snapshot_soft_cap_bytes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5 * 1024 * 1024 * 1024
    )


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
    always_recheck: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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
    bundle_type: Mapped[str] = mapped_column(String(40), nullable=False, default="BASELINE_CAPTURE")
    verification_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
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


class ProtectionPlan(Base):
    __tablename__ = "protection_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    change_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("project_changes.id"), nullable=False
    )
    impact_analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("impact_analyses.id"), nullable=False
    )
    source_identity_json: Mapped[str] = mapped_column(Text, nullable=False)
    binding_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(40), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stale_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    required_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    suggested_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    needs_review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unknown_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ProtectionPlanItem(Base):
    __tablename__ = "protection_plan_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("protection_plans.id"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    behavior_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("protected_behaviors.id"), nullable=False
    )
    behavior_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("behavior_versions.id"), nullable=False
    )
    baseline_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    selection_class: Mapped[str] = mapped_column(String(40), nullable=False)
    selection_reason: Mapped[str] = mapped_column(Text, nullable=False)
    impact_path_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    strongest_provenance: Mapped[str] = mapped_column(String(40), nullable=False)
    relation_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stale_relation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    unknown_boundary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    criticality: Mapped[str] = mapped_column(String(20), nullable=False)
    verification_method: Mapped[str] = mapped_column(String(40), nullable=False)
    current_result_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    __table_args__ = (UniqueConstraint("plan_id", "behavior_id"),)


class VerificationRun(Base):
    __tablename__ = "verification_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    change_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("project_changes.id"), nullable=False
    )
    plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("protection_plans.id"), nullable=False
    )
    source_identity_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VerificationRunItem(Base):
    __tablename__ = "verification_run_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("verification_runs.id"), nullable=False
    )
    plan_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("protection_plan_items.id"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    behavior_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("protected_behaviors.id"), nullable=False
    )
    behavior_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("behavior_versions.id"), nullable=False
    )
    result: Mapped[str] = mapped_column(String(40), nullable=False, default="NOT_RUN")
    adapter: Mapped[str] = mapped_column(String(80), nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_bundle_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    limitations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("run_id", "plan_item_id"),)


class AssertionResult(Base):
    __tablename__ = "assertion_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    verification_run_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("verification_run_items.id"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    assertion_type: Mapped[str] = mapped_column(String(40), nullable=False)
    expected_json: Mapped[str] = mapped_column(Text, nullable=False)
    observed_json: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_references_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    adapter_version: Mapped[str] = mapped_column(String(40), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("verification_run_item_id", "ordinal"),)


class HumanVerificationAttestation(Base):
    __tablename__ = "human_verification_attestations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    verification_run_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("verification_run_items.id"), nullable=False, unique=True
    )
    installation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("installations.id"), nullable=False
    )
    result: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source_identity_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegressionFinding(Base):
    __tablename__ = "regression_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    change_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("project_changes.id"), nullable=False
    )
    behavior_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("protected_behaviors.id"), nullable=False
    )
    behavior_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("behavior_versions.id"), nullable=False
    )
    baseline_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    verification_run_item_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("verification_run_items.id"), nullable=True
    )
    probe_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    signal_classification_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    decision_reason: Mapped[str] = mapped_column(Text, nullable=False)
    source_identity_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolving_run_item_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class CompletionGateDecision(Base):
    __tablename__ = "completion_gate_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    change_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("project_changes.id"), nullable=False
    )
    plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("protection_plans.id"), nullable=False
    )
    verification_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    source_identity_json: Mapped[str] = mapped_column(Text, nullable=False)
    limitations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    decision_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RepairContext(Base):
    __tablename__ = "repair_contexts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    change_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("project_changes.id"), nullable=False
    )
    regression_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("regression_findings.id"), nullable=False
    )
    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    source_identity_json: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    digest: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    saved_relative_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RepairContextItem(Base):
    __tablename__ = "repair_context_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    repair_context_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repair_contexts.id"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    item_type: Mapped[str] = mapped_column(String(40), nullable=False)
    relative_reference: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class ReverificationLink(Base):
    __tablename__ = "reverification_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    regression_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("regression_findings.id"), nullable=False
    )
    previous_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("verification_runs.id"), nullable=False
    )
    current_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("verification_runs.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VerificationAuditEvent(Base):
    __tablename__ = "verification_audit_events"

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


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=True
    )
    change_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    behavior_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    regression_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    gate_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    title_key: Mapped[str] = mapped_column(String(160), nullable=False)
    summary_key: Mapped[str] = mapped_column(String(160), nullable=False)
    parameters_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    route_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    deduplication_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    native_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    regression_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    blocked_gate_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    needs_review_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    project_errors_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    verified_complete_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    regression_resolved_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    show_behavior_name: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    show_project_name: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    hide_details: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    critical_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectNotificationPreference(Base):
    __tablename__ = "project_notification_preferences"

    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), primary_key=True)
    muted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QuietModeState(Base):
    __tablename__ = "quiet_mode_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    until_turned_off: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ApplicationPreference(Base):
    __tablename__ = "application_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    keep_running_on_close: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    start_at_login: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectLifecycleEvent(Base):
    __tablename__ = "project_lifecycle_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectDisconnectionRecord(Base):
    __tablename__ = "project_disconnection_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    display_name: Mapped[str] = mapped_column(String(240), nullable=False)
    repository_identity_json: Mapped[str] = mapped_column(Text, nullable=False)
    disconnected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RuntimeProfile(Base):
    __tablename__ = "runtime_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(240), nullable=False)
    current_version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="CONFIGURED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("project_id", "display_name"),)


class RuntimeProfileVersion(Base):
    __tablename__ = "runtime_profile_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runtime_profiles.id"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    runtime_type: Mapped[str] = mapped_column(String(40), nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(40), nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    executable_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    argv_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    relative_working_directory: Mapped[str] = mapped_column(Text, nullable=False, default=".")
    runtime_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    dependency_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    health_definition_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    expected_ports_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    test_definitions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    environment_schema_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    network_policy: Mapped[str] = mapped_column(String(40), nullable=False, default="LOOPBACK_ONLY")
    limitations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("profile_id", "version_number"),)


class RuntimeDetection(Base):
    __tablename__ = "runtime_detections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    candidates_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)


class RuntimeInstance(Base):
    __tablename__ = "runtime_instances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runtime_profiles.id"), nullable=False
    )
    profile_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runtime_profile_versions.id"), nullable=False
    )
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    process_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sanitized_observation_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class SourceEpisode(Base):
    __tablename__ = "source_episodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    added_paths_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    modified_paths_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    deleted_paths_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    renamed_paths_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    dependency_changes_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    runtime_events_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    base_snapshot_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resulting_snapshot_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    git_anchor_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="OPEN")
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)


class SourceSnapshot(Base):
    __tablename__ = "source_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    parent_snapshot_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    episode_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    creation_reason: Mapped[str] = mapped_column(String(40), nullable=False)
    source_identity_json: Mapped[str] = mapped_column(Text, nullable=False)
    git_anchor_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    runtime_profile_fingerprints_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]"
    )
    included_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    excluded_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sensitive_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unsupported_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    logical_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    physical_bytes_added: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reused_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    integrity_status: Mapped[str] = mapped_column(String(40), nullable=False, default="VERIFIED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("project_id", "manifest_digest"),)


class SnapshotEntry(Base):
    __tablename__ = "snapshot_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("source_snapshots.id"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    blob_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_mode: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    executable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    symlink_target: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification: Mapped[str] = mapped_column(String(40), nullable=False)

    __table_args__ = (UniqueConstraint("snapshot_id", "relative_path"),)


class SnapshotObject(Base):
    __tablename__ = "snapshot_objects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    digest: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    object_relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    reference_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    integrity_status: Mapped[str] = mapped_column(String(40), nullable=False, default="VERIFIED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (UniqueConstraint("project_id", "digest"),)


class SnapshotMilestone(Base):
    __tablename__ = "snapshot_milestones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    snapshot_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("source_snapshots.id"), nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(240), nullable=False)
    behavior_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    behavior_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    probe_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    runtime_profile_versions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    evidence_bundle_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    environment_summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    limitations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    human_attested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProbeDefinition(Base):
    __tablename__ = "probe_definitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    behavior_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    display_name: Mapped[str] = mapped_column(String(240), nullable=False)
    probe_type: Mapped[str] = mapped_column(String(40), nullable=False)
    current_version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="CONFIGURED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProbeVersion(Base):
    __tablename__ = "probe_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    probe_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("probe_definitions.id"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    runtime_profile_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    definition_json: Mapped[str] = mapped_column(Text, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    retry_policy_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    expected_result_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    evidence_policy_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    source_links_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    runtime_links_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("probe_id", "version_number"),)


class ProbeRun(Base):
    __tablename__ = "probe_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    probe_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("probe_definitions.id"), nullable=False
    )
    probe_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("probe_versions.id"), nullable=False
    )
    snapshot_id: Mapped[str] = mapped_column(String(64), nullable=False)
    episode_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    runtime_profile_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_identity_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    result: Mapped[str] = mapped_column(String(40), nullable=False, default="NOT_RUN")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expected_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    observed_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    limitations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    reproducible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RuntimeEvent(Base):
    __tablename__ = "runtime_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    profile_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    instance_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    episode_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    sanitized_details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SignalClassification(Base):
    __tablename__ = "signal_classifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    episode_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    snapshot_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    probe_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    regression_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    reason_codes_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    friendly_key: Mapped[str] = mapped_column(String(160), nullable=False)
    technical_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RepairWorkspace(Base):
    __tablename__ = "repair_workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    regression_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    signal_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    snapshot_id: Mapped[str] = mapped_column(String(64), nullable=False)
    workspace_relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    base_manifest_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    workspace_manifest_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    runtime_profile_versions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    validation_policy_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_change_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RepairWorkspaceItem(Base):
    __tablename__ = "repair_workspace_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repair_workspaces.id"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    item_type: Mapped[str] = mapped_column(String(40), nullable=False)
    relative_reference: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (UniqueConstraint("workspace_id", "ordinal"),)


class RepairCandidate(Base):
    __tablename__ = "repair_candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repair_workspaces.id"), nullable=False
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    base_manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    workspace_manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    source_snapshot_id: Mapped[str] = mapped_column(String(64), nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    logical_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    binary_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    limitations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("workspace_id", "revision"),)


class RepairCandidateFile(Base):
    __tablename__ = "repair_candidate_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repair_candidates.id"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    operation: Mapped[str] = mapped_column(String(24), nullable=False)
    base_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    candidate_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expected_live_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    classification: Mapped[str] = mapped_column(String(20), nullable=False)
    file_mode: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    executable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rename_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    rename_destination: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    apply_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    exclusion_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    warning_state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    excluded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("candidate_id", "ordinal"),
        UniqueConstraint("candidate_id", "relative_path"),
    )


class RepairCandidateValidation(Base):
    __tablename__ = "repair_candidate_validations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repair_candidates.id"), nullable=False
    )
    candidate_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    workspace_manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    runtime_profile_versions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    limitations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")


class RepairCandidateValidationItem(Base):
    __tablename__ = "repair_candidate_validation_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    validation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repair_candidate_validations.id"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    check_type: Mapped[str] = mapped_column(String(40), nullable=False)
    requirement: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    result: Mapped[str] = mapped_column(String(40), nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)

    __table_args__ = (UniqueConstraint("validation_id", "ordinal"),)


class ApplyTransaction(Base):
    __tablename__ = "apply_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repair_candidates.id"), nullable=False
    )
    validation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repair_candidate_validations.id"), nullable=False
    )
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    expected_source_snapshot_id: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_source_manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    safety_snapshot_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    post_apply_snapshot_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confirmation_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    confirmation_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    confirmation_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    journal_relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApplyTransactionFile(Base):
    __tablename__ = "apply_transaction_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("apply_transactions.id"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    operation: Mapped[str] = mapped_column(String(24), nullable=False)
    operation_state: Mapped[str] = mapped_column(String(40), nullable=False)
    original_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    candidate_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    temporary_relative_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("transaction_id", "ordinal"),)


class ApplyJournalEvent(Base):
    __tablename__ = "apply_journal_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("apply_transactions.id"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("transaction_id", "sequence"),)


class RollbackRecord(Base):
    __tablename__ = "rollback_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("apply_transactions.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    restored_paths_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    unresolved_paths_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    verification_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RecoveryBundle(Base):
    __tablename__ = "recovery_bundles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("apply_transactions.id"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DemoLabRun(Base):
    __tablename__ = "demo_lab_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    root_relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    scenario: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    state_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProductSelfTestRun(Base):
    __tablename__ = "product_self_test_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    steps_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    report_relative_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
