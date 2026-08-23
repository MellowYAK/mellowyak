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
