from __future__ import annotations

import platform
import subprocess
import time
from dataclasses import dataclass

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mellowyak_engine import APP_VERSION, ENGINE_VERSION
from mellowyak_engine.api.schemas import (
    ActionResponse,
    ChangeListResponse,
    GitStateResponse,
    HandshakeResponse,
    HealthResponse,
    ImpactSearchResponse,
    ImpactSummaryResponse,
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
    ReadinessResponse,
    ScanFindingListResponse,
    ScanRunResponse,
    StoragePathsResponse,
)
from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.core.logging import configure_logging
from mellowyak_engine.db.database import LocalDatabase
from mellowyak_engine.monitoring.service import MonitoringService
from mellowyak_engine.projects.service import ProjectError, ProjectService
from mellowyak_engine.scanning.service import ScanCoordinator, SourceScanner
from mellowyak_engine.security.auth import SessionTokenGuard
from mellowyak_engine.settings.config import EngineSettings
from mellowyak_engine.storage.paths import StoragePaths


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
        allow_methods=["GET", "POST"],
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

    @app.get("/events", response_model=LocalEventListResponse, dependencies=[Depends(guard)])
    def local_events(after: int = Query(default=0, ge=0)) -> LocalEventListResponse:
        return LocalEventListResponse(events=events.after(after))

    def stop_background_services() -> None:
        monitoring.stop_all()
        scans.stop_all()

    app.router.on_shutdown.append(stop_background_services)
    monitoring.start_persisted()

    logger.info("engine_runtime_ready schema=%s", schema_version)
    return app
