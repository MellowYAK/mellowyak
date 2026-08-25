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
    project_type: str = "OTHER"
    observation_level: str = "LIGHT"
    snapshot_retention_days: int = Field(default=30, ge=1, le=3650)
    snapshot_soft_cap_bytes: int = Field(
        default=5 * 1024 * 1024 * 1024,
        ge=16 * 1024 * 1024,
        le=1024 * 1024 * 1024 * 1024,
    )


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
    project_type: str = "OTHER"
    runtime_setup_status: str = "INCOMPLETE"
    observation_level: str = "LIGHT"
    snapshot_retention_days: int = 30
    snapshot_soft_cap_bytes: int = 5 * 1024 * 1024 * 1024
    phase7: dict[str, object] = Field(default_factory=dict)


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


class RuntimeProfileCreateRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=240)
    runtime_type: str = Field(min_length=1, max_length=40)
    primary: bool = False
    execution_mode: str = "MANAGED"
    executable_reference: str | None = Field(default=None, max_length=2000)
    argv: list[str] = Field(default_factory=list, max_length=100)
    relative_working_directory: str = Field(default=".", max_length=2000)
    runtime_version: str | None = Field(default=None, max_length=120)
    dependency_fingerprint: str | None = Field(default=None, max_length=64)
    health_definition: dict[str, object] = Field(default_factory=dict)
    expected_ports: list[int] = Field(default_factory=list, max_length=20)
    test_definitions: list[dict[str, object]] = Field(default_factory=list, max_length=50)
    environment_schema: list[str] = Field(default_factory=list, max_length=100)
    network_policy: str = "LOOPBACK_ONLY"
    limitations: list[str] = Field(default_factory=list, max_length=100)
    approved: bool = False


class RuntimeDetectionResponse(BaseModel):
    id: str
    project_id: str
    status: str
    candidates: list[dict[str, object]]
    started_at: str
    completed_at: str | None
    error_code: str | None


class RuntimeProfileVersionResponse(BaseModel):
    id: str
    version_number: int
    runtime_type: str
    adapter_version: str
    execution_mode: str
    executable_reference: str | None
    argv: list[str]
    relative_working_directory: str
    runtime_version: str | None
    dependency_fingerprint: str | None
    health_definition: dict[str, object]
    expected_ports: list[int]
    test_definitions: list[dict[str, object]]
    environment_schema: list[str]
    network_policy: str
    limitations: list[str]
    approved_at: str | None
    detected_at: str | None
    created_at: str


class RuntimeProfileResponse(BaseModel):
    id: str
    project_id: str
    display_name: str
    current_version_id: str
    primary: bool
    status: str
    current_version: RuntimeProfileVersionResponse
    versions: list[RuntimeProfileVersionResponse]
    created_at: str
    updated_at: str
    validation: dict[str, object] | None = None


class RuntimeProfileListResponse(BaseModel):
    profiles: list[RuntimeProfileResponse]


class RuntimeInstanceResponse(BaseModel):
    id: str
    project_id: str
    profile_id: str
    profile_version_id: str
    correlation_id: str
    status: str
    process_id: int | None
    started_at: str
    stopped_at: str | None
    exit_code: int | None
    observation: dict[str, object]


class RuntimeInstanceListResponse(BaseModel):
    instances: list[RuntimeInstanceResponse]


class SnapshotCreateRequest(BaseModel):
    creation_reason: str = Field(default="MANUAL_SAVE_POINT", max_length=40)
    episode_id: str | None = Field(default=None, max_length=36)


class SnapshotSummaryResponse(BaseModel):
    id: str
    project_id: str
    parent_snapshot_id: str | None
    episode_id: str | None
    manifest_digest: str
    creation_reason: str
    source_identity: dict[str, object]
    git_anchor: dict[str, object]
    included_count: int
    excluded_count: int
    sensitive_count: int
    unsupported_count: int
    logical_bytes: int
    physical_bytes_added: int
    reused_bytes: int
    pinned: bool
    integrity_status: str
    created_at: str


class SnapshotDetailResponse(SnapshotSummaryResponse):
    entries: list[dict[str, object]]
    runtime_profile_fingerprints: list[dict[str, object] | str]


class SnapshotListResponse(BaseModel):
    snapshots: list[SnapshotSummaryResponse]


class SnapshotMaterializationResponse(BaseModel):
    snapshot_id: str
    relative_path: str
    file_count: int
    logical_bytes: int
    verified: bool
    live_project_modified: bool = False


class SourceEpisodeResponse(BaseModel):
    id: str
    project_id: str
    started_at: str
    ended_at: str | None
    event_count: int
    added_paths: list[str]
    modified_paths: list[str]
    deleted_paths: list[str]
    renamed_paths: list[dict[str, str]]
    dependency_changes: list[str]
    runtime_events: list[dict[str, object]]
    base_snapshot_id: str | None
    resulting_snapshot_id: str | None
    git_anchor: dict[str, object]
    status: str
    error_code: str | None


class SourceEpisodeListResponse(BaseModel):
    episodes: list[SourceEpisodeResponse]


class MilestoneCreateRequest(BaseModel):
    snapshot_id: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=240)
    behavior_id: str | None = Field(default=None, max_length=36)
    behavior_version_id: str | None = Field(default=None, max_length=36)
    probe_version_id: str | None = Field(default=None, max_length=36)
    human_attested: bool = False


class SnapshotMilestoneResponse(BaseModel):
    id: str
    project_id: str
    snapshot_id: str
    display_name: str
    behavior_id: str | None
    behavior_version_id: str | None
    probe_version_id: str | None
    runtime_profile_versions: list[str]
    environment_summary: dict[str, object]
    limitations: list[str]
    status: str
    human_attested: bool
    pinned: bool
    created_at: str


class SnapshotMilestoneListResponse(BaseModel):
    milestones: list[SnapshotMilestoneResponse]


class ProbeCreateRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=240)
    probe_type: str = Field(min_length=1, max_length=40)
    behavior_id: str | None = Field(default=None, max_length=36)
    runtime_profile_version_id: str | None = Field(default=None, max_length=36)
    definition: dict[str, object] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    retry_policy: dict[str, object] = Field(default_factory=dict)
    expected_result: dict[str, object] = Field(default_factory=dict)
    evidence_policy: dict[str, object] = Field(default_factory=dict)
    source_links: list[dict[str, object]] = Field(default_factory=list, max_length=100)
    runtime_links: list[dict[str, object]] = Field(default_factory=list, max_length=100)
    approved: bool = False


class ProbeVersionResponse(BaseModel):
    id: str
    version_number: int
    runtime_profile_version_id: str | None
    definition: dict[str, object]
    timeout_seconds: int
    retry_policy: dict[str, object]
    expected_result: dict[str, object]
    evidence_policy: dict[str, object]
    source_links: list[dict[str, object]]
    runtime_links: list[dict[str, object]]
    approved_at: str | None
    created_at: str


class ProbeDefinitionResponse(BaseModel):
    id: str
    project_id: str
    behavior_id: str | None
    display_name: str
    probe_type: str
    current_version_id: str
    status: str
    current_version: ProbeVersionResponse
    versions: list[ProbeVersionResponse]
    last_run: dict[str, object] | None = None
    created_at: str
    updated_at: str


class ProbeListResponse(BaseModel):
    probes: list[ProbeDefinitionResponse]


class ProbeSelectionItemResponse(BaseModel):
    probe_id: str
    probe_version_id: str
    behavior_id: str | None
    probe_type: str
    reason: str
    automatic_eligible: bool


class ProbeSelectionResponse(BaseModel):
    project_id: str
    episode_id: str
    change_id: str | None
    protection_plan_id: str | None
    changed_paths: list[str]
    selected: list[ProbeSelectionItemResponse]
    selected_count: int
    candidate_count: int
    truncated: bool
    unknown_count: int


class ProbeRunRequest(BaseModel):
    snapshot_id: str | None = Field(default=None, max_length=64)


class ProbeRunResponse(BaseModel):
    id: str
    project_id: str
    probe_id: str
    probe_version_id: str
    snapshot_id: str
    episode_id: str | None
    runtime_profile_version_id: str | None
    source_identity: dict[str, object]
    status: str
    result: str
    attempt_count: int
    expected: dict[str, object]
    observed: dict[str, object]
    evidence: dict[str, object]
    limitations: list[str]
    reproducible: bool
    signal: dict[str, object] | None = None
    started_at: str | None
    completed_at: str | None
    cancelled_at: str | None


class RepairWorkspaceOpenRequest(BaseModel):
    target: str = "FOLDER"


class RepairWorkspaceResponse(BaseModel):
    id: str
    project_id: str
    regression_id: str | None
    signal_id: str | None
    snapshot_id: str
    relative_path: str
    manifest_digest: str
    base_manifest_digest: str | None = None
    workspace_manifest_digest: str | None = None
    runtime_profile_versions: list[str] = Field(default_factory=list)
    validation_policy: dict[str, object] = Field(default_factory=dict)
    status: str
    instructions: str | None = None
    items: list[dict[str, object]]
    created_at: str
    deleted_at: str | None


class CandidateExcludeRequest(BaseModel):
    paths: list[str] = Field(default_factory=list, max_length=250)


class CandidateRestoreRequest(BaseModel):
    relative_path: str = Field(min_length=1, max_length=2000)


class RepairCandidateResponse(BaseModel):
    id: str
    project_id: str
    workspace_id: str
    revision: int
    state: str
    base_manifest_digest: str
    workspace_manifest_digest: str
    candidate_digest: str
    source_snapshot_id: str
    file_count: int
    logical_bytes: int
    binary_count: int
    warnings: list[str]
    limitations: list[str]
    files: list[dict[str, object]]
    created_at: str
    updated_at: str


class CandidateDiffResponse(BaseModel):
    candidate_id: str
    relative_path: str
    available: bool
    reason: str | None
    lines: list[str]
    truncated: bool = False


class RepairValidationResponse(BaseModel):
    id: str
    project_id: str
    candidate_id: str
    candidate_digest: str
    workspace_manifest_digest: str
    runtime_profile_versions: list[str]
    status: str
    evidence_digest: str | None
    limitations: list[str]
    started_at: str
    completed_at: str | None
    items: list[dict[str, object]]


class ApplyConfirmRequest(BaseModel):
    confirmation_nonce: str = Field(min_length=20, max_length=240)
    deliberate_confirmation: bool = False


class ApplyTransactionResponse(BaseModel):
    id: str
    project_id: str
    candidate_id: str
    validation_id: str
    state: str
    expected_source_snapshot_id: str
    expected_source_manifest_digest: str
    safety_snapshot_id: str | None
    post_apply_snapshot_id: str | None
    confirmation_expires_at: str
    confirmation_used: bool
    confirmation_nonce: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    journal_relative_path: str
    error_code: str | None
    files: list[dict[str, object]]
    events: list[dict[str, object]]
    rollbacks: list[dict[str, object]]
    created_at: str
    updated_at: str
    completed_at: str | None


class ApplyTransactionListResponse(BaseModel):
    transactions: list[ApplyTransactionResponse]


class RecoveryBundleResponse(BaseModel):
    id: str
    transaction_id: str
    relative_path: str
    manifest_digest: str
    status: str
    created_at: str


class PortableRepairRequest(BaseModel):
    selected_paths: list[str] = Field(default_factory=list, max_length=100)


class PortableRepairResponse(BaseModel):
    id: str
    workspace_id: str
    relative_path: str
    file_count: int
    logical_bytes: int
    uploaded: bool


class DemoLabCreateRequest(BaseModel):
    selected_parent: str = Field(min_length=1, max_length=4000)


class DemoLabResponse(BaseModel):
    id: str
    project_id: str | None
    synthetic: bool
    scenario: str
    status: str
    state: dict[str, object]
    created_at: str
    updated_at: str


class ProductSelfTestResponse(BaseModel):
    id: str
    status: str
    steps: list[dict[str, object]]
    duration_ms: float
    report_relative_path: str | None
    created_at: str
    completed_at: str | None


class LocalExportResponse(BaseModel):
    run_id: str
    relative_path: str | None
    private_paths_included: bool
    exported: bool


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
