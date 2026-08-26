from __future__ import annotations

import os
import platform
import subprocess
import time
from dataclasses import dataclass

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from mellowyak_engine import APP_VERSION, ENGINE_VERSION
from mellowyak_engine.api.schemas import (
    ActionResponse,
    ActivityModeRequest,
    AlertListResponse,
    AlertResponse,
    ApplyConfirmRequest,
    ApplyTransactionListResponse,
    ApplyTransactionResponse,
    BackgroundSettingsRequest,
    BaselineAcceptRequest,
    BaselineRevokeRequest,
    BehaviorBaselineResponse,
    BehaviorCandidateListResponse,
    BehaviorCandidateResponse,
    BehaviorDraftRequest,
    BrowserCaptureListResponse,
    BrowserCaptureResponse,
    BrowserCaptureStartRequest,
    CandidateDiffResponse,
    CandidateExcludeRequest,
    CandidateRestoreRequest,
    CaptureReviewRequest,
    CaptureValidateRequest,
    ChangeImpactResponse,
    ChangeIntentRequest,
    ChangeListResponse,
    ContextReceiptResponse,
    CurrentChangeResponse,
    DemoLabCreateRequest,
    DemoLabResponse,
    DiagnosticsOverviewAggregateResponse,
    DiagnosticsResponse,
    DisconnectedProjectListResponse,
    EpisodeDetailAggregateResponse,
    EvidenceArtifactResponse,
    EvidenceBundleResponse,
    EvidenceListResponse,
    GateDecisionResponse,
    GitStateResponse,
    HandshakeResponse,
    HealthResponse,
    HomeSummaryResponse,
    HumanVerificationRequest,
    ImpactAnalyzeRequest,
    ImpactPathListResponse,
    ImpactSearchResponse,
    ImpactSummaryResponse,
    ImpactUnknownListResponse,
    InstallationResponse,
    LocalEventListResponse,
    LocalExportResponse,
    MilestoneCreateRequest,
    MonitoringResponse,
    NotificationActivationRequest,
    NotificationSettingsRequest,
    OnboardingResponse,
    OnboardingUpdateRequest,
    OpenDataFolderResponse,
    PackageAcceptanceRecordRequest,
    PerformanceMetricRequest,
    PortableRepairRequest,
    PortableRepairResponse,
    PrivacySettingsResponse,
    ProbeCreateRequest,
    ProbeDefinitionResponse,
    ProbeListResponse,
    ProbeRunRequest,
    ProbeRunResponse,
    ProbeSelectionResponse,
    ProductSelfTestResponse,
    ProjectActivityAggregateResponse,
    ProjectCreateRequest,
    ProjectDeleteRequest,
    ProjectDetectionResponse,
    ProjectDetectRequest,
    ProjectListResponse,
    ProjectLocationRequest,
    ProjectNotificationRequest,
    ProjectOverviewAggregateResponse,
    ProjectRelocateRequest,
    ProjectResponse,
    ProtectedBehaviorListResponse,
    ProtectedBehaviorResponse,
    ProtectionPlanResponse,
    QuietModeStartRequest,
    ReadinessResponse,
    RecoveryBundleResponse,
    RegressionDetailAggregateResponse,
    RegressionListResponse,
    RepairCandidateResponse,
    RepairContextCopyResponse,
    RepairContextResponse,
    RepairContextSaveResponse,
    RepairValidationResponse,
    RepairWorkspaceOpenRequest,
    RepairWorkspaceResponse,
    RuntimeConfigurationListResponse,
    RuntimeConfigurationRequest,
    RuntimeConfigurationResponse,
    RuntimeDetectionResponse,
    RuntimeInstanceListResponse,
    RuntimeInstanceResponse,
    RuntimeProfileCreateRequest,
    RuntimeProfileListResponse,
    RuntimeProfileResponse,
    ScanFindingListResponse,
    ScanRunResponse,
    SnapshotCreateRequest,
    SnapshotDetailResponse,
    SnapshotListResponse,
    SnapshotMaterializationResponse,
    SnapshotMilestoneListResponse,
    SnapshotMilestoneResponse,
    SnapshotSummaryResponse,
    SourceEpisodeListResponse,
    SourceEpisodeResponse,
    StoragePathsResponse,
    UnreadCountResponse,
    UpdateCheckRecordRequest,
    UpdateFixtureRequest,
    VerificationRunResponse,
    VerificationStartRequest,
)
from mellowyak_engine.behaviors.service import BehaviorService, BehaviorServiceError
from mellowyak_engine.browser.service import BrowserCaptureError, BrowserCaptureService
from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.core.logging import configure_logging
from mellowyak_engine.db.database import LocalDatabase
from mellowyak_engine.demo_lab.self_test import ProductSelfTestService
from mellowyak_engine.demo_lab.service import DemoLabService, DemoLabServiceError
from mellowyak_engine.episodes.service import EpisodeService
from mellowyak_engine.evidence.service import EvidenceService, EvidenceServiceError
from mellowyak_engine.evidence.store import EvidenceStore
from mellowyak_engine.gate.service import GateError, GateService
from mellowyak_engine.impact.models import TraversalPolicy
from mellowyak_engine.impact.service import ImpactService, ImpactServiceError
from mellowyak_engine.monitoring.service import MonitoringService
from mellowyak_engine.probes.service import ProbeService, ProbeServiceError
from mellowyak_engine.product_truth.service import ProductTruthService
from mellowyak_engine.productization.service import ProductizationError, ProductizationService
from mellowyak_engine.projects.service import ProjectError, ProjectService
from mellowyak_engine.protection.service import ProtectionPlanError, ProtectionPlanService
from mellowyak_engine.regression.service import RegressionService
from mellowyak_engine.repair.service import RepairContextError, RepairContextService
from mellowyak_engine.repair_candidates.service import (
    RepairCandidateService,
    RepairCandidateServiceError,
)
from mellowyak_engine.repair_validation.service import (
    RepairValidationService,
    RepairValidationServiceError,
)
from mellowyak_engine.repair_workspace.export import PortableRepairError, PortableRepairService
from mellowyak_engine.repair_workspace.service import (
    RepairWorkspaceService,
    RepairWorkspaceServiceError,
)
from mellowyak_engine.runtime_profiles.service import (
    RuntimeProfileService,
    RuntimeProfileServiceError,
)
from mellowyak_engine.safe_apply.service import SafeApplyService, SafeApplyServiceError
from mellowyak_engine.scanning.service import ScanCoordinator, SourceScanner
from mellowyak_engine.security.auth import SessionTokenGuard
from mellowyak_engine.settings.config import EngineSettings
from mellowyak_engine.snapshots.service import SnapshotService, SnapshotServiceError
from mellowyak_engine.storage.paths import StoragePaths
from mellowyak_engine.technical_preview.service import (
    TechnicalPreviewError,
    TechnicalPreviewService,
)
from mellowyak_engine.verification.service import VerificationError, VerificationService
from mellowyak_engine.workflow import state_model


@dataclass
class EngineRuntime:
    settings: EngineSettings
    paths: StoragePaths
    database: LocalDatabase
    schema_version: str
    installation_id: str
    run_id: str
    started_monotonic: float
    events: LocalEventBus
    projects: ProjectService
    scans: ScanCoordinator
    monitoring: MonitoringService
    impact: ImpactService
    behaviors: BehaviorService
    evidence: EvidenceService
    browser: BrowserCaptureService
    protection: ProtectionPlanService
    gate: GateService
    regressions: RegressionService
    repair: RepairContextService
    verification: VerificationService
    productization: ProductizationService
    runtime_profiles: RuntimeProfileService
    snapshots: SnapshotService
    episodes: EpisodeService
    probes: ProbeService
    repair_workspaces: RepairWorkspaceService
    repair_candidates: RepairCandidateService
    repair_validations: RepairValidationService
    safe_apply: SafeApplyService
    portable_repairs: PortableRepairService
    demo_lab: DemoLabService
    self_test: ProductSelfTestService
    technical_preview: TechnicalPreviewService
    product_truth: ProductTruthService


def _open_folder(path: str) -> str:
    system = platform.system().lower()
    if system == "darwin":
        command = ["/usr/bin/open", path]
        method = "macos_open"
    elif system == "windows":
        command = ["explorer.exe", path]
        method = "windows_explorer"
    else:
        command = ["xdg-open", path]
        method = "linux_xdg_open"
    subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    return method


def create_app(settings: EngineSettings) -> FastAPI:
    paths = StoragePaths.create(settings.data_root)
    logger = configure_logging(paths.logs, settings.session_token, paths.root)
    database = LocalDatabase(paths)
    schema_version = database.migrate()
    installation = database.ensure_installation()
    run_id = database.record_start(installation.id)
    events = LocalEventBus()
    projects = ProjectService(database.sessions, installation.id, events)
    scans = ScanCoordinator(SourceScanner(database.sessions, events))
    snapshots = SnapshotService(database.sessions, paths.root, events)
    episodes = EpisodeService(database.sessions, events)
    episodes.bind_snapshot_callback(snapshots.create)
    monitoring = MonitoringService(projects, scans, episodes)
    runtime_profiles = RuntimeProfileService(database.sessions, events)
    impact = ImpactService(database.sessions, events)
    behaviors = BehaviorService(database.sessions, events)
    evidence = EvidenceService(database.sessions, EvidenceStore(paths.evidence), events)
    protection = ProtectionPlanService(database.sessions, events)
    gate = GateService(database.sessions, events, evidence)
    regressions = RegressionService(database.sessions, events)
    repair = RepairContextService(database.sessions, paths.root, events)
    productization = ProductizationService(database.sessions, paths.root, events)
    technical_preview = TechnicalPreviewService(
        database.sessions,
        paths.root,
        schema_version,
        installation.id,
        events,
    )
    product_truth = ProductTruthService(database.sessions, technical_preview)
    probes = ProbeService(database.sessions, events, snapshots, productization)
    browser = BrowserCaptureService(database.sessions, evidence, events, probes)
    episodes.bind_selection_callback(probes.select_impacted)
    repair_workspaces = RepairWorkspaceService(database.sessions, paths.root, events, _open_folder)
    repair_candidates = RepairCandidateService(database.sessions, paths.root, events)
    repair_validations = RepairValidationService(database.sessions, paths.root, events)
    safe_apply = SafeApplyService(database.sessions, paths.root, events, snapshots)
    portable_repairs = PortableRepairService(database.sessions, paths.root)
    demo_lab = DemoLabService(
        database.sessions,
        paths.root,
        events,
        projects,
        snapshots,
        repair_candidates,
        repair_validations,
        safe_apply,
    )
    self_test = ProductSelfTestService(database.sessions, paths.root, events)
    verification = VerificationService(
        database.sessions,
        evidence,
        events,
        gate,
        regressions,
        installation.id,
    )
    runtime = EngineRuntime(
        settings=settings,
        paths=paths,
        database=database,
        schema_version=schema_version,
        installation_id=installation.id,
        run_id=run_id,
        started_monotonic=time.monotonic(),
        events=events,
        projects=projects,
        scans=scans,
        monitoring=monitoring,
        impact=impact,
        behaviors=behaviors,
        evidence=evidence,
        browser=browser,
        protection=protection,
        gate=gate,
        regressions=regressions,
        repair=repair,
        verification=verification,
        productization=productization,
        runtime_profiles=runtime_profiles,
        snapshots=snapshots,
        episodes=episodes,
        probes=probes,
        repair_workspaces=repair_workspaces,
        repair_candidates=repair_candidates,
        repair_validations=repair_validations,
        safe_apply=safe_apply,
        portable_repairs=portable_repairs,
        demo_lab=demo_lab,
        self_test=self_test,
        technical_preview=technical_preview,
        product_truth=product_truth,
    )

    app = FastAPI(
        title="MellowYak Local Engine",
        version=ENGINE_VERSION,
        description="Loopback-only API used by the MellowYak desktop shell.",
    )
    app.state.runtime = runtime
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def restrict_origin(request: Request, call_next):  # type: ignore[no-untyped-def]
        origin = request.headers.get("origin", "")
        if origin and origin not in settings.allowed_origins:
            return JSONResponse(status_code=403, content={"detail": "ORIGIN_NOT_ALLOWED"})
        return await call_next(request)

    guard = SessionTokenGuard(settings.session_token)

    def project_error(error: ProjectError) -> HTTPException:
        status = 404 if error.code in {"PROJECT_NOT_FOUND", "PROJECT_ROOT_UNAVAILABLE"} else 400
        if error.code == "PROJECT_ALREADY_CONNECTED":
            status = 409
        return HTTPException(status_code=status, detail=error.code)

    def impact_error(error: ImpactServiceError) -> HTTPException:
        status = (
            404 if error.code.endswith("_NOT_FOUND") or error.code == "PROJECT_NOT_FOUND" else 409
        )
        if error.code in {"TASK_INTENT_TOO_LONG", "BEHAVIOR_ACTION_INVALID"}:
            status = 400
        return HTTPException(status_code=status, detail=error.code)

    def phase4_error(error: Exception) -> HTTPException:
        code = str(getattr(error, "code", "PHASE4_OPERATION_FAILED"))
        status = 409
        if code.endswith("_NOT_FOUND"):
            status = 404
        elif code.endswith("_INVALID") or code in {
            "RUNTIME_LOOPBACK_HTTP_REQUIRED",
            "RUNTIME_EXPLICIT_PORT_REQUIRED",
            "CAPTURE_ORIGIN_NOT_ALLOWED",
            "ATTESTATION_INVALID",
        }:
            status = 400
        elif code in {"BROWSER_RUNTIME_UNAVAILABLE"}:
            status = 503
        return HTTPException(status_code=status, detail=code)

    def phase5_error(error: Exception) -> HTTPException:
        code = str(getattr(error, "code", str(error) or "PHASE5_OPERATION_FAILED"))
        status = 409
        if code.endswith("_NOT_FOUND"):
            status = 404
        elif code.endswith("_INVALID") or code.endswith("_LIMIT_EXCEEDED"):
            status = 400
        elif code in {"PLAYWRIGHT_UNAVAILABLE", "CHROMIUM_UNAVAILABLE"}:
            status = 503
        return HTTPException(status_code=status, detail=code)

    @app.get("/handshake", response_model=HandshakeResponse, include_in_schema=True)
    def handshake() -> HandshakeResponse:
        return HandshakeResponse(status="running", mode="local", authentication="required")

    @app.get("/health", response_model=HealthResponse, dependencies=[Depends(guard)])
    def health() -> HealthResponse:
        return HealthResponse(
            status="ready",
            mode="local",
            engine_version=ENGINE_VERSION,
            app_version=APP_VERSION,
            database_status="ready",
            database_schema_version=runtime.schema_version,
            data_root=str(paths.root),
            cloud_connected=False,
            outbound_network_enabled=False,
            uptime_seconds=round(time.monotonic() - runtime.started_monotonic, 3),
        )

    @app.get("/readiness", response_model=ReadinessResponse, dependencies=[Depends(guard)])
    def readiness() -> ReadinessResponse:
        pragmas = database.sqlite_pragmas()
        checks = {
            "storage_ready": paths.root.is_dir(),
            "database_ready": paths.sqlite_file.is_file(),
            "migration_ready": bool(runtime.schema_version),
            "sqlite_wal": str(pragmas["journal_mode"]).lower() == "wal",
            "sqlite_foreign_keys": pragmas["foreign_keys"] == 1,
            "local_only": settings.bind_host in {"127.0.0.1", "::1"},
        }
        return ReadinessResponse(ready=all(checks.values()), checks=checks)

    @app.get("/installation", response_model=InstallationResponse, dependencies=[Depends(guard)])
    def installation_info() -> InstallationResponse:
        current = database.installation()
        return InstallationResponse(
            installation_id=current.id,
            created_at=current.created_at.isoformat(),
            last_started_at=current.last_started_at.isoformat(),
            app_version=current.app_version,
            engine_version=current.engine_version,
            database_schema_version=runtime.schema_version,
        )

    @app.get(
        "/settings/privacy",
        response_model=PrivacySettingsResponse,
        dependencies=[Depends(guard)],
    )
    def privacy_settings() -> PrivacySettingsResponse:
        return PrivacySettingsResponse(
            mode="local",
            cloud_connected=False,
            outbound_network_enabled=False,
            source_upload_enabled=False,
            telemetry_upload_enabled=False,
            account_required=False,
        )

    @app.get("/storage/paths", response_model=StoragePathsResponse, dependencies=[Depends(guard)])
    def storage_paths() -> StoragePathsResponse:
        return StoragePathsResponse(**paths.public_dict())

    @app.post(
        "/system/open-data-folder",
        response_model=OpenDataFolderResponse,
        dependencies=[Depends(guard)],
    )
    def open_data_folder() -> OpenDataFolderResponse:
        method = _open_folder(str(paths.root))
        logger.info("data_folder_open_requested method=%s", method)
        return OpenDataFolderResponse(opened=True, method=method)

    @app.get("/projects", response_model=ProjectListResponse, dependencies=[Depends(guard)])
    def list_projects() -> ProjectListResponse:
        return ProjectListResponse(projects=projects.list())

    @app.get("/home/summary", response_model=HomeSummaryResponse, dependencies=[Depends(guard)])
    def home_summary() -> HomeSummaryResponse:
        return HomeSummaryResponse(**product_truth.home_summary())

    @app.get(
        "/projects/disconnected",
        response_model=DisconnectedProjectListResponse,
        dependencies=[Depends(guard)],
    )
    def list_disconnected_projects() -> DisconnectedProjectListResponse:
        return DisconnectedProjectListResponse(projects=technical_preview.disconnected_projects())

    @app.post(
        "/projects/detect",
        response_model=ProjectDetectionResponse,
        dependencies=[Depends(guard)],
    )
    def detect_project(request: ProjectDetectRequest) -> ProjectDetectionResponse:
        try:
            return ProjectDetectionResponse(**projects.detect(request.path)["public"])
        except ProjectError as error:
            raise project_error(error) from error

    @app.post("/projects", response_model=ProjectResponse, dependencies=[Depends(guard)])
    def create_project(request: ProjectCreateRequest) -> ProjectResponse:
        try:
            project = projects.create(
                request.path,
                request.display_name,
                request.monitoring_mode,
                request.project_type,
                request.observation_level,
                request.snapshot_retention_days,
                request.snapshot_soft_cap_bytes,
            )
            scans.start(project.id)
            if request.monitoring_mode == "passive":
                monitoring.start(project.id)
            return ProjectResponse(**projects.get(project.id))
        except ProjectError as error:
            raise project_error(error) from error
        except RuntimeError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get(
        "/projects/{project_id}", response_model=ProjectResponse, dependencies=[Depends(guard)]
    )
    def get_project(project_id: str) -> ProjectResponse:
        try:
            return ProjectResponse(**projects.get(project_id))
        except ProjectError as error:
            raise project_error(error) from error

    @app.get(
        "/projects/{project_id}/overview",
        response_model=ProjectOverviewAggregateResponse,
        dependencies=[Depends(guard)],
    )
    def project_overview(project_id: str) -> ProjectOverviewAggregateResponse:
        try:
            return ProjectOverviewAggregateResponse(**product_truth.project_overview(project_id))
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post(
        "/projects/{project_id}/scan",
        response_model=ActionResponse,
        dependencies=[Depends(guard)],
    )
    def start_scan(project_id: str) -> ActionResponse:
        try:
            projects.get_model(project_id)
            return ActionResponse(status=scans.start(project_id))
        except ProjectError as error:
            raise project_error(error) from error
        except RuntimeError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post(
        "/projects/{project_id}/scan/cancel",
        response_model=ActionResponse,
        dependencies=[Depends(guard)],
    )
    def cancel_scan(project_id: str) -> ActionResponse:
        return ActionResponse(status="cancelling" if scans.cancel(project_id) else "not_running")

    @app.get(
        "/projects/{project_id}/scan",
        response_model=ScanRunResponse | None,
        dependencies=[Depends(guard)],
    )
    def scan_status(project_id: str) -> ScanRunResponse | None:
        try:
            result = projects.scan(project_id)
            return ScanRunResponse(**result) if result else None
        except ProjectError as error:
            raise project_error(error) from error

    @app.get(
        "/projects/{project_id}/git",
        response_model=GitStateResponse,
        dependencies=[Depends(guard)],
    )
    def git_status(project_id: str) -> GitStateResponse:
        try:
            return GitStateResponse(**projects.git(project_id))
        except ProjectError as error:
            raise project_error(error) from error

    @app.get(
        "/projects/{project_id}/changes",
        response_model=ChangeListResponse,
        dependencies=[Depends(guard)],
    )
    def project_changes(project_id: str) -> ChangeListResponse:
        return ChangeListResponse(changes=projects.changes(project_id))

    @app.get(
        "/projects/{project_id}/changes/current",
        response_model=CurrentChangeResponse,
        dependencies=[Depends(guard)],
    )
    def current_change(project_id: str) -> CurrentChangeResponse:
        try:
            return CurrentChangeResponse(**impact.current_change(project_id))
        except ImpactServiceError as error:
            raise impact_error(error) from error

    @app.get(
        "/projects/{project_id}/changes/{change_id}",
        response_model=CurrentChangeResponse,
        dependencies=[Depends(guard)],
    )
    def change_detail(project_id: str, change_id: str) -> CurrentChangeResponse:
        try:
            return CurrentChangeResponse(**impact.get_change(project_id, change_id))
        except ImpactServiceError as error:
            raise impact_error(error) from error

    @app.post(
        "/projects/{project_id}/changes/{change_id}/intent",
        response_model=CurrentChangeResponse,
        dependencies=[Depends(guard)],
    )
    def change_intent(
        project_id: str, change_id: str, request: ChangeIntentRequest
    ) -> CurrentChangeResponse:
        try:
            return CurrentChangeResponse(**impact.set_intent(project_id, change_id, request.intent))
        except ImpactServiceError as error:
            raise impact_error(error) from error

    @app.post(
        "/projects/{project_id}/changes/{change_id}/analyze",
        response_model=ChangeImpactResponse,
        dependencies=[Depends(guard)],
    )
    def analyze_change(
        project_id: str, change_id: str, request: ImpactAnalyzeRequest
    ) -> ChangeImpactResponse:
        try:
            policy = TraversalPolicy(**request.model_dump())
            return ChangeImpactResponse(**impact.analyze(project_id, change_id, policy))
        except ImpactServiceError as error:
            raise impact_error(error) from error

    @app.get(
        "/projects/{project_id}/changes/{change_id}/impact",
        response_model=ChangeImpactResponse,
        dependencies=[Depends(guard)],
    )
    def change_impact(project_id: str, change_id: str) -> ChangeImpactResponse:
        try:
            return ChangeImpactResponse(**impact.get_impact(project_id, change_id))
        except ImpactServiceError as error:
            raise impact_error(error) from error

    @app.get(
        "/projects/{project_id}/changes/{change_id}/impact/paths",
        response_model=ImpactPathListResponse,
        dependencies=[Depends(guard)],
    )
    def change_impact_paths(project_id: str, change_id: str) -> ImpactPathListResponse:
        try:
            return ImpactPathListResponse(paths=impact.paths(project_id, change_id))
        except ImpactServiceError as error:
            raise impact_error(error) from error

    @app.get(
        "/projects/{project_id}/changes/{change_id}/unknowns",
        response_model=ImpactUnknownListResponse,
        dependencies=[Depends(guard)],
    )
    def change_unknowns(project_id: str, change_id: str) -> ImpactUnknownListResponse:
        try:
            return ImpactUnknownListResponse(unknowns=impact.unknowns(project_id, change_id))
        except ImpactServiceError as error:
            raise impact_error(error) from error

    @app.post(
        "/projects/{project_id}/changes/{change_id}/context-receipt",
        response_model=ContextReceiptResponse,
        dependencies=[Depends(guard)],
    )
    def create_context_receipt(project_id: str, change_id: str) -> ContextReceiptResponse:
        try:
            return ContextReceiptResponse(**impact.create_context_receipt(project_id, change_id))
        except ImpactServiceError as error:
            raise impact_error(error) from error

    @app.get(
        "/projects/{project_id}/changes/{change_id}/context-receipt",
        response_model=ContextReceiptResponse,
        dependencies=[Depends(guard)],
    )
    def get_context_receipt(project_id: str, change_id: str) -> ContextReceiptResponse:
        try:
            return ContextReceiptResponse(**impact.get_context_receipt(project_id, change_id))
        except ImpactServiceError as error:
            raise impact_error(error) from error

    @app.get(
        "/projects/{project_id}/behavior-candidates",
        response_model=BehaviorCandidateListResponse,
        dependencies=[Depends(guard)],
    )
    def behavior_candidates(project_id: str) -> BehaviorCandidateListResponse:
        try:
            return BehaviorCandidateListResponse(candidates=impact.behavior_candidates(project_id))
        except ImpactServiceError as error:
            raise impact_error(error) from error

    def candidate_action(
        project_id: str, candidate_id: str, action: str
    ) -> BehaviorCandidateResponse:
        try:
            return BehaviorCandidateResponse(
                **impact.set_candidate_status(project_id, candidate_id, action)
            )
        except ImpactServiceError as error:
            raise impact_error(error) from error

    @app.post(
        "/projects/{project_id}/behavior-candidates/{candidate_id}/dismiss",
        response_model=BehaviorCandidateResponse,
        dependencies=[Depends(guard)],
    )
    def dismiss_candidate(project_id: str, candidate_id: str) -> BehaviorCandidateResponse:
        return candidate_action(project_id, candidate_id, "dismiss")

    @app.post(
        "/projects/{project_id}/behavior-candidates/{candidate_id}/keep",
        response_model=BehaviorCandidateResponse,
        dependencies=[Depends(guard)],
    )
    def keep_candidate(project_id: str, candidate_id: str) -> BehaviorCandidateResponse:
        return candidate_action(project_id, candidate_id, "keep")

    @app.post(
        "/projects/{project_id}/behavior-candidates/{candidate_id}/prepare",
        response_model=BehaviorCandidateResponse,
        dependencies=[Depends(guard)],
    )
    def prepare_candidate(project_id: str, candidate_id: str) -> BehaviorCandidateResponse:
        candidate = candidate_action(project_id, candidate_id, "prepare")
        try:
            draft = behaviors.create_from_candidate(project_id, candidate_id)
        except BehaviorServiceError as error:
            raise phase4_error(error) from error
        return candidate.model_copy(update={"behavior_draft_id": draft["id"]})

    @app.get(
        "/projects/{project_id}/impact/summary",
        response_model=ImpactSummaryResponse,
        dependencies=[Depends(guard)],
    )
    def impact_summary(project_id: str) -> ImpactSummaryResponse:
        try:
            return ImpactSummaryResponse(**projects.impact_summary(project_id))
        except ProjectError as error:
            raise project_error(error) from error

    @app.get(
        "/projects/{project_id}/impact/search",
        response_model=ImpactSearchResponse,
        dependencies=[Depends(guard)],
    )
    def impact_search(
        project_id: str, query: str = Query(default="", max_length=240)
    ) -> ImpactSearchResponse:
        return ImpactSearchResponse(results=projects.impact_search(project_id, query))

    @app.get(
        "/projects/{project_id}/findings",
        response_model=ScanFindingListResponse,
        dependencies=[Depends(guard)],
    )
    def scan_findings(project_id: str) -> ScanFindingListResponse:
        return ScanFindingListResponse(findings=projects.findings(project_id))

    @app.post(
        "/projects/{project_id}/monitoring/pause",
        response_model=MonitoringResponse,
        dependencies=[Depends(guard)],
    )
    def pause_monitoring(project_id: str) -> MonitoringResponse:
        monitoring.pause(project_id)
        try:
            return MonitoringResponse(**projects.set_monitoring(project_id, False))
        except ProjectError as error:
            raise project_error(error) from error

    @app.post(
        "/projects/{project_id}/monitoring/resume",
        response_model=MonitoringResponse,
        dependencies=[Depends(guard)],
    )
    def resume_monitoring(project_id: str) -> MonitoringResponse:
        try:
            response = projects.set_monitoring(project_id, True)
            monitoring.resume(project_id)
            return MonitoringResponse(**response)
        except ProjectError as error:
            raise project_error(error) from error

    @app.post(
        "/projects/{project_id}/open-folder",
        response_model=OpenDataFolderResponse,
        dependencies=[Depends(guard)],
    )
    def open_project_folder(project_id: str) -> OpenDataFolderResponse:
        try:
            project = projects.get_model(project_id)
            method = _open_folder(str(project.canonical_root_path))
            logger.info("project_folder_open_requested project_id=%s method=%s", project_id, method)
            return OpenDataFolderResponse(opened=True, method=method)
        except ProjectError as error:
            raise project_error(error) from error

    @app.get(
        "/projects/{project_id}/behaviors",
        response_model=ProtectedBehaviorListResponse,
        dependencies=[Depends(guard)],
    )
    def list_behaviors(project_id: str) -> ProtectedBehaviorListResponse:
        try:
            return ProtectedBehaviorListResponse(behaviors=behaviors.list(project_id))
        except BehaviorServiceError as error:
            raise phase4_error(error) from error

    @app.post(
        "/projects/{project_id}/behaviors",
        response_model=ProtectedBehaviorResponse,
        dependencies=[Depends(guard)],
    )
    def create_behavior(
        project_id: str, request: BehaviorDraftRequest
    ) -> ProtectedBehaviorResponse:
        try:
            return ProtectedBehaviorResponse(
                **behaviors.create_draft(
                    project_id,
                    request.title,
                    request.description,
                    request.expected_outcome,
                    request.links,
                    request.criticality,
                    request.persona,
                    request.preconditions,
                    request.starting_state,
                    request.expected_assertions,
                    request.always_recheck,
                )
            )
        except BehaviorServiceError as error:
            raise phase4_error(error) from error

    @app.get(
        "/projects/{project_id}/behaviors/{behavior_id}",
        response_model=ProtectedBehaviorResponse,
        dependencies=[Depends(guard)],
    )
    def get_behavior(project_id: str, behavior_id: str) -> ProtectedBehaviorResponse:
        try:
            return ProtectedBehaviorResponse(**behaviors.get(project_id, behavior_id))
        except BehaviorServiceError as error:
            raise phase4_error(error) from error

    @app.post(
        "/projects/{project_id}/behaviors/{behavior_id}/versions",
        response_model=ProtectedBehaviorResponse,
        dependencies=[Depends(guard)],
    )
    def update_behavior(
        project_id: str, behavior_id: str, request: BehaviorDraftRequest
    ) -> ProtectedBehaviorResponse:
        try:
            return ProtectedBehaviorResponse(
                **behaviors.update(
                    project_id,
                    behavior_id,
                    request.title,
                    request.description,
                    request.expected_outcome,
                    request.criticality,
                    request.persona,
                    request.preconditions,
                    request.starting_state,
                    request.expected_assertions,
                    request.always_recheck,
                )
            )
        except BehaviorServiceError as error:
            raise phase4_error(error) from error

    @app.post(
        "/projects/{project_id}/behaviors/{behavior_id}/archive",
        response_model=ProtectedBehaviorResponse,
        dependencies=[Depends(guard)],
    )
    def archive_behavior(project_id: str, behavior_id: str) -> ProtectedBehaviorResponse:
        try:
            return ProtectedBehaviorResponse(**behaviors.archive(project_id, behavior_id))
        except BehaviorServiceError as error:
            raise phase4_error(error) from error

    @app.get(
        "/projects/{project_id}/behaviors/{behavior_id}/baseline",
        response_model=BehaviorBaselineResponse,
        dependencies=[Depends(guard)],
    )
    def current_behavior_baseline(project_id: str, behavior_id: str) -> BehaviorBaselineResponse:
        try:
            behavior = behaviors.get(project_id, behavior_id)
            baseline_id = behavior["last_accepted_baseline_id"]
            if not baseline_id:
                raise EvidenceServiceError("BASELINE_NOT_FOUND")
            return BehaviorBaselineResponse(**evidence.baseline(project_id, baseline_id))
        except (BehaviorServiceError, EvidenceServiceError) as error:
            raise phase4_error(error) from error

    @app.post(
        "/projects/{project_id}/behaviors/{behavior_id}/baseline/revoke",
        response_model=ActionResponse,
        dependencies=[Depends(guard)],
    )
    def revoke_behavior_baseline(
        project_id: str, behavior_id: str, request: BaselineRevokeRequest
    ) -> ActionResponse:
        try:
            result = evidence.revoke_baseline(
                project_id, behavior_id, request.delete_evidence, request.confirmation
            )
            return ActionResponse(status=result["status"])
        except EvidenceServiceError as error:
            raise phase4_error(error) from error

    @app.get(
        "/projects/{project_id}/runtime-configurations",
        response_model=RuntimeConfigurationListResponse,
        dependencies=[Depends(guard)],
    )
    @app.get(
        "/projects/{project_id}/runtimes",
        response_model=RuntimeConfigurationListResponse,
        dependencies=[Depends(guard)],
    )
    def list_runtimes(project_id: str) -> RuntimeConfigurationListResponse:
        try:
            return RuntimeConfigurationListResponse(runtimes=behaviors.runtimes(project_id))
        except BehaviorServiceError as error:
            raise phase4_error(error) from error

    @app.post(
        "/projects/{project_id}/runtime-configurations",
        response_model=RuntimeConfigurationResponse,
        dependencies=[Depends(guard)],
    )
    @app.post(
        "/projects/{project_id}/runtimes",
        response_model=RuntimeConfigurationResponse,
        dependencies=[Depends(guard)],
    )
    def configure_runtime(
        project_id: str, request: RuntimeConfigurationRequest
    ) -> RuntimeConfigurationResponse:
        try:
            return RuntimeConfigurationResponse(
                **behaviors.add_runtime(
                    project_id,
                    request.display_name,
                    request.base_url,
                    request.starting_path,
                    request.viewport_width,
                    request.viewport_height,
                    request.locale,
                    request.timezone,
                    request.browser_type,
                    request.capture_screenshots,
                    request.capture_trace,
                    request.capture_video,
                    request.capture_network,
                )
            )
        except BehaviorServiceError as error:
            raise phase4_error(error) from error

    @app.post(
        "/projects/{project_id}/runtime-configurations/{runtime_id}/test",
        response_model=ActionResponse,
        dependencies=[Depends(guard)],
    )
    def test_runtime_configuration(project_id: str, runtime_id: str) -> ActionResponse:
        try:
            return ActionResponse(status=behaviors.test_runtime(project_id, runtime_id)["status"])
        except BehaviorServiceError as error:
            raise phase4_error(error) from error

    @app.get(
        "/projects/{project_id}/captures",
        response_model=BrowserCaptureListResponse,
        dependencies=[Depends(guard)],
    )
    def list_captures(project_id: str) -> BrowserCaptureListResponse:
        try:
            return BrowserCaptureListResponse(captures=browser.list(project_id))
        except BrowserCaptureError as error:
            raise phase4_error(error) from error

    @app.post(
        "/projects/{project_id}/captures",
        response_model=BrowserCaptureResponse,
        dependencies=[Depends(guard)],
    )
    def start_capture(
        project_id: str, request: BrowserCaptureStartRequest
    ) -> BrowserCaptureResponse:
        try:
            return BrowserCaptureResponse(
                **browser.start(
                    project_id,
                    request.behavior_id,
                    request.runtime_configuration_id,
                    request.entry_url,
                )
            )
        except BrowserCaptureError as error:
            raise phase4_error(error) from error

    @app.get(
        "/projects/{project_id}/captures/{capture_id}",
        response_model=BrowserCaptureResponse,
        dependencies=[Depends(guard)],
    )
    def get_capture(project_id: str, capture_id: str) -> BrowserCaptureResponse:
        try:
            return BrowserCaptureResponse(**browser.get(project_id, capture_id))
        except BrowserCaptureError as error:
            raise phase4_error(error) from error

    @app.post(
        "/projects/{project_id}/captures/{capture_id}/stop",
        response_model=BrowserCaptureResponse,
        dependencies=[Depends(guard)],
    )
    def stop_capture(project_id: str, capture_id: str) -> BrowserCaptureResponse:
        try:
            return BrowserCaptureResponse(**browser.stop(project_id, capture_id))
        except BrowserCaptureError as error:
            raise phase4_error(error) from error

    @app.post(
        "/projects/{project_id}/captures/{capture_id}/pause",
        response_model=BrowserCaptureResponse,
        dependencies=[Depends(guard)],
    )
    def pause_capture(project_id: str, capture_id: str) -> BrowserCaptureResponse:
        try:
            return BrowserCaptureResponse(**browser.pause(project_id, capture_id))
        except BrowserCaptureError as error:
            raise phase4_error(error) from error

    @app.post(
        "/projects/{project_id}/captures/{capture_id}/resume",
        response_model=BrowserCaptureResponse,
        dependencies=[Depends(guard)],
    )
    def resume_capture(project_id: str, capture_id: str) -> BrowserCaptureResponse:
        try:
            return BrowserCaptureResponse(**browser.resume(project_id, capture_id))
        except BrowserCaptureError as error:
            raise phase4_error(error) from error

    @app.post(
        "/projects/{project_id}/captures/{capture_id}/review",
        response_model=BrowserCaptureResponse,
        dependencies=[Depends(guard)],
    )
    def review_capture(
        project_id: str, capture_id: str, request: CaptureReviewRequest
    ) -> BrowserCaptureResponse:
        try:
            return BrowserCaptureResponse(
                **browser.review(
                    project_id,
                    capture_id,
                    request.step_updates,
                    request.excluded_observation_ids,
                    request.expected_assertions,
                    request.notes,
                )
            )
        except BrowserCaptureError as error:
            raise phase4_error(error) from error

    @app.post(
        "/projects/{project_id}/captures/{capture_id}/cancel",
        response_model=BrowserCaptureResponse,
        dependencies=[Depends(guard)],
    )
    def cancel_capture(project_id: str, capture_id: str) -> BrowserCaptureResponse:
        try:
            return BrowserCaptureResponse(**browser.cancel(project_id, capture_id))
        except BrowserCaptureError as error:
            raise phase4_error(error) from error

    @app.post(
        "/projects/{project_id}/captures/{capture_id}/validate",
        response_model=ProbeRunResponse,
        dependencies=[Depends(guard)],
    )
    def validate_capture(
        project_id: str, capture_id: str, request: CaptureValidateRequest
    ) -> ProbeRunResponse:
        try:
            return ProbeRunResponse(
                **browser.validate(project_id, capture_id, request.runtime_profile_version_id)
            )
        except (BrowserCaptureError, ProbeServiceError, EvidenceServiceError) as error:
            raise phase4_error(error) from error

    @app.post(
        "/projects/{project_id}/captures/{capture_id}/validation-fixture-flow",
        response_model=ActionResponse,
        include_in_schema=False,
        dependencies=[Depends(guard)],
    )
    def validation_fixture_flow(project_id: str, capture_id: str) -> ActionResponse:
        try:
            return ActionResponse(status=browser.run_fixture_flow(project_id, capture_id)["status"])
        except BrowserCaptureError as error:
            raise phase4_error(error) from error

    @app.post(
        "/projects/{project_id}/captures/{capture_id}/accept-baseline",
        response_model=BehaviorBaselineResponse,
        dependencies=[Depends(guard)],
    )
    def accept_baseline(
        project_id: str, capture_id: str, request: BaselineAcceptRequest
    ) -> BehaviorBaselineResponse:
        try:
            baseline = evidence.accept_baseline(
                project_id, capture_id, request.reviewer, request.notes
            )
            bundle = evidence.get_bundle(project_id, str(baseline["evidence_bundle_id"]))
            run = probes.get_run(project_id, str(bundle["verification_run_id"]))
            behavior = behaviors.get(project_id, str(baseline["behavior_id"]))
            probes.create_milestone(
                project_id,
                str(run["snapshot_id"]),
                f"{behavior['display_name']} known good",
                str(baseline["behavior_id"]),
                str(baseline["behavior_version_id"]),
                str(run["probe_version_id"]),
                False,
            )
            return BehaviorBaselineResponse(**baseline)
        except (EvidenceServiceError, ProbeServiceError, BehaviorServiceError) as error:
            raise phase4_error(error) from error

    @app.get(
        "/projects/{project_id}/evidence/bundles/{bundle_id}",
        response_model=EvidenceBundleResponse,
        dependencies=[Depends(guard)],
    )
    def evidence_bundle(project_id: str, bundle_id: str) -> EvidenceBundleResponse:
        try:
            return EvidenceBundleResponse(**evidence.get_bundle(project_id, bundle_id))
        except EvidenceServiceError as error:
            raise phase4_error(error) from error

    @app.get(
        "/projects/{project_id}/evidence",
        response_model=EvidenceListResponse,
        dependencies=[Depends(guard)],
    )
    def list_evidence(project_id: str) -> EvidenceListResponse:
        try:
            return EvidenceListResponse(**evidence.list_evidence(project_id))
        except EvidenceServiceError as error:
            raise phase4_error(error) from error

    @app.get(
        "/projects/{project_id}/evidence/{artifact_id}",
        response_model=EvidenceArtifactResponse,
        dependencies=[Depends(guard)],
    )
    def evidence_artifact_canonical(project_id: str, artifact_id: str) -> EvidenceArtifactResponse:
        try:
            return EvidenceArtifactResponse(**evidence.artifact(project_id, artifact_id))
        except EvidenceServiceError as error:
            raise phase4_error(error) from error

    @app.get(
        "/projects/{project_id}/evidence/artifacts/{artifact_id}",
        response_model=EvidenceArtifactResponse,
        dependencies=[Depends(guard)],
    )
    def evidence_artifact(project_id: str, artifact_id: str) -> EvidenceArtifactResponse:
        try:
            return EvidenceArtifactResponse(**evidence.artifact(project_id, artifact_id))
        except EvidenceServiceError as error:
            raise phase4_error(error) from error

    @app.get(
        "/projects/{project_id}/evidence/artifacts/{artifact_id}/content",
        dependencies=[Depends(guard)],
    )
    def evidence_artifact_content(project_id: str, artifact_id: str) -> Response:
        try:
            content, media_type = evidence.artifact_content(project_id, artifact_id)
            return Response(
                content=content,
                media_type=media_type,
                headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
            )
        except EvidenceServiceError as error:
            raise phase4_error(error) from error

    @app.delete(
        "/projects/{project_id}/evidence/artifacts/{artifact_id}",
        response_model=ActionResponse,
        dependencies=[Depends(guard)],
    )
    def delete_evidence_artifact(project_id: str, artifact_id: str) -> ActionResponse:
        try:
            return ActionResponse(
                status=evidence.remove_review_artifact(project_id, artifact_id)["status"]
            )
        except EvidenceServiceError as error:
            raise phase4_error(error) from error

    @app.delete(
        "/projects/{project_id}/evidence/{artifact_id}",
        response_model=ActionResponse,
        dependencies=[Depends(guard)],
    )
    def delete_evidence_artifact_canonical(project_id: str, artifact_id: str) -> ActionResponse:
        return delete_evidence_artifact(project_id, artifact_id)

    @app.post(
        "/projects/{project_id}/evidence/{artifact_id}/open-local",
        response_model=ActionResponse,
        dependencies=[Depends(guard)],
    )
    def open_evidence_artifact(project_id: str, artifact_id: str) -> ActionResponse:
        try:
            _open_folder(str(evidence.artifact_local_path(project_id, artifact_id).parent))
            return ActionResponse(status="opened")
        except EvidenceServiceError as error:
            raise phase4_error(error) from error

    @app.post(
        "/projects/{project_id}/changes/{change_id}/protection-plan",
        response_model=ProtectionPlanResponse,
        dependencies=[Depends(guard)],
    )
    def create_protection_plan(project_id: str, change_id: str) -> ProtectionPlanResponse:
        try:
            return ProtectionPlanResponse(**protection.create(project_id, change_id))
        except ProtectionPlanError as error:
            raise phase5_error(error) from error

    @app.get(
        "/projects/{project_id}/changes/{change_id}/protection-plan",
        response_model=ProtectionPlanResponse,
        dependencies=[Depends(guard)],
    )
    def get_protection_plan(project_id: str, change_id: str) -> ProtectionPlanResponse:
        try:
            return ProtectionPlanResponse(**protection.get(project_id, change_id))
        except ProtectionPlanError as error:
            raise phase5_error(error) from error

    @app.post(
        "/projects/{project_id}/changes/{change_id}/verify",
        response_model=VerificationRunResponse,
        dependencies=[Depends(guard)],
    )
    def verify_required(
        project_id: str, change_id: str, request: VerificationStartRequest
    ) -> VerificationRunResponse:
        try:
            result = verification.start(project_id, change_id, request.plan_id, request.item_ids)
            project = projects.get(project_id)
            for finding in regressions.list(project_id):
                if finding.get("change_id") == change_id and finding.get("status") == "DETECTED":
                    productization.create_alert(
                        project_id=project_id,
                        change_id=change_id,
                        regression_id=str(finding["id"]),
                        category="REGRESSION",
                        severity="CRITICAL",
                        title_key="alerts.regressionTitle",
                        summary_key="alerts.regressionSummary",
                        parameters={"project": project["display_name"]},
                        deduplication_key=f"regression:{finding['id']}",
                        route={
                            "screen": "change",
                            "project_id": project_id,
                            "change_id": change_id,
                            "regression_id": finding["id"],
                        },
                    )
            return VerificationRunResponse(**result)
        except (VerificationError, GateError) as error:
            raise phase5_error(error) from error

    @app.get(
        "/projects/{project_id}/verification-runs/{run_id}",
        response_model=VerificationRunResponse,
        dependencies=[Depends(guard)],
    )
    def get_verification_run(project_id: str, run_id: str) -> VerificationRunResponse:
        try:
            return VerificationRunResponse(**verification.get_for_project(project_id, run_id))
        except VerificationError as error:
            raise phase5_error(error) from error

    @app.post(
        "/projects/{project_id}/verification-runs/{run_id}/cancel",
        response_model=VerificationRunResponse,
        dependencies=[Depends(guard)],
    )
    def cancel_verification(project_id: str, run_id: str) -> VerificationRunResponse:
        try:
            run = verification.get_for_project(project_id, run_id)
            return VerificationRunResponse(
                **verification.cancel(project_id, run["change_id"], run_id)
            )
        except VerificationError as error:
            raise phase5_error(error) from error

    @app.post(
        "/projects/{project_id}/verification-runs/{run_id}/retry",
        response_model=VerificationRunResponse,
        dependencies=[Depends(guard)],
    )
    def retry_verification(project_id: str, run_id: str) -> VerificationRunResponse:
        try:
            return VerificationRunResponse(**verification.retry(project_id, run_id))
        except VerificationError as error:
            raise phase5_error(error) from error

    @app.post(
        "/projects/{project_id}/verification-runs/{run_id}/human-result",
        response_model=VerificationRunResponse,
        dependencies=[Depends(guard)],
    )
    def human_verification_result(
        project_id: str,
        run_id: str,
        request: HumanVerificationRequest,
    ) -> VerificationRunResponse:
        try:
            run = verification.get_for_project(project_id, run_id)
            return VerificationRunResponse(
                **verification.attest(
                    project_id,
                    run["change_id"],
                    run_id,
                    request.run_item_id,
                    request.result,
                    request.note,
                    request.confirmed,
                    request.evidence_reference,
                )
            )
        except (VerificationError, GateError) as error:
            raise phase5_error(error) from error

    @app.get(
        "/projects/{project_id}/changes/{change_id}/gate",
        response_model=GateDecisionResponse,
        dependencies=[Depends(guard)],
    )
    def get_gate(project_id: str, change_id: str) -> GateDecisionResponse:
        try:
            return GateDecisionResponse(**gate.latest(project_id, change_id))
        except GateError as error:
            raise phase5_error(error) from error

    @app.post(
        "/projects/{project_id}/changes/{change_id}/gate/evaluate",
        response_model=GateDecisionResponse,
        dependencies=[Depends(guard)],
    )
    def evaluate_gate(
        project_id: str, change_id: str, request: VerificationStartRequest
    ) -> GateDecisionResponse:
        try:
            result = gate.evaluate(project_id, change_id, request.plan_id)
            project = projects.get(project_id)
            alert_values = {
                "BLOCKED": ("HIGH", "alerts.blockedTitle", "alerts.blockedSummary"),
                "NEEDS_REVIEW": ("WARNING", "alerts.reviewTitle", "alerts.reviewSummary"),
                "VERIFIED_COMPLETE": ("INFO", "alerts.verifiedTitle", "alerts.verifiedSummary"),
            }
            if result["state"] in alert_values:
                severity, title_key, summary_key = alert_values[result["state"]]
                productization.create_alert(
                    project_id=project_id,
                    change_id=change_id,
                    gate_id=str(result["id"]),
                    category="GATE",
                    severity=severity,
                    title_key=title_key,
                    summary_key=summary_key,
                    parameters={"project": project["display_name"]},
                    deduplication_key=f"gate:{project_id}:{change_id}:{result['state']}",
                    route={
                        "screen": "change",
                        "project_id": project_id,
                        "change_id": change_id,
                        "gate_id": result["id"],
                    },
                )
            return GateDecisionResponse(**result)
        except GateError as error:
            raise phase5_error(error) from error

    @app.get(
        "/projects/{project_id}/regressions",
        response_model=RegressionListResponse,
        dependencies=[Depends(guard)],
    )
    def list_regressions(project_id: str) -> RegressionListResponse:
        return RegressionListResponse(regressions=regressions.list(project_id))

    @app.get(
        "/projects/{project_id}/regressions/{regression_id}",
        dependencies=[Depends(guard)],
    )
    def get_regression(project_id: str, regression_id: str) -> dict[str, object]:
        try:
            return regressions.get(project_id, regression_id)
        except RuntimeError as error:
            raise phase5_error(error) from error

    @app.get(
        "/projects/{project_id}/regressions/{regression_id}/detail",
        response_model=RegressionDetailAggregateResponse,
        dependencies=[Depends(guard)],
    )
    def get_regression_detail(
        project_id: str, regression_id: str
    ) -> RegressionDetailAggregateResponse:
        try:
            return RegressionDetailAggregateResponse(
                **product_truth.regression_detail(project_id, regression_id)
            )
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post(
        "/projects/{project_id}/regressions/{regression_id}/repair-context",
        response_model=RepairContextResponse,
        dependencies=[Depends(guard)],
    )
    def create_repair_context(project_id: str, regression_id: str) -> RepairContextResponse:
        try:
            return RepairContextResponse(**repair.create(project_id, regression_id))
        except RepairContextError as error:
            raise phase5_error(error) from error

    @app.get(
        "/projects/{project_id}/repair-contexts/{context_id}",
        response_model=RepairContextResponse,
        dependencies=[Depends(guard)],
    )
    def get_repair_context(project_id: str, context_id: str) -> RepairContextResponse:
        try:
            return RepairContextResponse(**repair.get(project_id, context_id))
        except RepairContextError as error:
            raise phase5_error(error) from error

    @app.post(
        "/projects/{project_id}/repair-contexts/{context_id}/copy",
        response_model=RepairContextCopyResponse,
        dependencies=[Depends(guard)],
    )
    def copy_repair_context(project_id: str, context_id: str) -> RepairContextCopyResponse:
        try:
            return RepairContextCopyResponse(**repair.copy_payload(project_id, context_id))
        except RepairContextError as error:
            raise phase5_error(error) from error

    @app.post(
        "/projects/{project_id}/repair-contexts/{context_id}/save-local",
        response_model=RepairContextSaveResponse,
        dependencies=[Depends(guard)],
    )
    def save_repair_context(project_id: str, context_id: str) -> RepairContextSaveResponse:
        try:
            return RepairContextSaveResponse(**repair.save_local(project_id, context_id))
        except RepairContextError as error:
            raise phase5_error(error) from error

    def product_error(error: ProductizationError) -> HTTPException:
        code = str(error)
        return HTTPException(status_code=404 if code.endswith("NOT_FOUND") else 409, detail=code)

    @app.get("/alerts", response_model=AlertListResponse, dependencies=[Depends(guard)])
    def list_alerts(
        project_id: str | None = None,
        state: str = "all",
        severity: str | None = None,
        category: str | None = None,
    ) -> AlertListResponse:
        return AlertListResponse(
            alerts=productization.list_alerts(
                project_id=project_id, state=state, severity=severity, category=category
            )
        )

    @app.get(
        "/alerts/unread-count", response_model=UnreadCountResponse, dependencies=[Depends(guard)]
    )
    def unread_alert_count() -> UnreadCountResponse:
        return UnreadCountResponse(count=productization.unread_count())

    @app.post(
        "/alerts/{alert_id}/read", response_model=AlertResponse, dependencies=[Depends(guard)]
    )
    def read_alert(alert_id: str) -> AlertResponse:
        try:
            return AlertResponse(**productization.set_alert_state(alert_id, "read"))
        except ProductizationError as error:
            raise product_error(error) from error

    @app.post(
        "/alerts/{alert_id}/unread", response_model=AlertResponse, dependencies=[Depends(guard)]
    )
    def unread_alert(alert_id: str) -> AlertResponse:
        try:
            return AlertResponse(**productization.set_alert_state(alert_id, "unread"))
        except ProductizationError as error:
            raise product_error(error) from error

    @app.post(
        "/alerts/{alert_id}/resolve", response_model=AlertResponse, dependencies=[Depends(guard)]
    )
    def resolve_alert(alert_id: str) -> AlertResponse:
        try:
            return AlertResponse(**productization.set_alert_state(alert_id, "resolve"))
        except ProductizationError as error:
            raise product_error(error) from error

    @app.post("/alerts/clear-resolved", dependencies=[Depends(guard)])
    def clear_resolved_alerts() -> dict[str, int]:
        return {"cleared": productization.clear_resolved()}

    @app.get("/settings/notifications", dependencies=[Depends(guard)])
    def notification_settings() -> dict[str, object]:
        return productization.notification_settings()

    @app.put("/settings/notifications", dependencies=[Depends(guard)])
    def update_notification_settings(request: NotificationSettingsRequest) -> dict[str, object]:
        return productization.update_notification_settings(request.model_dump(exclude_none=True))

    @app.get("/settings/quiet-mode", dependencies=[Depends(guard)])
    def quiet_mode() -> dict[str, object]:
        return productization.quiet()

    @app.post("/settings/quiet-mode/start", dependencies=[Depends(guard)])
    def start_quiet_mode(request: QuietModeStartRequest) -> dict[str, object]:
        try:
            return productization.start_quiet(request.duration, request.allow_critical)
        except ProductizationError as error:
            raise product_error(error) from error

    @app.post("/settings/quiet-mode/stop", dependencies=[Depends(guard)])
    def stop_quiet_mode() -> dict[str, object]:
        return productization.stop_quiet()

    @app.get("/projects/{project_id}/notification-preferences", dependencies=[Depends(guard)])
    def project_notification_preferences(project_id: str) -> dict[str, object]:
        try:
            return productization.project_notifications(project_id)
        except ProductizationError as error:
            raise product_error(error) from error

    @app.put("/projects/{project_id}/notification-preferences", dependencies=[Depends(guard)])
    def update_project_notification_preferences(
        project_id: str, request: ProjectNotificationRequest
    ) -> dict[str, object]:
        try:
            return productization.project_notifications(project_id, request.muted)
        except ProductizationError as error:
            raise product_error(error) from error

    @app.get("/projects/{project_id}/capabilities", dependencies=[Depends(guard)])
    def project_capabilities(project_id: str) -> dict[str, object]:
        try:
            return productization.capabilities(project_id)
        except ProductizationError as error:
            raise product_error(error) from error

    @app.get("/projects/{project_id}/deletion-preview", dependencies=[Depends(guard)])
    def project_deletion_preview(project_id: str) -> dict[str, object]:
        try:
            return productization.lifecycle_preview(project_id)
        except ProductizationError as error:
            raise product_error(error) from error

    @app.post("/projects/{project_id}/disconnect", dependencies=[Depends(guard)])
    def disconnect_project(project_id: str) -> dict[str, object]:
        monitoring.pause(project_id)
        try:
            return productization.disconnect(project_id)
        except ProductizationError as error:
            raise product_error(error) from error

    @app.post("/projects/{project_id}/reconnect", dependencies=[Depends(guard)])
    def reconnect_project(project_id: str, request: ProjectLocationRequest) -> dict[str, object]:
        try:
            if request.path:
                result = technical_preview.reconnect_or_relocate(
                    project_id, request.path, "reconnect"
                )
            else:
                result = productization.reconnect(project_id)
            monitoring.start(project_id)
            return result
        except (ProductizationError, TechnicalPreviewError) as error:
            raise product_error(ProductizationError(str(error))) from error

    @app.post("/projects/{project_id}/relocate", dependencies=[Depends(guard)])
    def relocate_project(project_id: str, request: ProjectRelocateRequest) -> dict[str, object]:
        try:
            return technical_preview.reconnect_or_relocate(project_id, request.path, "relocate")
        except (ProductizationError, TechnicalPreviewError) as error:
            raise product_error(ProductizationError(str(error))) from error

    @app.post("/projects/{project_id}/delete-local-data", dependencies=[Depends(guard)])
    def delete_project_local_data(
        project_id: str, request: ProjectDeleteRequest
    ) -> dict[str, object]:
        monitoring.pause(project_id)
        try:
            return productization.delete_local_data(project_id, request.confirmation)
        except ProductizationError as error:
            raise product_error(error) from error

    @app.get("/app/background-status", dependencies=[Depends(guard)])
    def background_status() -> dict[str, object]:
        return productization.background()

    @app.put("/app/background-status", dependencies=[Depends(guard)])
    def update_background_status(request: BackgroundSettingsRequest) -> dict[str, object]:
        return productization.background(request.keep_running_on_close, request.start_at_login)

    @app.get("/app/start-at-login", dependencies=[Depends(guard)])
    def start_at_login() -> dict[str, object]:
        return productization.background()

    @app.put("/app/start-at-login", dependencies=[Depends(guard)])
    def update_start_at_login(request: BackgroundSettingsRequest) -> dict[str, object]:
        return productization.background(start_at_login=request.start_at_login)

    def phase7_error(error: Exception) -> HTTPException:
        code = str(getattr(error, "code", str(error) or "PHASE7_OPERATION_FAILED"))
        if code.endswith("_NOT_FOUND"):
            status = 404
        elif code.endswith("_UNAVAILABLE") or code.endswith("_FAILED_OPEN"):
            status = 503
        elif code.endswith("_REQUIRED") or code.endswith("_INVALID") or code.endswith("_DENIED"):
            status = 400
        else:
            status = 409
        return HTTPException(status_code=status, detail=code)

    def phase8_error(error: Exception) -> HTTPException:
        code = str(getattr(error, "code", str(error) or "PHASE8_OPERATION_FAILED"))
        if code.endswith("_NOT_FOUND"):
            status = 404
        elif code.endswith("_INVALID") or code.endswith("_REJECTED") or code.endswith("_REQUIRED"):
            status = 400
        elif code.endswith("_UNAVAILABLE"):
            status = 503
        else:
            status = 409
        return HTTPException(status_code=status, detail=code)

    @app.post(
        "/projects/{project_id}/runtime/detect",
        response_model=RuntimeDetectionResponse,
        dependencies=[Depends(guard)],
    )
    def detect_runtime_profiles(project_id: str) -> RuntimeDetectionResponse:
        try:
            return RuntimeDetectionResponse(**runtime_profiles.detect(project_id))
        except RuntimeProfileServiceError as error:
            raise phase7_error(error) from error

    @app.get(
        "/projects/{project_id}/runtime-profiles",
        response_model=RuntimeProfileListResponse,
        dependencies=[Depends(guard)],
    )
    def list_runtime_profiles(project_id: str) -> RuntimeProfileListResponse:
        try:
            return RuntimeProfileListResponse(profiles=runtime_profiles.list(project_id))
        except RuntimeProfileServiceError as error:
            raise phase7_error(error) from error

    @app.post(
        "/projects/{project_id}/runtime-profiles",
        response_model=RuntimeProfileResponse,
        dependencies=[Depends(guard)],
    )
    def create_runtime_profile(
        project_id: str, request: RuntimeProfileCreateRequest
    ) -> RuntimeProfileResponse:
        try:
            return RuntimeProfileResponse(
                **runtime_profiles.create_or_version(project_id, **request.model_dump())
            )
        except RuntimeProfileServiceError as error:
            raise phase7_error(error) from error

    @app.get(
        "/projects/{project_id}/runtime-profiles/{profile_id}",
        response_model=RuntimeProfileResponse,
        dependencies=[Depends(guard)],
    )
    def get_runtime_profile(project_id: str, profile_id: str) -> RuntimeProfileResponse:
        try:
            return RuntimeProfileResponse(**runtime_profiles.get(project_id, profile_id))
        except RuntimeProfileServiceError as error:
            raise phase7_error(error) from error

    @app.post(
        "/projects/{project_id}/runtime-profiles/{profile_id}/validate",
        response_model=RuntimeProfileResponse,
        dependencies=[Depends(guard)],
    )
    def validate_runtime_profile(project_id: str, profile_id: str) -> RuntimeProfileResponse:
        try:
            return RuntimeProfileResponse(**runtime_profiles.validate(project_id, profile_id))
        except RuntimeProfileServiceError as error:
            raise phase7_error(error) from error

    @app.post(
        "/projects/{project_id}/runtime-profiles/{profile_id}/start",
        response_model=RuntimeInstanceResponse,
        dependencies=[Depends(guard)],
    )
    def start_runtime_profile(project_id: str, profile_id: str) -> RuntimeInstanceResponse:
        try:
            return RuntimeInstanceResponse(**runtime_profiles.start(project_id, profile_id))
        except RuntimeProfileServiceError as error:
            raise phase7_error(error) from error

    @app.post(
        "/projects/{project_id}/runtime-profiles/{profile_id}/stop",
        response_model=RuntimeInstanceResponse,
        dependencies=[Depends(guard)],
    )
    def stop_runtime_profile(project_id: str, profile_id: str) -> RuntimeInstanceResponse:
        try:
            return RuntimeInstanceResponse(**runtime_profiles.stop(project_id, profile_id))
        except RuntimeProfileServiceError as error:
            raise phase7_error(error) from error

    @app.get(
        "/projects/{project_id}/runtime-instances",
        response_model=RuntimeInstanceListResponse,
        dependencies=[Depends(guard)],
    )
    def list_runtime_instances(project_id: str) -> RuntimeInstanceListResponse:
        try:
            return RuntimeInstanceListResponse(instances=runtime_profiles.instances(project_id))
        except RuntimeProfileServiceError as error:
            raise phase7_error(error) from error

    @app.get(
        "/projects/{project_id}/snapshots",
        response_model=SnapshotListResponse,
        dependencies=[Depends(guard)],
    )
    def list_snapshots(project_id: str) -> SnapshotListResponse:
        try:
            return SnapshotListResponse(snapshots=snapshots.list(project_id))
        except SnapshotServiceError as error:
            raise phase7_error(error) from error

    @app.post(
        "/projects/{project_id}/snapshots",
        response_model=SnapshotSummaryResponse,
        dependencies=[Depends(guard)],
    )
    def create_snapshot(project_id: str, request: SnapshotCreateRequest) -> SnapshotSummaryResponse:
        try:
            return SnapshotSummaryResponse(
                **snapshots.create(project_id, request.episode_id, request.creation_reason)
            )
        except (SnapshotServiceError, OSError, ValueError) as error:
            raise phase7_error(error) from error

    @app.get(
        "/projects/{project_id}/snapshots/{snapshot_id}",
        response_model=SnapshotDetailResponse,
        dependencies=[Depends(guard)],
    )
    def get_snapshot(project_id: str, snapshot_id: str) -> SnapshotDetailResponse:
        try:
            return SnapshotDetailResponse(**snapshots.get(project_id, snapshot_id))
        except SnapshotServiceError as error:
            raise phase7_error(error) from error

    @app.post(
        "/projects/{project_id}/snapshots/{snapshot_id}/materialize",
        response_model=SnapshotMaterializationResponse,
        dependencies=[Depends(guard)],
    )
    def materialize_snapshot(project_id: str, snapshot_id: str) -> SnapshotMaterializationResponse:
        try:
            return SnapshotMaterializationResponse(**snapshots.materialize(project_id, snapshot_id))
        except (SnapshotServiceError, OSError, ValueError) as error:
            raise phase7_error(error) from error

    @app.post(
        "/projects/{project_id}/snapshots/{snapshot_id}/pin",
        response_model=SnapshotSummaryResponse,
        dependencies=[Depends(guard)],
    )
    def pin_snapshot(project_id: str, snapshot_id: str) -> SnapshotSummaryResponse:
        try:
            return SnapshotSummaryResponse(**snapshots.pin(project_id, snapshot_id, True))
        except SnapshotServiceError as error:
            raise phase7_error(error) from error

    @app.post(
        "/projects/{project_id}/snapshots/{snapshot_id}/unpin",
        response_model=SnapshotSummaryResponse,
        dependencies=[Depends(guard)],
    )
    def unpin_snapshot(project_id: str, snapshot_id: str) -> SnapshotSummaryResponse:
        try:
            return SnapshotSummaryResponse(**snapshots.pin(project_id, snapshot_id, False))
        except SnapshotServiceError as error:
            raise phase7_error(error) from error

    @app.get(
        "/projects/{project_id}/episodes",
        response_model=SourceEpisodeListResponse,
        dependencies=[Depends(guard)],
    )
    def list_source_episodes(project_id: str) -> SourceEpisodeListResponse:
        try:
            projects.get_model(project_id)
            return SourceEpisodeListResponse(episodes=episodes.list(project_id))
        except (ProjectError, ValueError) as error:
            raise phase7_error(error) from error

    @app.get(
        "/projects/{project_id}/activity",
        response_model=ProjectActivityAggregateResponse,
        dependencies=[Depends(guard)],
    )
    def project_activity(
        project_id: str,
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=25, ge=1, le=50),
    ) -> ProjectActivityAggregateResponse:
        try:
            return ProjectActivityAggregateResponse(
                **product_truth.activity(project_id, offset, limit)
            )
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.get(
        "/projects/{project_id}/episodes/{episode_id}",
        response_model=SourceEpisodeResponse,
        dependencies=[Depends(guard)],
    )
    def get_source_episode(project_id: str, episode_id: str) -> SourceEpisodeResponse:
        try:
            return SourceEpisodeResponse(**episodes.get(project_id, episode_id))
        except ValueError as error:
            raise phase7_error(error) from error

    @app.get(
        "/projects/{project_id}/episodes/{episode_id}/summary",
        response_model=EpisodeDetailAggregateResponse,
        dependencies=[Depends(guard)],
    )
    def get_episode_summary(project_id: str, episode_id: str) -> EpisodeDetailAggregateResponse:
        try:
            return EpisodeDetailAggregateResponse(
                **product_truth.episode_detail(project_id, episode_id)
            )
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.get(
        "/projects/{project_id}/episodes/{episode_id}/probe-selection",
        response_model=ProbeSelectionResponse,
        dependencies=[Depends(guard)],
    )
    def get_episode_probe_selection(project_id: str, episode_id: str) -> ProbeSelectionResponse:
        try:
            return ProbeSelectionResponse(**probes.select_impacted(project_id, episode_id))
        except ProbeServiceError as error:
            raise phase7_error(error) from error

    @app.post(
        "/projects/{project_id}/milestones/known-good",
        response_model=SnapshotMilestoneResponse,
        dependencies=[Depends(guard)],
    )
    def create_known_good_milestone(
        project_id: str, request: MilestoneCreateRequest
    ) -> SnapshotMilestoneResponse:
        try:
            return SnapshotMilestoneResponse(
                **probes.create_milestone(project_id, **request.model_dump())
            )
        except ProbeServiceError as error:
            raise phase7_error(error) from error

    @app.get(
        "/projects/{project_id}/milestones",
        response_model=SnapshotMilestoneListResponse,
        dependencies=[Depends(guard)],
    )
    def list_known_good_milestones(project_id: str) -> SnapshotMilestoneListResponse:
        try:
            return SnapshotMilestoneListResponse(milestones=probes.milestones(project_id))
        except ProbeServiceError as error:
            raise phase7_error(error) from error

    @app.get(
        "/projects/{project_id}/probes",
        response_model=ProbeListResponse,
        dependencies=[Depends(guard)],
    )
    def list_probes(project_id: str) -> ProbeListResponse:
        try:
            return ProbeListResponse(probes=probes.list(project_id))
        except ProbeServiceError as error:
            raise phase7_error(error) from error

    @app.post(
        "/projects/{project_id}/probes",
        response_model=ProbeDefinitionResponse,
        dependencies=[Depends(guard)],
    )
    def create_probe(project_id: str, request: ProbeCreateRequest) -> ProbeDefinitionResponse:
        try:
            return ProbeDefinitionResponse(**probes.create(project_id, **request.model_dump()))
        except ProbeServiceError as error:
            raise phase7_error(error) from error

    @app.get(
        "/projects/{project_id}/probes/{probe_id}",
        response_model=ProbeDefinitionResponse,
        dependencies=[Depends(guard)],
    )
    def get_probe(project_id: str, probe_id: str) -> ProbeDefinitionResponse:
        try:
            return ProbeDefinitionResponse(**probes.get(project_id, probe_id))
        except ProbeServiceError as error:
            raise phase7_error(error) from error

    @app.post(
        "/projects/{project_id}/probes/{probe_id}/run",
        response_model=ProbeRunResponse,
        dependencies=[Depends(guard)],
    )
    def run_probe(project_id: str, probe_id: str, request: ProbeRunRequest) -> ProbeRunResponse:
        try:
            return ProbeRunResponse(**probes.run(project_id, probe_id, request.snapshot_id))
        except ProbeServiceError as error:
            raise phase7_error(error) from error

    @app.post(
        "/projects/{project_id}/probes/{probe_id}/cancel",
        response_model=ActionResponse,
        dependencies=[Depends(guard)],
    )
    def cancel_probe(project_id: str, probe_id: str) -> ActionResponse:
        return ActionResponse(status=probes.cancel(project_id, probe_id)["status"])

    @app.post(
        "/projects/{project_id}/regressions/{regression_id}/repair-workspace",
        response_model=RepairWorkspaceResponse,
        dependencies=[Depends(guard)],
    )
    def create_repair_workspace(project_id: str, regression_id: str) -> RepairWorkspaceResponse:
        try:
            return RepairWorkspaceResponse(**repair_workspaces.create(project_id, regression_id))
        except RepairWorkspaceServiceError as error:
            raise phase7_error(error) from error

    @app.get(
        "/projects/{project_id}/repair-workspaces/{workspace_id}",
        response_model=RepairWorkspaceResponse,
        dependencies=[Depends(guard)],
    )
    def get_repair_workspace(project_id: str, workspace_id: str) -> RepairWorkspaceResponse:
        try:
            return RepairWorkspaceResponse(**repair_workspaces.get(project_id, workspace_id))
        except RepairWorkspaceServiceError as error:
            raise phase7_error(error) from error

    @app.post(
        "/projects/{project_id}/repair-workspaces/{workspace_id}/open",
        response_model=ActionResponse,
        dependencies=[Depends(guard)],
    )
    def open_repair_workspace(
        project_id: str, workspace_id: str, request: RepairWorkspaceOpenRequest
    ) -> ActionResponse:
        try:
            result = repair_workspaces.open(project_id, workspace_id, request.target)
            return ActionResponse(status=result["status"])
        except RepairWorkspaceServiceError as error:
            raise phase7_error(error) from error

    @app.delete(
        "/projects/{project_id}/repair-workspaces/{workspace_id}",
        response_model=ActionResponse,
        dependencies=[Depends(guard)],
    )
    def delete_repair_workspace(project_id: str, workspace_id: str) -> ActionResponse:
        try:
            return ActionResponse(
                status=repair_workspaces.delete(project_id, workspace_id)["status"]
            )
        except RepairWorkspaceServiceError as error:
            raise phase7_error(error) from error

    @app.post(
        "/projects/{project_id}/repair-workspaces/{workspace_id}/candidates",
        response_model=RepairCandidateResponse,
        dependencies=[Depends(guard)],
    )
    def create_repair_candidate(project_id: str, workspace_id: str) -> RepairCandidateResponse:
        try:
            return RepairCandidateResponse(**repair_candidates.create(project_id, workspace_id))
        except RepairCandidateServiceError as error:
            raise phase8_error(error) from error

    @app.get(
        "/projects/{project_id}/repair-candidates/{candidate_id}",
        response_model=RepairCandidateResponse,
        dependencies=[Depends(guard)],
    )
    def get_repair_candidate(project_id: str, candidate_id: str) -> RepairCandidateResponse:
        try:
            return RepairCandidateResponse(**repair_candidates.get(project_id, candidate_id))
        except RepairCandidateServiceError as error:
            raise phase8_error(error) from error

    @app.post(
        "/projects/{project_id}/repair-candidates/{candidate_id}/refresh",
        response_model=RepairCandidateResponse,
        dependencies=[Depends(guard)],
    )
    def refresh_repair_candidate(project_id: str, candidate_id: str) -> RepairCandidateResponse:
        try:
            return RepairCandidateResponse(**repair_candidates.refresh(project_id, candidate_id))
        except RepairCandidateServiceError as error:
            raise phase8_error(error) from error

    @app.post(
        "/projects/{project_id}/repair-candidates/{candidate_id}/exclude",
        response_model=RepairCandidateResponse,
        dependencies=[Depends(guard)],
    )
    def exclude_repair_candidate_paths(
        project_id: str, candidate_id: str, request: CandidateExcludeRequest
    ) -> RepairCandidateResponse:
        try:
            return RepairCandidateResponse(
                **repair_candidates.exclude(project_id, candidate_id, request.paths)
            )
        except RepairCandidateServiceError as error:
            raise phase8_error(error) from error

    @app.post(
        "/projects/{project_id}/repair-candidates/{candidate_id}/restore-workspace-file",
        response_model=RepairCandidateResponse,
        dependencies=[Depends(guard)],
    )
    def restore_repair_workspace_file(
        project_id: str, candidate_id: str, request: CandidateRestoreRequest
    ) -> RepairCandidateResponse:
        try:
            return RepairCandidateResponse(
                **repair_candidates.restore_workspace_file(
                    project_id, candidate_id, request.relative_path
                )
            )
        except RepairCandidateServiceError as error:
            raise phase8_error(error) from error

    @app.get(
        "/projects/{project_id}/repair-candidates/{candidate_id}/diff",
        response_model=CandidateDiffResponse,
        dependencies=[Depends(guard)],
    )
    def repair_candidate_diff(
        project_id: str,
        candidate_id: str,
        relative_path: str = Query(min_length=1, max_length=2000),
    ) -> CandidateDiffResponse:
        try:
            return CandidateDiffResponse(
                **repair_candidates.diff(project_id, candidate_id, relative_path)
            )
        except RepairCandidateServiceError as error:
            raise phase8_error(error) from error

    @app.post(
        "/projects/{project_id}/repair-candidates/{candidate_id}/validate",
        response_model=RepairValidationResponse,
        dependencies=[Depends(guard)],
    )
    def validate_repair_candidate(project_id: str, candidate_id: str) -> RepairValidationResponse:
        try:
            return RepairValidationResponse(**repair_validations.validate(project_id, candidate_id))
        except RepairValidationServiceError as error:
            raise phase8_error(error) from error

    @app.post(
        "/projects/{project_id}/repair-candidates/{candidate_id}/cancel-validation",
        response_model=ActionResponse,
        dependencies=[Depends(guard)],
    )
    def cancel_repair_candidate_validation(project_id: str, candidate_id: str) -> ActionResponse:
        try:
            return ActionResponse(**repair_validations.cancel(project_id, candidate_id))
        except RepairValidationServiceError as error:
            raise phase8_error(error) from error

    @app.post(
        "/projects/{project_id}/repair-candidates/{candidate_id}/apply/prepare",
        response_model=ApplyTransactionResponse,
        dependencies=[Depends(guard)],
    )
    def prepare_repair_apply(project_id: str, candidate_id: str) -> ApplyTransactionResponse:
        try:
            return ApplyTransactionResponse(**safe_apply.prepare(project_id, candidate_id))
        except (SafeApplyServiceError, SnapshotServiceError) as error:
            raise phase8_error(error) from error

    @app.post(
        "/projects/{project_id}/repair-candidates/{candidate_id}/apply/confirm",
        response_model=ApplyTransactionResponse,
        dependencies=[Depends(guard)],
    )
    def confirm_repair_apply(
        project_id: str, candidate_id: str, request: ApplyConfirmRequest
    ) -> ApplyTransactionResponse:
        if not request.deliberate_confirmation:
            raise HTTPException(status_code=400, detail="APPLY_DELIBERATE_CONFIRMATION_REQUIRED")
        try:
            pending = [
                item
                for item in safe_apply.pending()
                if item["project_id"] == project_id
                and item["candidate_id"] == candidate_id
                and item["state"] == "AWAITING_CONFIRMATION"
            ]
            if len(pending) != 1:
                raise SafeApplyServiceError("APPLY_TRANSACTION_NOT_FOUND")
            return ApplyTransactionResponse(
                **safe_apply.confirm(project_id, str(pending[0]["id"]), request.confirmation_nonce)
            )
        except (SafeApplyServiceError, SnapshotServiceError) as error:
            raise phase8_error(error) from error

    @app.get(
        "/projects/{project_id}/apply-transactions/{transaction_id}",
        response_model=ApplyTransactionResponse,
        dependencies=[Depends(guard)],
    )
    def get_apply_transaction(project_id: str, transaction_id: str) -> ApplyTransactionResponse:
        try:
            return ApplyTransactionResponse(**safe_apply.get(project_id, transaction_id))
        except SafeApplyServiceError as error:
            raise phase8_error(error) from error

    @app.post(
        "/projects/{project_id}/apply-transactions/{transaction_id}/cancel",
        response_model=ApplyTransactionResponse,
        dependencies=[Depends(guard)],
    )
    def cancel_apply_transaction(project_id: str, transaction_id: str) -> ApplyTransactionResponse:
        try:
            return ApplyTransactionResponse(**safe_apply.cancel(project_id, transaction_id))
        except SafeApplyServiceError as error:
            raise phase8_error(error) from error

    @app.post(
        "/projects/{project_id}/apply-transactions/{transaction_id}/rollback",
        response_model=ApplyTransactionResponse,
        dependencies=[Depends(guard)],
    )
    def rollback_apply_transaction(
        project_id: str, transaction_id: str
    ) -> ApplyTransactionResponse:
        try:
            return ApplyTransactionResponse(**safe_apply.rollback(project_id, transaction_id))
        except (SafeApplyServiceError, SnapshotServiceError) as error:
            raise phase8_error(error) from error

    @app.post(
        "/projects/{project_id}/apply-transactions/{transaction_id}/resume-verification",
        response_model=ApplyTransactionResponse,
        dependencies=[Depends(guard)],
    )
    def resume_apply_verification(project_id: str, transaction_id: str) -> ApplyTransactionResponse:
        try:
            return ApplyTransactionResponse(
                **safe_apply.resume_verification(project_id, transaction_id)
            )
        except (SafeApplyServiceError, SnapshotServiceError) as error:
            raise phase8_error(error) from error

    @app.get(
        "/recovery/pending",
        response_model=ApplyTransactionListResponse,
        dependencies=[Depends(guard)],
    )
    def pending_recovery() -> ApplyTransactionListResponse:
        return ApplyTransactionListResponse(transactions=safe_apply.pending())

    @app.post(
        "/recovery/{transaction_id}/attempt",
        response_model=ApplyTransactionResponse,
        dependencies=[Depends(guard)],
    )
    def attempt_recovery(transaction_id: str) -> ApplyTransactionResponse:
        pending = [item for item in safe_apply.pending() if item["id"] == transaction_id]
        if not pending:
            raise HTTPException(status_code=404, detail="APPLY_TRANSACTION_NOT_FOUND")
        try:
            return ApplyTransactionResponse(
                **safe_apply.rollback(
                    str(pending[0]["project_id"]), transaction_id, reason="MANUAL_RECOVERY"
                )
            )
        except (SafeApplyServiceError, SnapshotServiceError) as error:
            raise phase8_error(error) from error

    @app.post(
        "/recovery/{transaction_id}/create-bundle",
        response_model=RecoveryBundleResponse,
        dependencies=[Depends(guard)],
    )
    def create_recovery_bundle(transaction_id: str) -> RecoveryBundleResponse:
        pending = [item for item in safe_apply.pending() if item["id"] == transaction_id]
        if not pending:
            raise HTTPException(status_code=404, detail="APPLY_TRANSACTION_NOT_FOUND")
        try:
            return RecoveryBundleResponse(
                **safe_apply.create_recovery_bundle(str(pending[0]["project_id"]), transaction_id)
            )
        except SafeApplyServiceError as error:
            raise phase8_error(error) from error

    @app.post(
        "/projects/{project_id}/repair-workspaces/{workspace_id}/export-portable",
        response_model=PortableRepairResponse,
        dependencies=[Depends(guard)],
    )
    def export_portable_repair(
        project_id: str, workspace_id: str, request: PortableRepairRequest
    ) -> PortableRepairResponse:
        try:
            return PortableRepairResponse(
                **portable_repairs.export(project_id, workspace_id, request.selected_paths)
            )
        except PortableRepairError as error:
            raise phase8_error(error) from error

    @app.post(
        "/demo-lab/create",
        response_model=DemoLabResponse,
        dependencies=[Depends(guard)],
    )
    def create_demo_lab(request: DemoLabCreateRequest) -> DemoLabResponse:
        try:
            return DemoLabResponse(**demo_lab.create(request.selected_parent))
        except (DemoLabServiceError, ProjectError, SnapshotServiceError) as error:
            raise phase8_error(error) from error

    @app.get(
        "/demo-lab/{demo_id}",
        response_model=DemoLabResponse,
        dependencies=[Depends(guard)],
    )
    def get_demo_lab(demo_id: str) -> DemoLabResponse:
        try:
            return DemoLabResponse(**demo_lab.get(demo_id))
        except DemoLabServiceError as error:
            raise phase8_error(error) from error

    @app.post(
        "/demo-lab/{demo_id}/inject-regression",
        response_model=DemoLabResponse,
        dependencies=[Depends(guard)],
    )
    def demo_inject_regression(demo_id: str) -> DemoLabResponse:
        try:
            return DemoLabResponse(**demo_lab.inject_regression(demo_id))
        except (DemoLabServiceError, SnapshotServiceError) as error:
            raise phase8_error(error) from error

    @app.post(
        "/demo-lab/{demo_id}/create-bad-candidate",
        response_model=DemoLabResponse,
        dependencies=[Depends(guard)],
    )
    def demo_bad_candidate(demo_id: str) -> DemoLabResponse:
        try:
            return DemoLabResponse(**demo_lab.candidate(demo_id, valid=False))
        except (
            DemoLabServiceError,
            RepairCandidateServiceError,
            RepairValidationServiceError,
        ) as error:
            raise phase8_error(error) from error

    @app.post(
        "/demo-lab/{demo_id}/create-valid-candidate",
        response_model=DemoLabResponse,
        dependencies=[Depends(guard)],
    )
    def demo_valid_candidate(demo_id: str) -> DemoLabResponse:
        try:
            return DemoLabResponse(**demo_lab.candidate(demo_id, valid=True))
        except (
            DemoLabServiceError,
            RepairCandidateServiceError,
            RepairValidationServiceError,
        ) as error:
            raise phase8_error(error) from error

    @app.post(
        "/demo-lab/{demo_id}/apply-valid",
        response_model=DemoLabResponse,
        dependencies=[Depends(guard)],
    )
    def demo_apply_valid(demo_id: str) -> DemoLabResponse:
        try:
            return DemoLabResponse(**demo_lab.apply_valid(demo_id))
        except (DemoLabServiceError, SafeApplyServiceError, SnapshotServiceError) as error:
            raise phase8_error(error) from error

    @app.post(
        "/demo-lab/{demo_id}/simulate-post-apply-failure",
        response_model=DemoLabResponse,
        dependencies=[Depends(guard)],
    )
    def demo_post_apply_failure(demo_id: str) -> DemoLabResponse:
        try:
            return DemoLabResponse(**demo_lab.simulate_post_apply_failure(demo_id))
        except (DemoLabServiceError, SafeApplyServiceError, SnapshotServiceError) as error:
            raise phase8_error(error) from error

    @app.post(
        "/demo-lab/{demo_id}/test-crash/{fault_point}",
        response_model=DemoLabResponse,
        dependencies=[Depends(guard)],
        include_in_schema=False,
    )
    def demo_test_crash(demo_id: str, fault_point: str) -> DemoLabResponse:
        if os.environ.get("MELLOWYAK_DEMO_TEST_MODE") != "1":
            raise HTTPException(status_code=404, detail="DEMO_TEST_MODE_DISABLED")

        def terminate_at(selected: str) -> None:
            if selected == fault_point:
                os._exit(86)

        try:
            return DemoLabResponse(**demo_lab.apply_with_fault(demo_id, fault_point, terminate_at))
        except (DemoLabServiceError, SafeApplyServiceError, SnapshotServiceError) as error:
            raise phase8_error(error) from error

    @app.post(
        "/demo-lab/{demo_id}/reset",
        response_model=DemoLabResponse,
        dependencies=[Depends(guard)],
    )
    def reset_demo_lab(demo_id: str) -> DemoLabResponse:
        try:
            return DemoLabResponse(**demo_lab.reset(demo_id))
        except (DemoLabServiceError, SnapshotServiceError) as error:
            raise phase8_error(error) from error

    @app.post(
        "/self-test",
        response_model=ProductSelfTestResponse,
        dependencies=[Depends(guard)],
    )
    def run_product_self_test() -> ProductSelfTestResponse:
        return ProductSelfTestResponse(**self_test.run())

    @app.post(
        "/diagnostics/self-test",
        response_model=ProductSelfTestResponse,
        dependencies=[Depends(guard)],
    )
    def run_diagnostic_product_self_test() -> ProductSelfTestResponse:
        return ProductSelfTestResponse(**self_test.run())

    @app.get(
        "/self-test/{run_id}",
        response_model=ProductSelfTestResponse,
        dependencies=[Depends(guard)],
    )
    def get_product_self_test(run_id: str) -> ProductSelfTestResponse:
        try:
            return ProductSelfTestResponse(**self_test.get(run_id))
        except RuntimeError as error:
            raise phase8_error(error) from error

    @app.post(
        "/self-test/{run_id}/cancel",
        response_model=ActionResponse,
        dependencies=[Depends(guard)],
    )
    def cancel_product_self_test(run_id: str) -> ActionResponse:
        return ActionResponse(**self_test.cancel(run_id))

    @app.post(
        "/self-test/{run_id}/export",
        response_model=LocalExportResponse,
        dependencies=[Depends(guard)],
    )
    def export_product_self_test(run_id: str) -> LocalExportResponse:
        try:
            return LocalExportResponse(**self_test.export(run_id))
        except RuntimeError as error:
            raise phase8_error(error) from error

    def technical_preview_error(error: TechnicalPreviewError) -> HTTPException:
        code = str(error)
        if code.endswith(("NOT_FOUND", "MISSING")):
            status = 404
        elif code.endswith(("INVALID", "REQUIRED")):
            status = 400
        else:
            status = 409
        return HTTPException(status_code=status, detail=code)

    @app.get(
        "/app/onboarding",
        response_model=OnboardingResponse,
        dependencies=[Depends(guard)],
    )
    def onboarding_state() -> OnboardingResponse:
        return OnboardingResponse(**technical_preview.onboarding())

    @app.put(
        "/app/onboarding",
        response_model=OnboardingResponse,
        dependencies=[Depends(guard)],
    )
    def update_onboarding(request: OnboardingUpdateRequest) -> OnboardingResponse:
        try:
            result = technical_preview.update_onboarding(
                current_step=request.current_step,
                selected_path=request.selected_path,
                completed=request.completed,
            )
            return OnboardingResponse(**result)
        except TechnicalPreviewError as error:
            raise technical_preview_error(error) from error

    @app.post(
        "/app/onboarding/replay",
        response_model=OnboardingResponse,
        dependencies=[Depends(guard)],
    )
    def replay_onboarding() -> OnboardingResponse:
        return OnboardingResponse(**technical_preview.replay_onboarding())

    @app.get("/app/activity-mode", dependencies=[Depends(guard)])
    def activity_mode() -> dict[str, object]:
        return technical_preview.preferences()

    @app.put("/app/activity-mode", dependencies=[Depends(guard)])
    def update_activity_mode(request: ActivityModeRequest) -> dict[str, object]:
        try:
            return technical_preview.preferences(request.activity_mode)
        except TechnicalPreviewError as error:
            raise technical_preview_error(error) from error

    @app.get("/projects/{project_id}/identity-preview", dependencies=[Depends(guard)])
    def project_identity_preview(project_id: str, path: str) -> dict[str, object]:
        try:
            return technical_preview.identity_preview(project_id, path)
        except (OSError, TechnicalPreviewError) as error:
            wrapped = (
                error
                if isinstance(error, TechnicalPreviewError)
                else TechnicalPreviewError("PROJECT_PATH_MISSING")
            )
            raise technical_preview_error(wrapped) from error

    @app.get("/tray/state", dependencies=[Depends(guard)])
    def tray_state() -> dict[str, object]:
        return technical_preview.tray_state()

    @app.post("/notifications/activate", dependencies=[Depends(guard)])
    def activate_notification(request: NotificationActivationRequest) -> dict[str, object]:
        return technical_preview.validate_notification_route(request.route)

    @app.get(
        "/diagnostics",
        response_model=DiagnosticsResponse,
        dependencies=[Depends(guard)],
    )
    def diagnostics() -> DiagnosticsResponse:
        return DiagnosticsResponse(**technical_preview.diagnostics())

    @app.get(
        "/diagnostics/overview",
        response_model=DiagnosticsOverviewAggregateResponse,
        dependencies=[Depends(guard)],
    )
    def diagnostics_overview() -> DiagnosticsOverviewAggregateResponse:
        return DiagnosticsOverviewAggregateResponse(**product_truth.diagnostics_overview())

    @app.get("/workflow/state-model", dependencies=[Depends(guard)])
    def workflow_state_model() -> dict[str, dict[str, list[str]]]:
        return state_model()

    @app.post("/diagnostics/storage-integrity", dependencies=[Depends(guard)])
    def storage_integrity() -> dict[str, object]:
        return technical_preview.storage_integrity()

    @app.post("/diagnostics/performance", dependencies=[Depends(guard)])
    def record_performance_metric(request: PerformanceMetricRequest) -> dict[str, object]:
        try:
            return technical_preview.record_performance_metric(
                request.metric,
                request.duration_ms,
                route=request.route,
                project_id=request.project_id,
            )
        except TechnicalPreviewError as error:
            raise technical_preview_error(error) from error

    @app.post("/diagnostics/support-bundle", dependencies=[Depends(guard)])
    def export_support_bundle() -> dict[str, object]:
        return technical_preview.export_support_bundle()

    @app.get("/diagnostics/support-bundles/{bundle_id}", dependencies=[Depends(guard)])
    def support_bundle(bundle_id: str) -> dict[str, object]:
        try:
            return technical_preview.support_bundle(bundle_id)
        except TechnicalPreviewError as error:
            raise technical_preview_error(error) from error

    @app.get("/updates/status", dependencies=[Depends(guard)])
    def updater_status() -> dict[str, object]:
        return technical_preview.updater_status()

    @app.post("/updates/check", dependencies=[Depends(guard)])
    def record_update_check(request: UpdateCheckRecordRequest) -> dict[str, object]:
        try:
            return technical_preview.record_update_check(request.result)
        except TechnicalPreviewError as error:
            raise technical_preview_error(error) from error

    @app.post(
        "/updates/test/validate",
        dependencies=[Depends(guard)],
        include_in_schema=False,
    )
    def validate_update_fixture(request: UpdateFixtureRequest) -> dict[str, object]:
        if os.environ.get("MELLOWYAK_DEMO_TEST_MODE") != "1":
            raise HTTPException(status_code=404, detail="DEMO_TEST_MODE_DISABLED")
        try:
            return technical_preview.validate_update_fixture(request.fixture)
        except TechnicalPreviewError as error:
            raise technical_preview_error(error) from error

    @app.get("/package-acceptance", dependencies=[Depends(guard)])
    def package_acceptance() -> dict[str, object]:
        return technical_preview.package_acceptance()

    @app.post(
        "/package-acceptance/run",
        dependencies=[Depends(guard)],
        include_in_schema=False,
    )
    def record_package_acceptance(
        request: PackageAcceptanceRecordRequest,
    ) -> dict[str, object]:
        if os.environ.get("MELLOWYAK_DEMO_TEST_MODE") != "1":
            raise HTTPException(status_code=404, detail="DEMO_TEST_MODE_DISABLED")
        try:
            return technical_preview.record_package_acceptance(request.status, request.summary)
        except TechnicalPreviewError as error:
            raise technical_preview_error(error) from error

    @app.get("/events", response_model=LocalEventListResponse, dependencies=[Depends(guard)])
    def local_events(after: int = Query(default=0, ge=0)) -> LocalEventListResponse:
        return LocalEventListResponse(events=events.after(after))

    def stop_background_services() -> None:
        monitoring.stop_all()
        episodes.stop_all()
        runtime_profiles.stop_all()
        scans.stop_all()
        browser.close()

    app.router.on_shutdown.append(stop_background_services)
    episodes.recover()
    runtime_profiles.recover()
    safe_apply.recover_pending()
    monitoring.start_persisted()

    logger.info("engine_runtime_ready schema=%s", schema_version)
    return app
