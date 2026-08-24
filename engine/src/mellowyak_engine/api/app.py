from __future__ import annotations

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
    BaselineAcceptRequest,
    BaselineRevokeRequest,
    BehaviorBaselineResponse,
    BehaviorCandidateListResponse,
    BehaviorCandidateResponse,
    BehaviorDraftRequest,
    BrowserCaptureListResponse,
    BrowserCaptureResponse,
    BrowserCaptureStartRequest,
    CaptureReviewRequest,
    ChangeImpactResponse,
    ChangeIntentRequest,
    ChangeListResponse,
    ContextReceiptResponse,
    CurrentChangeResponse,
    EvidenceArtifactResponse,
    EvidenceBundleResponse,
    EvidenceListResponse,
    GateDecisionResponse,
    GitStateResponse,
    HandshakeResponse,
    HealthResponse,
    HumanVerificationRequest,
    ImpactAnalyzeRequest,
    ImpactPathListResponse,
    ImpactSearchResponse,
    ImpactSummaryResponse,
    ImpactUnknownListResponse,
    InstallationResponse,
    LocalEventListResponse,
    MonitoringResponse,
    OpenDataFolderResponse,
    PrivacySettingsResponse,
    ProjectCreateRequest,
    ProjectDetectionResponse,
    ProjectDetectRequest,
    ProjectListResponse,
    ProjectResponse,
    ProtectedBehaviorListResponse,
    ProtectedBehaviorResponse,
    ProtectionPlanResponse,
    ReadinessResponse,
    RegressionListResponse,
    RepairContextCopyResponse,
    RepairContextResponse,
    RepairContextSaveResponse,
    RuntimeConfigurationListResponse,
    RuntimeConfigurationRequest,
    RuntimeConfigurationResponse,
    ScanFindingListResponse,
    ScanRunResponse,
    StoragePathsResponse,
    VerificationRunResponse,
    VerificationStartRequest,
)
from mellowyak_engine.behaviors.service import BehaviorService, BehaviorServiceError
from mellowyak_engine.browser.service import BrowserCaptureError, BrowserCaptureService
from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.core.logging import configure_logging
from mellowyak_engine.db.database import LocalDatabase
from mellowyak_engine.evidence.service import EvidenceService, EvidenceServiceError
from mellowyak_engine.evidence.store import EvidenceStore
from mellowyak_engine.gate.service import GateError, GateService
from mellowyak_engine.impact.models import TraversalPolicy
from mellowyak_engine.impact.service import ImpactService, ImpactServiceError
from mellowyak_engine.monitoring.service import MonitoringService
from mellowyak_engine.projects.service import ProjectError, ProjectService
from mellowyak_engine.protection.service import ProtectionPlanError, ProtectionPlanService
from mellowyak_engine.regression.service import RegressionService
from mellowyak_engine.repair.service import RepairContextError, RepairContextService
from mellowyak_engine.scanning.service import ScanCoordinator, SourceScanner
from mellowyak_engine.security.auth import SessionTokenGuard
from mellowyak_engine.settings.config import EngineSettings
from mellowyak_engine.storage.paths import StoragePaths
from mellowyak_engine.verification.service import VerificationError, VerificationService


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
    monitoring = MonitoringService(projects, scans)
    impact = ImpactService(database.sessions, events)
    behaviors = BehaviorService(database.sessions, events)
    evidence = EvidenceService(database.sessions, EvidenceStore(paths.evidence), events)
    browser = BrowserCaptureService(database.sessions, evidence, events)
    protection = ProtectionPlanService(database.sessions, events)
    gate = GateService(database.sessions, events, evidence)
    regressions = RegressionService(database.sessions, events)
    repair = RepairContextService(database.sessions, paths.root, events)
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
        allow_methods=["GET", "POST", "DELETE"],
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
            project = projects.create(request.path, request.display_name, request.monitoring_mode)
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
            return BehaviorBaselineResponse(
                **evidence.accept_baseline(project_id, capture_id, request.reviewer, request.notes)
            )
        except EvidenceServiceError as error:
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
            return VerificationRunResponse(
                **verification.start(project_id, change_id, request.plan_id, request.item_ids)
            )
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
            return GateDecisionResponse(**gate.evaluate(project_id, change_id, request.plan_id))
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

    @app.get("/events", response_model=LocalEventListResponse, dependencies=[Depends(guard)])
    def local_events(after: int = Query(default=0, ge=0)) -> LocalEventListResponse:
        return LocalEventListResponse(events=events.after(after))

    def stop_background_services() -> None:
        monitoring.stop_all()
        scans.stop_all()
        browser.close()

    app.router.on_shutdown.append(stop_background_services)
    monitoring.start_persisted()

    logger.info("engine_runtime_ready schema=%s", schema_version)
    return app
