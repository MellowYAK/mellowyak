from __future__ import annotations

import platform
import subprocess
import time
from dataclasses import dataclass

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mellowyak_engine import APP_VERSION, ENGINE_VERSION
from mellowyak_engine.api.schemas import (
    HandshakeResponse,
    HealthResponse,
    InstallationResponse,
    OpenDataFolderResponse,
    PrivacySettingsResponse,
    ReadinessResponse,
    StoragePathsResponse,
)
from mellowyak_engine.core.logging import configure_logging
from mellowyak_engine.db.database import LocalDatabase
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
    runtime = EngineRuntime(
        settings=settings,
        paths=paths,
        database=database,
        schema_version=schema_version,
        installation_id=installation.id,
        run_id=run_id,
        started_monotonic=time.monotonic(),
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

    logger.info("engine_runtime_ready schema=%s", schema_version)
    return app
