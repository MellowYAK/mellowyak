from __future__ import annotations

import os
from collections import Counter, defaultdict
from enum import StrEnum
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.db.models import Project, ProjectScanRun, RuntimeProfileVersion
from mellowyak_engine.runtime_profiles.detection import RuntimeDetectionService
from mellowyak_engine.scanning.policy import (
    BUILD_OUTPUT_DIRS,
    CACHE_DIRS,
    DEFAULT_EXCLUDED_DIRS,
    FileClassification,
    build_ignore_spec,
    classify_path,
    iter_candidates,
    normalize_relative_path,
)

MAX_DETAIL_ITEMS_PER_CLASS = 20


class CompatibilityState(StrEnum):
    READY_FOR_PASSIVE_MONITORING = "READY_FOR_PASSIVE_MONITORING"
    READY_FOR_AUTOMATIC_CHECKS = "READY_FOR_AUTOMATIC_CHECKS"
    NEEDS_RUNTIME_APPROVAL = "NEEDS_RUNTIME_APPROVAL"
    NEEDS_SETUP = "NEEDS_SETUP"
    OBSERVE_ONLY = "OBSERVE_ONLY"
    SUPPORTED_WITH_LIMITS = "SUPPORTED_WITH_LIMITS"
    UNSUPPORTED = "UNSUPPORTED"
    ERROR = "ERROR"


class CompatibilityError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _structures(root: Path, runtime_types: set[str], package_roots: set[str]) -> list[str]:
    result: list[str] = []
    if (root / ".git").exists():
        result.append("GIT_REPOSITORY")
    else:
        result.append("GIT_LESS_PROJECT")
    if (root / "pnpm-workspace.yaml").is_file():
        result.append("NODE_WORKSPACE")
    elif package_roots - {"."}:
        result.append("NESTED_PACKAGES")
    if "PYTHON" in runtime_types:
        result.append("PYTHON_PROJECT")
    if "NODE" in runtime_types:
        result.append("NODE_PROJECT")
    if (root / "Cargo.toml").is_file():
        result.append("CARGO_WORKSPACE")
    if len(runtime_types) > 1:
        result.append("MIXED_POLYGLOT")
    return list(dict.fromkeys(result))


def _excluded_directories(root: Path) -> tuple[list[dict[str, str]], int]:
    ignore = build_ignore_spec(root)
    details: list[dict[str, str]] = []
    count = 0
    for current, directories, _ in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        relative_dir = current_path.relative_to(root).as_posix()
        retained: list[str] = []
        for directory in sorted(directories):
            path = current_path / directory
            relative = normalize_relative_path(f"{relative_dir}/{directory}")
            reason = ""
            if path.is_symlink():
                reason = "file.reason.symlink_directory_not_traversed"
            elif directory in DEFAULT_EXCLUDED_DIRS:
                reason = (
                    "file.reason.build_output"
                    if directory in BUILD_OUTPUT_DIRS
                    else "file.reason.cache_directory"
                    if directory in CACHE_DIRS
                    else "file.reason.default_excluded_directory"
                )
            elif ignore.match_file(f"{relative}/"):
                reason = "file.reason.project_ignore_rule"
            if reason:
                count += 1
                if len(details) < 100:
                    details.append({"path": relative, "reason": reason})
            else:
                retained.append(directory)
        directories[:] = retained
    return details, count


def assess_project_path(
    root: Path,
    *,
    project_alias: str | None = None,
    approved_runtime_types: set[str] | None = None,
    scan: ProjectScanRun | None = None,
) -> dict[str, Any]:
    try:
        resolved = root.expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise CompatibilityError("PROJECT_ROOT_UNAVAILABLE") from error
    if not resolved.is_dir():
        raise CompatibilityError("PROJECT_ROOT_NOT_DIRECTORY")
    approved = {item.upper() for item in approved_runtime_types or set()}
    report = RuntimeDetectionService().detect(resolved)
    candidates, ignored_count = iter_candidates(resolved)
    counts: Counter[str] = Counter()
    samples: dict[str, list[dict[str, str]]] = defaultdict(list)
    for candidate in candidates:
        classification, reason = classify_path(
            candidate.relative_path, symlink_outside=candidate.symlink_outside
        )
        counts[str(classification)] += 1
        if len(samples[str(classification)]) < MAX_DETAIL_ITEMS_PER_CLASS:
            samples[str(classification)].append({"path": candidate.relative_path, "reason": reason})
    excluded_directories, excluded_directory_count = _excluded_directories(resolved)
    counts[FileClassification.IGNORED] += ignored_count + excluded_directory_count

    runtime_types = {item.runtime_type for item in report.detections}
    package_roots = {str(item.metadata.get("package_root", ".")) for item in report.detections}
    runtimes: list[dict[str, Any]] = []
    missing: list[str] = []
    known_limits: list[str] = []
    available_probes: set[str] = set()
    for item in report.detections:
        metadata = item.metadata
        executable_name = Path(item.executable).name if item.executable else None
        runtime = {
            "runtime_type": item.runtime_type,
            "adapter_name": item.adapter_name,
            "adapter_version": item.adapter_version,
            "confidence": str(item.confidence),
            "runtime_version": item.version,
            "runtime_owner": metadata.get("runtime_owner", "PROJECT_ROOT"),
            "workspace_root": metadata.get("workspace_root", "."),
            "package_root": metadata.get("package_root", "."),
            "package_manager": metadata.get("package_manager"),
            "executable": executable_name,
            "scripts": list(metadata.get("scripts", ())),
            "test_commands": list(metadata.get("test_commands", ())),
            "development_commands": list(metadata.get("development_commands", ())),
            "expected_ports": list(metadata.get("expected_ports", ())),
            "health_checks": list(metadata.get("health_checks", ())),
            "approved": item.runtime_type in approved,
            "limitations": list(item.limitations),
        }
        runtimes.append(runtime)
        known_limits.extend(item.limitations)
        if item.executable is None and item.runtime_type in {"NODE", "PYTHON", "GENERIC_PROCESS"}:
            missing.append(f"{item.runtime_type}_EXECUTABLE")
        if item.runtime_type in {"NODE", "PYTHON", "GENERIC_PROCESS"}:
            available_probes.update(("CLI", "TEST", "PROCESS"))
        frameworks = set(metadata.get("frameworks", ()))
        if frameworks & {
            "REACT",
            "VITE",
            "NEXT",
            "EXPRESS",
            "FLASK",
            "FASTAPI",
            "DJANGO",
            "DATASETTE",
        }:
            available_probes.add("HTTP")
        if frameworks & {"REACT", "VITE", "NEXT", "FLASK", "FASTAPI", "DJANGO", "DATASETTE"}:
            available_probes.add("BROWSER")
    known_limits.extend(failure.reason for failure in report.failures)
    supported_files = sum(
        counts[item]
        for item in (
            FileClassification.SOURCE,
            FileClassification.TEST,
            FileClassification.DEPENDENCY_MANIFEST,
            FileClassification.DEPENDENCY_LOCK,
        )
    )
    unsupported_files = counts[FileClassification.UNSUPPORTED]
    if not report.detections:
        state = CompatibilityState.OBSERVE_ONLY
        known_limits.append("compatibility.limit.no_supported_runtime_detected")
        safe_next_action = "compatibility.action.continue_passive_observation"
    elif missing:
        state = CompatibilityState.NEEDS_SETUP
        safe_next_action = "compatibility.action.complete_local_setup"
    elif not approved.intersection(runtime_types):
        state = CompatibilityState.NEEDS_RUNTIME_APPROVAL
        safe_next_action = "compatibility.action.review_and_approve_runtime"
    elif scan is None or scan.status != "completed":
        state = CompatibilityState.READY_FOR_PASSIVE_MONITORING
        safe_next_action = "compatibility.action.complete_initial_scan"
    elif known_limits or unsupported_files:
        state = CompatibilityState.SUPPORTED_WITH_LIMITS
        safe_next_action = "compatibility.action.review_limits"
    else:
        state = CompatibilityState.READY_FOR_AUTOMATIC_CHECKS
        safe_next_action = "compatibility.action.approve_automatic_checks"
    automatic = bool(
        state
        in {CompatibilityState.READY_FOR_AUTOMATIC_CHECKS, CompatibilityState.SUPPORTED_WITH_LIMITS}
        and approved.intersection(runtime_types)
        and available_probes
    )
    return {
        "project_alias": (project_alias or resolved.name)[:240],
        "state": str(state),
        "detected_structure": _structures(resolved, runtime_types, package_roots),
        "source": {
            "path_alias": f"…/{resolved.name}",
            "git_available": (resolved / ".git").exists(),
            "source_remains_local": True,
        },
        "inventory": {
            "total_candidates": len(candidates),
            "included_files": supported_files,
            "excluded_items": counts[FileClassification.IGNORED]
            + counts[FileClassification.GENERATED]
            + counts[FileClassification.BUILD_OUTPUT]
            + counts[FileClassification.CACHE]
            + counts[FileClassification.SENSITIVE],
            "unsupported_files": unsupported_files,
            "sensitive_files": counts[FileClassification.SENSITIVE],
            "classification_counts": {item.value: counts[item] for item in FileClassification},
            "classification_samples": dict(samples),
            "excluded_directories": excluded_directories,
        },
        "runtimes": runtimes,
        "approved_runtimes": sorted(approved.intersection(runtime_types)),
        "available_probe_types": sorted(available_probes),
        "passive_monitoring_ready": True,
        "automatic_checks_eligible": automatic,
        "missing_prerequisites": sorted(set(missing)),
        "external_service_requirement": "UNKNOWN_NOT_EXECUTED",
        "known_limitations": sorted(set(known_limits)),
        "unknowns": [
            "compatibility.unknown.omitted_behaviors",
            "compatibility.unknown.unexecuted_scripts",
            "compatibility.unknown.external_service_requirements",
        ],
        "safe_next_action": safe_next_action,
        "assessment_scope": "INSTALLATION_AND_PROJECT_SPECIFIC",
    }


class ProjectCompatibilityService:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self.sessions = sessions

    def assess(self, project_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            project = session.get(Project, project_id)
            if project is None or project.archived_at is not None:
                raise CompatibilityError("PROJECT_NOT_FOUND")
            root = Path(project.repository_root_path or project.canonical_root_path or "")
            approved = set(
                session.scalars(
                    select(RuntimeProfileVersion.runtime_type).where(
                        RuntimeProfileVersion.project_id == project_id,
                        RuntimeProfileVersion.approved_at.is_not(None),
                    )
                ).all()
            )
            scan = session.scalars(
                select(ProjectScanRun)
                .where(ProjectScanRun.project_id == project_id)
                .order_by(ProjectScanRun.started_at.desc())
                .limit(1)
            ).first()
            alias = project.display_name
            session.expunge(scan) if scan is not None else None
        return assess_project_path(
            root,
            project_alias=alias,
            approved_runtime_types=approved,
            scan=scan,
        )
