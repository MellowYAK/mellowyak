from __future__ import annotations

import sqlite3
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from alembic.config import Config
from sqlalchemy import Engine, create_engine, event, select, text
from sqlalchemy.orm import sessionmaker

from alembic import command
from mellowyak_engine import APP_VERSION, ENGINE_VERSION
from mellowyak_engine.db.models import AppSetting, AuditEvent, EngineRun, Installation
from mellowyak_engine.storage.paths import StoragePaths


def _configure_sqlite(connection: sqlite3.Connection, _record: object) -> None:
    cursor = connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def _alembic_config_path() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root is not None:
        return Path(frozen_root) / "alembic.ini"
    return Path(__file__).resolve().parents[3] / "alembic.ini"


class LocalDatabase:
    def __init__(self, paths: StoragePaths) -> None:
        self.paths = paths
        self.engine: Engine = create_engine(
            f"sqlite:///{paths.sqlite_file}", connect_args={"check_same_thread": False}
        )
        event.listen(self.engine, "connect", _configure_sqlite)
        self.sessions = sessionmaker(bind=self.engine, expire_on_commit=False)

    def migrate(self) -> str:
        backup = self.paths.backups / "migration-previous.sqlite3"
        existed = self.paths.sqlite_file.exists()
        if existed:
            with (
                sqlite3.connect(self.paths.sqlite_file) as source,
                sqlite3.connect(backup) as target,
            ):
                source.backup(target)
        config = Config(str(_alembic_config_path()))
        config.set_main_option("sqlalchemy.url", f"sqlite:///{self.paths.sqlite_file}")
        try:
            command.upgrade(config, "head")
        except Exception:
            self.engine.dispose()
            if existed and backup.exists():
                with (
                    sqlite3.connect(backup) as source,
                    sqlite3.connect(self.paths.sqlite_file) as target,
                ):
                    source.backup(target)
            elif self.paths.sqlite_file.exists():
                self.paths.sqlite_file.unlink()
            raise
        return self.schema_version()

    def schema_version(self) -> str:
        with self.engine.connect() as connection:
            result = connection.execute(text("SELECT version_num FROM alembic_version"))
            return str(result.scalar_one())

    def sqlite_pragmas(self) -> dict[str, object]:
        with self.engine.connect() as connection:
            return {
                "journal_mode": str(connection.execute(text("PRAGMA journal_mode")).scalar_one()),
                "foreign_keys": int(connection.execute(text("PRAGMA foreign_keys")).scalar_one()),
                "busy_timeout": int(connection.execute(text("PRAGMA busy_timeout")).scalar_one()),
            }

    def ensure_installation(self) -> Installation:
        now = datetime.now(UTC)
        with self.sessions.begin() as session:
            installation = session.scalars(select(Installation).limit(1)).first()
            if installation is None:
                installation = Installation(
                    id=str(uuid.uuid4()),
                    created_at=now,
                    last_started_at=now,
                    app_version=APP_VERSION,
                    engine_version=ENGINE_VERSION,
                )
                session.add(installation)
            else:
                installation.last_started_at = now
                installation.app_version = APP_VERSION
                installation.engine_version = ENGINE_VERSION
            session.flush()
            return installation

    def record_start(self, installation_id: str) -> str:
        run_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        with self.sessions.begin() as session:
            session.add(EngineRun(id=run_id, installation_id=installation_id, started_at=now))
            session.add(AuditEvent(event_type="engine_started", created_at=now, details_json="{}"))
        return run_id

    def installation(self) -> Installation:
        with self.sessions() as session:
            return session.scalars(select(Installation).limit(1)).one()

    def set_setting(self, key: str, value: str) -> None:
        now = datetime.now(UTC)
        with self.sessions.begin() as session:
            setting = session.get(AppSetting, key)
            if setting is None:
                session.add(AppSetting(key=key, value=value, updated_at=now))
            else:
                setting.value = value
                setting.updated_at = now

    def get_setting(self, key: str) -> str | None:
        with self.sessions() as session:
            setting = session.get(AppSetting, key)
            return setting.value if setting else None
