from __future__ import annotations

from pydantic import BaseModel


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
    type: str
    target_type: str
    target: str
    target_path: str | None
    provenance: str
    parser_adapter: str


class ImpactNodeResponse(BaseModel):
    type: str
    label: str
    relative_path: str | None


class ImpactSearchItem(BaseModel):
    node: ImpactNodeResponse
    relationships: list[RelationshipResponse]


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
