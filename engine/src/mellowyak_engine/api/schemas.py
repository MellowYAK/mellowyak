from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class HandshakeResponse(BaseModel):
    status: str
    mode: str
    authentication: str


class HealthResponse(BaseModel):
    status: str
    mode: str
    engine_version: str
    app_version: str
    database_status: str
    database_schema_version: str
    data_root: str
    cloud_connected: bool
    outbound_network_enabled: bool
    uptime_seconds: float


class ReadinessResponse(BaseModel):
    ready: bool
    checks: dict[str, bool]


class InstallationResponse(BaseModel):
    installation_id: str
    created_at: str
    last_started_at: str
    app_version: str
    engine_version: str
    database_schema_version: str


class PrivacySettingsResponse(BaseModel):
    mode: str
    cloud_connected: bool
    outbound_network_enabled: bool
    source_upload_enabled: bool
    telemetry_upload_enabled: bool
    account_required: bool


class StoragePathsResponse(BaseModel):
    data_root: str
    database: str
    evidence: str
    projects: str
    cache: str
    logs: str
    runtime: str
    backups: str


class OpenDataFolderResponse(BaseModel):
    opened: bool
    method: str


class GitStateResponse(BaseModel):
    available: bool
    branch: str | None
    head_sha: str | None
    is_detached: bool
    is_dirty: bool
    staged: list[str]
    unstaged: list[str]
    untracked: list[str]
    ignored_count: int
    worktree_fingerprint: str
    error: str | None = None


class ProjectDetectRequest(BaseModel):
    path: str


class ProjectDetectionResponse(BaseModel):
    selected_path: str
    repository_path: str
    suggested_name: str
    git: GitStateResponse
    languages: list[str]
    language_counts: dict[str, int]
    frameworks: list[str]
    tests: list[str]
    runtime_hints: list[str]
    candidate_files: int
    ignored_paths: int
    relationship_coverage: str
    unsupported_coverage: str
    source_remains_local: bool


class ProjectCreateRequest(BaseModel):
    path: str
    display_name: str
    monitoring_mode: str = "passive"


class ScanRunResponse(BaseModel):
    id: str
    status: str
    scan_version: str
    started_at: str
    completed_at: str | None
    total_candidates: int
    processed_files: int
    included_files: int
    excluded_files: int
    binary_files: int
    sensitive_files: int
    failed_files: int
    unknown_items: int
    unsupported_files: int
    test_files: int
    relationship_count: int
    duration_seconds: float | None
    error_summary: str | None


class ProjectResponse(BaseModel):
    id: str
    display_name: str
    display_path: str
    repository_path: str
    monitoring_mode: str
    monitoring_status: str
    last_scan_status: str | None
    last_scan_at: str | None
    created_at: str
    updated_at: str | None
    languages: list[str]
    frameworks: list[str]
    tests: list[str]
    runtime_hints: list[str]
    git: GitStateResponse
    scan: ScanRunResponse | None
    source_remains_local: bool


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]


class ActionResponse(BaseModel):
    status: str


class MonitoringResponse(BaseModel):
    monitoring_status: str


class ChangeObservationResponse(BaseModel):
    id: str
    observed_at: str
    worktree_fingerprint: str
    changed_paths: list[str]


class ChangeListResponse(BaseModel):
    changes: list[ChangeObservationResponse]


class CurrentChangeResponse(BaseModel):
    id: str
    project_id: str
    change_kind: str
    revision: int
    base_head_sha: str | None
    head_sha: str | None
    worktree_fingerprint: str
    changed_paths: list[str]
    task_intent: str | None
    status: str
    created_at: str
    updated_at: str


class ChangeIntentRequest(BaseModel):
    intent: str | None = None


class ImpactAnalyzeRequest(BaseModel):
    max_depth: int = 4
    max_result_nodes: int = 250
    max_paths_per_result: int = 3
    max_heuristic_depth: int = 1
    max_duration_ms: int = 1500
    max_unknown_expansion: int = 50
    max_explanation_bytes: int = 48000


class ImpactAnalysisResponse(BaseModel):
    id: str
    project_id: str
    change_id: str
    analysis_revision: int
    base_head_sha: str | None
    head_sha: str | None
    worktree_fingerprint: str
    scan_revision: str | None
    algorithm_version: str
    status: str
    changed_file_count: int
    impacted_node_count: int
    unknown_count: int
    stale_count: int
    heuristic_count: int
    truncated: bool
    truncation_reasons: list[str]
    duration_ms: float
    stale: bool
    stale_reasons: list[str]
    created_at: str


class ImpactAnalysisResultResponse(BaseModel):
    id: str
    node_id: str | None
    node_type: str
    display_name: str
    relative_path: str | None
    impact_class: str
    minimum_depth: int
    strongest_provenance: str
    stale: bool
    unknown: bool
    explanation: str
    path_count: int
    ranking_score: float
    ranking_reasons: list[str]
    unknown_reason: str | None


class ChangeImpactResponse(BaseModel):
    analysis: ImpactAnalysisResponse
    results: list[ImpactAnalysisResultResponse]


class ImpactPathListResponse(BaseModel):
    paths: list[dict[str, object]]


class ImpactUnknownListResponse(BaseModel):
    unknowns: list[ImpactAnalysisResultResponse]


class ContextReceiptResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_name: str = Field(alias="schema")
    id: str
    project: dict[str, object]
    change_id: str
    analysis_id: str
    request: str | None
    source_revision: dict[str, object]
    selected_files: list[dict[str, object]]
    selected_symbols: list[str]
    related_tests: list[str]
    relationship_paths: list[dict[str, object]]
    constraints: dict[str, object]
    unknowns: list[dict[str, object]]
    excluded_context: list[dict[str, object]]
    selection_reasons: list[str]
    size_metrics: dict[str, object]
    truncated: bool
    stale: bool
    source_uploaded: bool
    created_at: str


class BehaviorCandidateResponse(BaseModel):
    id: str
    title: str | None = None
    source_type: str | None = None
    source_key: str | None = None
    status: str
    evidence: str | None = None
    verification: str
    not_protected: bool
    created_at: str | None = None
    updated_at: str | None = None


class BehaviorCandidateListResponse(BaseModel):
    candidates: list[BehaviorCandidateResponse]


class ImpactSummaryResponse(BaseModel):
    files_indexed: int
    languages: int
    language_counts: dict[str, int]
    direct_relationships: int
    tests_found: int
    sensitive_files: int
    unknown_references: int
    unsupported_files: int
    stale_relationships: int


class RelationshipResponse(BaseModel):
    direction: str
    type: str
    target_type: str
    target: str
    target_path: str | None
    provenance: str
    parser_adapter: str
    source_scan_revision: str
    stale: bool


class ImpactNodeResponse(BaseModel):
    type: str
    label: str
    relative_path: str | None


class ImpactSearchItem(BaseModel):
    node: ImpactNodeResponse
    relationships: list[RelationshipResponse]
    recent_changes: list[str]


class ImpactSearchResponse(BaseModel):
    results: list[ImpactSearchItem]


class ScanFindingResponse(BaseModel):
    severity: str
    code: str
    relative_path: str | None
    message: str


class ScanFindingListResponse(BaseModel):
    findings: list[ScanFindingResponse]


class LocalEventResponse(BaseModel):
    sequence: int
    event_type: str
    project_id: str | None
    occurred_at: str
    payload: dict[str, object]


class LocalEventListResponse(BaseModel):
    events: list[LocalEventResponse]
