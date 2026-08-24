from __future__ import annotations

from datetime import datetime

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
    disconnected: bool = False
    source_available: bool = True
    notifications_muted: bool = False


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
    behavior_draft_id: str | None = None


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


class AlertResponse(BaseModel):
    id: str
    project_id: str | None = None
    change_id: str | None = None
    behavior_id: str | None = None
    regression_id: str | None = None
    gate_id: str | None = None
    severity: str
    category: str
    title_key: str
    summary_key: str
    parameters: dict[str, object]
    route: dict[str, object]
    read: bool
    resolved: bool
    created_at: str
    updated_at: str


class AlertListResponse(BaseModel):
    alerts: list[AlertResponse]


class UnreadCountResponse(BaseModel):
    count: int


class NotificationSettingsRequest(BaseModel):
    native_enabled: bool | None = None
    regression_enabled: bool | None = None
    blocked_gate_enabled: bool | None = None
    needs_review_enabled: bool | None = None
    project_errors_enabled: bool | None = None
    verified_complete_enabled: bool | None = None
    regression_resolved_enabled: bool | None = None
    show_behavior_name: bool | None = None
    show_project_name: bool | None = None
    hide_details: bool | None = None
    critical_override: bool | None = None


class QuietModeStartRequest(BaseModel):
    duration: str
    allow_critical: bool = False


class ProjectNotificationRequest(BaseModel):
    muted: bool


class ProjectRelocateRequest(BaseModel):
    path: str
    confirm_identity_change: bool = False


class ProjectDeleteRequest(BaseModel):
    confirmation: str


class BackgroundSettingsRequest(BaseModel):
    keep_running_on_close: bool | None = None
    start_at_login: bool | None = None


class BehaviorDraftRequest(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(default="", max_length=4000)
    expected_outcome: str = Field(default="", max_length=4000)
    criticality: str = "MEDIUM"
    persona: str = Field(default="", max_length=500)
    preconditions: str = Field(default="", max_length=4000)
    starting_state: str = Field(default="", max_length=4000)
    expected_assertions: list[dict[str, object]] = Field(default_factory=list, max_length=50)
    links: list[dict[str, str]] = Field(default_factory=list, max_length=50)
    always_recheck: bool = False


class BehaviorVersionResponse(BaseModel):
    id: str
    version_number: int
    title: str
    description: str
    expected_outcome: str
    criticality: str
    persona: str
    preconditions: str
    starting_state: str
    expected_assertions: list[dict[str, object]]
    limitations: list[str]
    verification_not_configured: bool
    created_by_type: str
    source_candidate_id: str | None
    content_digest: str
    supersedes_version_id: str | None
    source_revision: dict[str, object]
    created_at: datetime


class BehaviorBaselineSummaryResponse(BaseModel):
    id: str
    status: str
    behavior_version_id: str
    evidence_bundle_id: str
    created_at: datetime


class ProtectedBehaviorResponse(BaseModel):
    id: str
    project_id: str
    stable_key: str
    display_name: str
    lifecycle_state: str
    current_version_id: str
    last_accepted_baseline_id: str | None
    always_recheck: bool
    current_version: BehaviorVersionResponse
    versions: list[BehaviorVersionResponse]
    links: list[dict[str, str]]
    baselines: list[BehaviorBaselineSummaryResponse]
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class ProtectedBehaviorListResponse(BaseModel):
    behaviors: list[ProtectedBehaviorResponse]


class RuntimeConfigurationRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=240)
    base_url: str = Field(min_length=1, max_length=2000)
    starting_path: str = Field(default="/", max_length=1000)
    viewport_width: int = Field(default=1280, ge=320, le=3840)
    viewport_height: int = Field(default=800, ge=240, le=2160)
    locale: str = Field(default="en-US", max_length=40)
    timezone: str = Field(default="UTC", max_length=80)
    browser_type: str = "chromium"
    capture_screenshots: bool = True
    capture_trace: bool = False
    capture_video: bool = False
    capture_network: bool = True


class RuntimeConfigurationResponse(BaseModel):
    id: str
    project_id: str
    display_name: str
    base_url: str
    allowed_origin: str
    starting_path: str
    viewport_width: int
    viewport_height: int
    locale: str
    timezone: str
    browser_type: str
    capture_screenshots: bool
    capture_trace: bool
    capture_video: bool
    capture_network: bool
    created_at: datetime
    updated_at: datetime


class RuntimeConfigurationListResponse(BaseModel):
    runtimes: list[RuntimeConfigurationResponse]


class BrowserCaptureStartRequest(BaseModel):
    behavior_id: str
    runtime_configuration_id: str
    entry_url: str | None = Field(default=None, max_length=2000)


class BrowserCaptureStepResponse(BaseModel):
    id: str
    ordinal: int
    event_type: str
    page_url: str
    selector: str | None
    metadata: dict[str, object]
    occurred_at: datetime
    included: bool
    label: str


class RuntimeObservationResponse(BaseModel):
    id: str
    observation_type: str
    metadata: dict[str, object]
    observed_at: datetime
    included: bool


class BrowserCaptureResponse(BaseModel):
    id: str
    project_id: str
    behavior_id: str
    behavior_version_id: str
    runtime_configuration_id: str
    status: str
    entry_url: str
    source_revision: dict[str, object]
    source_stale: bool
    steps: list[BrowserCaptureStepResponse]
    observations: list[RuntimeObservationResponse]
    started_at: datetime
    stopped_at: datetime | None
    error_code: str | None
    paused: bool
    browser_version: str | None
    expected_assertions: list[dict[str, object]]


class CaptureReviewRequest(BaseModel):
    step_updates: list[dict[str, object]] = Field(default_factory=list, max_length=500)
    excluded_observation_ids: list[str] = Field(default_factory=list, max_length=1000)
    expected_assertions: list[dict[str, object]] = Field(default_factory=list, max_length=50)
    notes: str = Field(default="", max_length=4000)


class BaselineRevokeRequest(BaseModel):
    delete_evidence: bool = False
    confirmation: bool = False


class BrowserCaptureListResponse(BaseModel):
    captures: list[BrowserCaptureResponse]


class BaselineAcceptRequest(BaseModel):
    reviewer: str = Field(min_length=1, max_length=240)
    notes: str = Field(default="", max_length=4000)


class BehaviorBaselineResponse(BaseModel):
    id: str
    project_id: str
    behavior_id: str
    behavior_version_id: str
    evidence_bundle_id: str
    status: str
    source_revision: dict[str, object]
    attestation: dict[str, object]
    created_at: datetime
    revoked_at: datetime | None


class EvidenceArtifactResponse(BaseModel):
    id: str
    project_id: str
    sha256: str
    size_bytes: int
    media_type: str
    redaction_state: str
    capture_id: str | None
    behavior_id: str | None
    behavior_version_id: str | None
    source_identity: dict[str, object]
    runtime_identity: dict[str, object]
    trust_source: str
    local_reference: str
    integrity_verified: bool
    created_at: datetime


class EvidenceListResponse(BaseModel):
    bundles: list[dict[str, object]]
    artifacts: list[EvidenceArtifactResponse]


class EvidenceBundleResponse(BaseModel):
    id: str
    project_id: str
    capture_id: str
    manifest_sha256: str
    status: str
    bundle_type: str
    verification_run_id: str | None
    items: list[dict[str, object]]
    created_at: datetime


class ProtectionPlanResponse(BaseModel):
    id: str
    project_id: str
    change_id: str
    impact_analysis_id: str
    source_identity: dict[str, object]
    binding_digest: str
    algorithm_version: str
    policy_version: str
    status: str
    created_at: datetime
    stale_at: datetime | None
    counts: dict[str, int]
    truncated: bool
    items: list[dict[str, object]]


class VerificationRunResponse(BaseModel):
    id: str
    project_id: str
    change_id: str
    plan_id: str
    source_identity: dict[str, object]
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    error_code: str | None
    created_at: datetime
    items: list[dict[str, object]]


class VerificationStartRequest(BaseModel):
    plan_id: str = Field(min_length=1, max_length=36)
    item_ids: list[str] = Field(default_factory=list, max_length=50)


class HumanVerificationRequest(BaseModel):
    run_item_id: str = Field(min_length=1, max_length=36)
    result: str = Field(min_length=1, max_length=40)
    note: str = Field(min_length=1, max_length=4000)
    confirmed: bool = False
    evidence_reference: str | None = Field(default=None, max_length=1000)


class GateDecisionResponse(BaseModel):
    id: str
    project_id: str
    change_id: str
    plan_id: str
    verification_run_id: str | None
    state: str
    reason: str
    source_identity: dict[str, object]
    limitations: list[str]
    decision_digest: str
    created_at: datetime


class RegressionListResponse(BaseModel):
    regressions: list[dict[str, object]]


class RepairContextResponse(BaseModel):
    id: str
    project_id: str
    change_id: str
    regression_id: str
    schema_version: str
    source_identity: dict[str, object]
    payload: dict[str, object]
    digest: str
    size_bytes: int
    saved_relative_path: str | None
    created_at: datetime


class RepairContextCopyResponse(BaseModel):
    context_id: str
    text: str
    transmitted: bool


class RepairContextSaveResponse(BaseModel):
    context_id: str
    relative_path: str
    saved: bool
