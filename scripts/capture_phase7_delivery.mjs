#!/usr/bin/env node

import { spawn } from "node:child_process";
import { access, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { chromium } from "../apps/desktop/node_modules/playwright-core/index.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const desktop = path.join(root, "apps", "desktop");
const delivery = path.join(root, "docs", "phase-7-delivery");
const screenshots = path.join(delivery, "screenshots");
const port = Number(process.env.MELLOWYAK_CAPTURE_PORT ?? 1427);
const baseUrl = `http://127.0.0.1:${port}`;
const engineOrigin = "http://127.0.0.1:43127";

const browserCandidates = [
  process.env.MELLOWYAK_CHROMIUM_PATH,
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
].filter(Boolean);

async function findBrowser() {
  for (const candidate of browserCandidates) {
    try { await access(candidate); return candidate; } catch { /* try the next local browser */ }
  }
  throw new Error("No supported local Chromium browser was found. Set MELLOWYAK_CHROMIUM_PATH.");
}

const NOW = "2026-08-24T14:00:00Z";
const PROJECT_ID = "project-public-phase7";
const SNAPSHOT_CURRENT_ID = "snapshot-public-current";
const SNAPSHOT_INITIAL_ID = "snapshot-public-initial";
const BEHAVIOR_ID = "behavior-checkout-public";
const PROBE_ID = "probe-api-health-public";
const CHANGE_ID = "change-public-phase7";
const REGRESSION_ID = "regression-public-phase7";

const gitAvailable = {
  available: true,
  branch: "main",
  head_sha: "8fc79e1c8ad7446849941219bf17f01a8fa3c141",
  is_detached: false,
  is_dirty: true,
  staged: [],
  unstaged: ["src/checkout/summary.ts"],
  untracked: ["tests/checkout/summary.test.ts"],
  ignored_count: 18,
  worktree_fingerprint: "phase7-public-worktree",
  error: null,
};

const gitOptional = {
  available: false,
  branch: null,
  head_sha: null,
  is_detached: false,
  is_dirty: true,
  staged: [],
  unstaged: [],
  untracked: ["src/service.py", "tests/test_service.py"],
  ignored_count: 11,
  worktree_fingerprint: "snapshot-backed-public-worktree",
  error: "GIT_NOT_REQUIRED",
};

const scan = {
  id: "scan-public-phase7",
  status: "completed",
  scan_version: "1",
  started_at: "2026-08-24T13:59:55Z",
  completed_at: NOW,
  total_candidates: 316,
  processed_files: 316,
  included_files: 298,
  excluded_files: 18,
  binary_files: 4,
  sensitive_files: 3,
  failed_files: 0,
  unknown_items: 3,
  unsupported_files: 2,
  test_files: 48,
  relationship_count: 884,
  duration_seconds: 5,
  error_summary: null,
};

function projectFor(screen) {
  const nonGit = screen.variant === "nonGit" || screen.kind === "wizard";
  const polyglot = screen.variant === "polyglot";
  return {
    id: PROJECT_ID,
    display_name: polyglot ? "Polyglot Workshop Demo" : nonGit ? "Local Service Demo" : "PulsePlan Local Demo",
    display_path: polyglot ? "/fixture/polyglot-workshop" : nonGit ? "/fixture/local-service" : "/fixture/pulseplan-local",
    repository_path: polyglot ? "/fixture/polyglot-workshop" : nonGit ? "/fixture/local-service" : "/fixture/pulseplan-local",
    monitoring_mode: "passive",
    monitoring_status: "active",
    last_scan_status: "completed",
    last_scan_at: NOW,
    created_at: "2026-08-24T13:40:00Z",
    updated_at: NOW,
    languages: polyglot ? ["TypeScript", "Python"] : nonGit ? ["Python"] : ["TypeScript", "Python"],
    frameworks: polyglot ? ["React", "FastAPI"] : nonGit ? ["FastAPI"] : ["React", "FastAPI"],
    tests: polyglot ? ["Vitest", "Pytest"] : nonGit ? ["Pytest"] : ["Vitest", "Pytest"],
    runtime_hints: polyglot ? ["Node.js", "Python"] : nonGit ? ["Python"] : ["Node.js", "Python"],
    git: nonGit ? gitOptional : gitAvailable,
    scan,
    source_remains_local: true,
    disconnected: false,
    source_available: true,
    notifications_muted: false,
    project_type: polyglot ? "MIXED_POLYGLOT" : nonGit ? "API_SERVICE" : "WEB_APP",
    runtime_setup_status: screen.variant === "limits" ? "INCOMPLETE" : "READY_WITH_LIMITS",
    observation_level: "LIGHT",
    snapshot_retention_days: 30,
    snapshot_soft_cap_bytes: 5 * 1024 ** 3,
  };
}

const detection = {
  selected_path: "/fixture/local-service",
  repository_path: "/fixture/local-service",
  suggested_name: "Local Service Demo",
  git: gitOptional,
  languages: ["TypeScript", "Python", "Rust"],
  language_counts: { TypeScript: 142, Python: 91, Rust: 18 },
  frameworks: ["React", "FastAPI", "Tauri"],
  tests: ["Vitest", "Pytest"],
  runtime_hints: ["Node.js", "Python", "Tauri"],
  candidate_files: 316,
  ignored_paths: 18,
  relationship_coverage: "bounded deterministic adapters",
  unsupported_coverage: "reported explicitly",
  source_remains_local: true,
};

const runtimeCandidates = [
  { runtime_type: "NODE", display_name: "Node.js / TypeScript", runtime_version: "22.18.0", executable_reference: "node", relative_working_directory: ".", dependency_manifests: ["package.json", "package-lock.json"], test_definitions: [{ framework: "Vitest" }], limitations: [], detected: true },
  { runtime_type: "PYTHON", display_name: "Python", runtime_version: "3.11.9", executable_reference: ".venv/bin/python", relative_working_directory: ".", dependency_manifests: ["pyproject.toml", "uv.lock"], test_definitions: [{ framework: "Pytest" }], limitations: [], detected: true },
];

function runtimeProfile({ id, name, type, primary, executable, argv, port, health, tests, status = "READY", limitations = [] }) {
  const version = {
    id: `${id}-version-1`,
    version_number: 1,
    runtime_type: type,
    adapter_version: "1",
    execution_mode: "MANAGED",
    executable_reference: executable,
    argv,
    relative_working_directory: ".",
    runtime_version: type === "NODE" ? "22.18.0" : "3.11.9",
    dependency_fingerprint: `${type.toLowerCase()}-public-lock-digest`,
    health_definition: health ? { url: health } : {},
    expected_ports: port ? [port] : [],
    test_definitions: tests.map((framework) => ({ framework, approved: true })),
    environment_schema: ["PATH", "LANG"],
    network_policy: "LOOPBACK_ONLY",
    limitations,
    approved_at: NOW,
    detected_at: NOW,
    created_at: NOW,
  };
  return { id, project_id: PROJECT_ID, display_name: name, current_version_id: version.id, primary, status, current_version: version, versions: [version], created_at: NOW, updated_at: NOW };
}

const nodeProfile = runtimeProfile({ id: "runtime-node-public", name: "Desktop UI", type: "NODE", primary: true, executable: "node", argv: ["node_modules/vite/bin/vite.js", "--host", "127.0.0.1"], port: 4310, health: "http://127.0.0.1:4310/health", tests: ["Vitest"] });
const pythonProfile = runtimeProfile({ id: "runtime-python-public", name: "Local API", type: "PYTHON", primary: false, executable: ".venv/bin/python", argv: ["-m", "uvicorn", "fixture.main:app"], port: 4311, health: "http://127.0.0.1:4311/health", tests: ["Pytest"] });

function runtimeProfiles(screen) {
  if (screen.variant === "nonGit") return [{ ...pythonProfile, primary: true }];
  return [nodeProfile, pythonProfile];
}

function runtimeInstances(screen) {
  if (screen.variant !== "running") return [];
  return [{ id: "instance-node-public", project_id: PROJECT_ID, profile_id: nodeProfile.id, profile_version_id: nodeProfile.current_version_id, correlation_id: "correlation-public-runtime", status: "RUNNING", process_id: 4127, started_at: "2026-08-24T13:58:00Z", stopped_at: null, exit_code: null, observation: { health: "passing", port: 4310, uptime_seconds: 120 } }];
}

const initialSnapshot = {
  id: SNAPSHOT_INITIAL_ID,
  project_id: PROJECT_ID,
  parent_snapshot_id: null,
  episode_id: null,
  manifest_digest: "101c672e62a038aa4c97d58c3c8d72a1940f886bb2624e214ab978d4ba03f04f",
  creation_reason: "INITIAL_SAVE_POINT",
  source_identity: { kind: "snapshot", snapshot_id: SNAPSHOT_INITIAL_ID, manifest_hash: "101c672e62a038aa" },
  git_anchor: {},
  included_count: 298,
  excluded_count: 18,
  sensitive_count: 3,
  unsupported_count: 2,
  logical_bytes: 812_400,
  physical_bytes_added: 812_400,
  reused_bytes: 0,
  pinned: true,
  integrity_status: "VERIFIED",
  created_at: "2026-08-24T13:45:00Z",
  runtime_profile_fingerprints: ["node-public-lock-digest", "python-public-lock-digest"],
};

const currentSnapshot = {
  ...initialSnapshot,
  id: SNAPSHOT_CURRENT_ID,
  parent_snapshot_id: SNAPSHOT_INITIAL_ID,
  episode_id: "episode-public-2",
  manifest_digest: "a75e94ad695241662365c016c50558e88412104c99cfe94571b3c5301873b2f9",
  creation_reason: "EPISODE_STABILIZED",
  source_identity: { kind: "snapshot", parent_snapshot_id: SNAPSHOT_INITIAL_ID, snapshot_id: SNAPSHOT_CURRENT_ID, manifest_hash: "a75e94ad69524166", episode_id: "episode-public-2" },
  included_count: 301,
  logical_bytes: 824_900,
  physical_bytes_added: 12_500,
  reused_bytes: 812_400,
  pinned: false,
  created_at: NOW,
  entries: [
    { relative_path: "src/checkout/summary.ts", blob_digest: "2f854882", byte_size: 5100, classification: "SOURCE" },
    { relative_path: "src/api/checkout.py", blob_digest: "4bd399b1", byte_size: 4200, classification: "SOURCE" },
    { relative_path: "tests/checkout/summary.test.ts", blob_digest: "926af6d0", byte_size: 3200, classification: "TEST" },
  ],
};

const episodes = [
  { id: "episode-public-2", project_id: PROJECT_ID, started_at: "2026-08-24T13:59:52Z", ended_at: NOW, event_count: 12, added_paths: ["tests/checkout/summary.test.ts"], modified_paths: ["src/checkout/summary.ts", "src/api/checkout.py"], deleted_paths: [], renamed_paths: [], dependency_changes: [], runtime_events: [{ type: "runtime_restart" }], base_snapshot_id: SNAPSHOT_INITIAL_ID, resulting_snapshot_id: SNAPSHOT_CURRENT_ID, git_anchor: {}, status: "STABILIZED", error_code: null },
  { id: "episode-public-1", project_id: PROJECT_ID, started_at: "2026-08-24T13:44:54Z", ended_at: "2026-08-24T13:45:00Z", event_count: 7, added_paths: ["src/api/checkout.py"], modified_paths: ["package.json"], deleted_paths: [], renamed_paths: [], dependency_changes: ["package.json"], runtime_events: [], base_snapshot_id: null, resulting_snapshot_id: SNAPSHOT_INITIAL_ID, git_anchor: {}, status: "STABILIZED", error_code: null },
];

const milestone = { id: "milestone-public-1", project_id: PROJECT_ID, snapshot_id: SNAPSHOT_INITIAL_ID, display_name: "Checkout happy path works", behavior_id: BEHAVIOR_ID, behavior_version_id: "behavior-version-public-1", probe_version_id: "probe-version-public-1", runtime_profile_versions: [nodeProfile.current_version_id, pythonProfile.current_version_id], environment_summary: { network: "loopback_only", locale: "en-US" }, limitations: [], status: "ACCEPTED", human_attested: false, pinned: true, created_at: "2026-08-24T13:46:00Z" };

function probeRun(state) {
  const confirmed = state === "CONFIRMED";
  return {
    id: confirmed ? "probe-run-confirmed-public" : "probe-run-watch-public",
    project_id: PROJECT_ID,
    probe_id: PROBE_ID,
    probe_version_id: "probe-version-public-1",
    snapshot_id: SNAPSHOT_CURRENT_ID,
    episode_id: "episode-public-2",
    runtime_profile_version_id: nodeProfile.current_version_id,
    source_identity: currentSnapshot.source_identity,
    status: "COMPLETED",
    result: confirmed ? "FAILED" : "INCONCLUSIVE",
    attempt_count: confirmed ? 2 : 1,
    expected: { status: 200, json: { ready: true } },
    observed: confirmed ? { status: 503, error: "SERVICE_UNAVAILABLE" } : { changed_paths: 3, behavior_failure: false },
    evidence: confirmed ? { prior_passing_run_id: "probe-run-known-good-public", retry_run_ids: ["probe-run-current-1", "probe-run-current-2"] } : { source_change_only: true },
    limitations: confirmed ? [] : ["NO_BEHAVIOR_FAILURE_OBSERVED"],
    reproducible: confirmed,
    signal: { state, reason_codes: confirmed ? ["PRIOR_ACCEPTED_PASS", "CURRENT_COMPARABLE_FAIL", "RETRY_REPRODUCED"] : ["FILE_CHANGE_ONLY"], prior_milestone_id: milestone.id, source_identity: currentSnapshot.source_identity },
    started_at: "2026-08-24T14:00:01Z",
    completed_at: "2026-08-24T14:00:02Z",
    cancelled_at: null,
  };
}

function apiProbe(screen) {
  const state = screen.variant === "confirmed" ? "CONFIRMED" : screen.variant === "watch" ? "WATCH" : null;
  const version = { id: "probe-version-public-1", version_number: 1, runtime_profile_version_id: nodeProfile.current_version_id, definition: { url: "http://127.0.0.1:4310/health", method: "GET" }, timeout_seconds: 12, retry_policy: { max_attempts: 2 }, expected_result: { status: 200, json: { ready: true } }, evidence_policy: { persist_response_body: false }, source_links: [{ path: "src/api/health.ts", provenance: "HUMAN_CONFIRMED" }], runtime_links: [{ profile_version_id: nodeProfile.current_version_id }], approved_at: NOW, created_at: NOW };
  return { id: PROBE_ID, project_id: PROJECT_ID, behavior_id: BEHAVIOR_ID, display_name: "Checkout API remains healthy", probe_type: "HTTP", current_version_id: version.id, status: "ACTIVE", current_version: version, versions: [version], last_run: state ? probeRun(state) : null, created_at: NOW, updated_at: NOW };
}

const behaviorVersion = { id: "behavior-version-public-1", version_number: 1, title: "Checkout completes successfully", description: "A customer can review and submit a valid order.", expected_outcome: "The order is accepted and a confirmation is shown.", criticality: "CRITICAL", persona: "Returning customer", preconditions: "A valid cart exists", starting_state: "Checkout summary", expected_assertions: [{ type: "HTTP_STATUS", value: 200 }], limitations: [], verification_not_configured: true, created_by_type: "USER", source_candidate_id: null, content_digest: "behavior-public-digest", supersedes_version_id: null, source_revision: initialSnapshot.source_identity, created_at: NOW };
const behavior = { id: BEHAVIOR_ID, project_id: PROJECT_ID, stable_key: "checkout-completes", display_name: behaviorVersion.title, lifecycle_state: "PROTECTED", current_version_id: behaviorVersion.id, last_accepted_baseline_id: "baseline-public-1", always_recheck: true, current_version: behaviorVersion, versions: [behaviorVersion], links: [{ id: "link-public-1", link_type: "FILE", link_key: "src/checkout/summary.ts", provenance: "HUMAN_CONFIRMED" }], baselines: [{ id: "baseline-public-1", status: "ACCEPTED", behavior_version_id: behaviorVersion.id, evidence_bundle_id: "evidence-public-1", created_at: NOW }], created_at: NOW, updated_at: NOW, archived_at: null };

const browserRuntime = { id: "browser-runtime-public", project_id: PROJECT_ID, display_name: "Local web preview", base_url: "http://127.0.0.1:4310", allowed_origin: "http://127.0.0.1:4310", starting_path: "/checkout", viewport_width: 1280, viewport_height: 800, locale: "en-US", timezone: "UTC", browser_type: "chromium", capture_screenshots: true, capture_trace: true, capture_video: false, capture_network: false, created_at: NOW, updated_at: NOW };

const change = { id: CHANGE_ID, project_id: PROJECT_ID, change_kind: "uncommitted_worktree", revision: 2, base_head_sha: gitAvailable.head_sha, head_sha: gitAvailable.head_sha, worktree_fingerprint: gitAvailable.worktree_fingerprint, changed_paths: ["src/checkout/summary.ts", "src/api/checkout.py", "tests/checkout/summary.test.ts"], task_intent: "Keep checkout healthy after the summary update", status: "change_detected", created_at: NOW, updated_at: NOW };
const changeImpact = { analysis: { id: "analysis-public", project_id: PROJECT_ID, change_id: CHANGE_ID, analysis_revision: 1, base_head_sha: gitAvailable.head_sha, head_sha: gitAvailable.head_sha, worktree_fingerprint: gitAvailable.worktree_fingerprint, scan_revision: scan.id, algorithm_version: "reverse-impact-v1", status: "completed", changed_file_count: 3, impacted_node_count: 4, unknown_count: 1, stale_count: 0, heuristic_count: 0, truncated: false, truncation_reasons: [], duration_ms: 22, stale: false, stale_reasons: [], created_at: NOW }, results: [{ id: "impact-public-1", node_id: "node-public-1", node_type: "BEHAVIOR", display_name: behaviorVersion.title, relative_path: null, impact_class: "direct_human_confirmed", minimum_depth: 1, strongest_provenance: "HUMAN_CONFIRMED", stale: false, unknown: false, explanation: "A confirmed behavior link touches the changed checkout summary.", path_count: 1, ranking_score: 100, ranking_reasons: ["human_confirmed"], unknown_reason: null }] };
const protectionPlan = { id: "plan-public-1", project_id: PROJECT_ID, change_id: CHANGE_ID, source_identity: currentSnapshot.source_identity, status: "ACTIVE", counts: { required: 1, suggested: 0, skipped: 0, needs_review: 0, unknown: 1 }, items: [{ id: "plan-item-public-1", behavior_id: BEHAVIOR_ID, behavior_name: behaviorVersion.title, behavior_version_id: behaviorVersion.id, baseline_id: "baseline-public-1", selection_class: "REQUIRED", selection_reason: "direct_human_confirmed", impact_path: [{ from: "src/checkout/summary.ts", to: BEHAVIOR_ID }], criticality: "CRITICAL", verification_method: "BROWSER_REPLAY", current_result_id: "probe-run-confirmed-public" }] };
const regression = { id: REGRESSION_ID, change_id: CHANGE_ID, behavior_id: BEHAVIOR_ID, baseline_id: "baseline-public-1", verification_run_item_id: "verification-item-public-1", probe_run_id: "probe-run-confirmed-public", signal_classification_id: "signal-public-confirmed", status: "CONFIRMED", decision_reason: "PRIOR_PASS_CURRENT_REPRODUCIBLE_FAIL", source_identity: currentSnapshot.source_identity };
const gate = { id: "gate-public-1", state: "BLOCKED", reason: "CONFIRMED_REGRESSION", source_identity: currentSnapshot.source_identity, limitations: ["ONE_UNKNOWN_BOUNDARY"], decision_digest: "gate-public-digest" };
const repairWorkspace = { id: "repair-workspace-public-1", project_id: PROJECT_ID, regression_id: REGRESSION_ID, signal_id: "signal-public-confirmed", snapshot_id: SNAPSHOT_CURRENT_ID, relative_path: "repair-workspaces/repair-workspace-public-1", manifest_digest: currentSnapshot.manifest_digest, status: "READY", instructions: null, items: [{ kind: "current", relative_path: "current" }, { kind: "evidence", relative_path: "evidence/probe-run-confirmed.json" }, { kind: "validation", relative_path: "validation-plan.json" }], created_at: NOW, deleted_at: null };

const setup = {
  "/health": { status: "ready", mode: "local", engine_version: "0.1.0", app_version: "0.1.0", database_status: "ready", database_schema_version: "0007_runtime_snapshot_probe_foundation", data_root: "/fixture/mellowyak-data", cloud_connected: false, outbound_network_enabled: false, uptime_seconds: 84 },
  "/readiness": { ready: true, checks: { local_only: true, database_ready: true, snapshot_store_ready: true } },
  "/installation": { installation_id: "phase7-public-fixture", created_at: NOW, last_started_at: NOW, app_version: "0.1.0", engine_version: "0.1.0", database_schema_version: "0007_runtime_snapshot_probe_foundation" },
  "/settings/privacy": { mode: "local", cloud_connected: false, outbound_network_enabled: false, source_upload_enabled: false, telemetry_upload_enabled: false, account_required: false },
  "/storage/paths": { data_root: "/fixture/mellowyak-data", database: "/fixture/mellowyak-data/database", evidence: "/fixture/mellowyak-data/evidence", projects: "/fixture/mellowyak-data/projects", cache: "/fixture/mellowyak-data/cache", logs: "/fixture/mellowyak-data/logs", runtime: "/fixture/mellowyak-data/runtime", backups: "/fixture/mellowyak-data/backups" },
};

const screens = [
  { file: "00-runtime-wizard-project-type.png", locale: "en-US", kind: "wizard", step: 2, title: "Runtime Wizard — project type", purpose: "Review the confirmed project-type choice before runtime setup.", state: "A local non-Git source folder was detected and Web App is suggested.", actions: "Choose any project type, continue, go back, or cancel.", known: "Canonical local folder metadata, detected languages, frameworks, and source-local policy.", unknown: "The primary runtime and executable are not selected yet.", next: "Confirm the project type and continue to runtime detection." },
  { file: "01-runtime-wizard-detected-runtimes.png", locale: "en-US", kind: "wizard", step: 3, title: "Runtime Wizard — detected runtimes", purpose: "Review every detected runtime independently and choose primary/secondary roles.", state: "Node.js, Python, and Tauri/Rust are suggested from public fixture metadata.", actions: "Select runtimes, choose exactly one primary runtime, re-run detection, continue, or go back.", known: "Runtime candidates and available version hints.", unknown: "No start command has been approved yet.", next: "Confirm the selected runtimes and describe how each one runs." },
  { file: "02-runtime-wizard-profile-config.png", locale: "en-US", kind: "wizard", step: 4, title: "Runtime Wizard — profile configuration", purpose: "Configure one approved runtime profile without a shell command string.", state: "The primary profile is expanded; secondary profiles remain available but collapsed for legibility.", actions: "Set mode, executable, argv, working folder, ports, health URL, tests, and safe environment names.", known: "Executable and argv are persisted separately with loopback-only policy.", unknown: "Availability is not claimed until profile validation succeeds.", next: "Review test suggestions and monitoring/privacy settings." },
  { file: "03-runtime-wizard-initial-save-point.png", locale: "en-US", kind: "wizard", step: 7, title: "Runtime Wizard — initial Save Point", purpose: "Confirm the first content-addressed local source snapshot.", state: "The initial snapshot reports included, excluded, sensitive, unsupported, physical, and reused bytes.", actions: "Continue to the readiness summary or go back.", known: "Exact snapshot identity and bounded capture counts.", unknown: "Unsupported files remain outside verified coverage.", next: "Review readiness and every remaining limitation." },
  { file: "04-ready-with-limits-details.png", locale: "en-US", kind: "overview", variant: "limits", openLimits: true, title: "Ready with limits — actionable details", purpose: "Replace a vague readiness badge with an actionable explanation.", state: "Runtime setup, unsupported files, and unknown relationships are explained.", actions: "Close the explanation or follow the recommended setup actions.", known: "Source scanning and local monitoring remain operational.", unknown: "Automatic runtime checks and unsupported relationships are not fully covered.", next: "Complete runtime setup and review unsupported or unknown boundaries." },
  { file: "05-runtime-profiles.png", locale: "en-US", kind: "runtime", title: "Runtime Profiles", purpose: "Inspect primary and secondary local runtime profiles.", state: "Node.js and Python profiles are configured but no managed process is currently running.", actions: "Detect, validate, start, stop, inspect evidence, add a profile, or add a probe.", known: "Approved executable/argv, ports, tests, health policy, and profile versions.", unknown: "Current process health is unknown until a runtime starts.", next: "Validate and start the intended primary runtime." },
  { file: "06-runtime-running.png", locale: "en-US", kind: "runtime", variant: "running", title: "Runtime Profile — running", purpose: "Show bounded runtime process and health observation.", state: "The primary Node.js profile is running on its expected loopback port.", actions: "Stop, validate, inspect technical details, or run an approved probe.", known: "Process ID, local port, health state, uptime, and profile version.", unknown: "MellowYak does not inspect unrelated process memory or environment values.", next: "Run the relevant approved probe or continue passive monitoring." },
  { file: "07-memory-save-points.png", locale: "en-US", kind: "memory", title: "Memory — Episodes and Save Points", purpose: "Review grouped change Episodes and deduplicated local Save Point history.", state: "Two stabilized Episodes produced two Save Points with reused-byte evidence.", actions: "Create a Save Point, select history, inspect retention, or open snapshot details.", known: "Episode counts, changed-path summaries, physical bytes, reused bytes, and pinned milestones.", unknown: "A Save Point alone does not prove a behavior still works.", next: "Select a Save Point to inspect or bind it to a passing probe as known good." },
  { file: "08-snapshot-detail.png", locale: "en-US", kind: "snapshotDetail", title: "Snapshot detail", purpose: "Inspect exact snapshot identity, integrity, exclusions, and materialization safety.", state: "The current incremental snapshot is verified and its bounded manifest entries are visible.", actions: "Load manifest, pin, materialize, or begin a known-good milestone.", known: "Manifest digest, source identity, included entries, sizes, and Git-optional anchor.", unknown: "Behavioral correctness is not inferred from files alone.", next: "Materialize for inspection or validate a behavior before marking known good." },
  { file: "09-this-works-save-it.png", locale: "en-US", kind: "behavior", title: "This works — save it", purpose: "Start the friendly known-good workflow from a protected behavior.", state: "Checkout has an explicit expected outcome but no Phase 7 probe has been configured.", actions: "Add a Browser, API, CLI, Process, Test, or Manual probe.", known: "Behavior version, expected outcome, criticality, and prior accepted baseline.", unknown: "No comparable current automated result exists yet.", next: "Choose a probe type and record its exact expected result." },
  { file: "10-probe-type-selection.png", locale: "en-US", kind: "probeBuilder", title: "Probe type selection", purpose: "Choose one universal Probe contract for the behavior.", state: "The probe builder exposes the approved type selector and bounded execution policy.", actions: "Choose Browser, API, CLI, Process, Test, or Manual; cancel or save after required fields are complete.", known: "All probe types bind to source identity and use bounded local evidence.", unknown: "No type or expected result is accepted until the user saves it.", next: "Select the probe matching the behavior and fill its expected result." },
  { file: "11-api-probe.png", locale: "en-US", kind: "probeBuilder", fillProbe: "api", title: "HTTP/API Probe", purpose: "Configure a loopback-only API health assertion.", state: "A GET request targets a synthetic loopback health endpoint and expects status 200.", actions: "Edit target, expected status, timeout, runtime binding, save, or cancel.", known: "External egress is disabled and bodies are not retained by default.", unknown: "The endpoint has not run in this configuration yet.", next: "Save the approved probe and execute it against the exact Save Point." },
  { file: "12-cli-probe.png", locale: "en-US", kind: "probeBuilder", fillProbe: "cli", title: "CLI Probe", purpose: "Configure a bounded local CLI check without invoking a shell.", state: "Executable and argv are separate and the expected exit code is zero.", actions: "Edit executable, one argument per line, timeout, expected exit code, save, or cancel.", known: "No shell syntax is evaluated and the working scope is local.", unknown: "The executable has not been validated on this fixture screen.", next: "Save, validate availability, then run the probe." },
  { file: "13-known-good-milestone.png", locale: "en-US", kind: "knownGood", title: "Known-Good Milestone", purpose: "Bind a friendly milestone name to an exact Save Point and explicit attestation.", state: "A current snapshot is selected and the known-good milestone form is open.", actions: "Name and save the milestone, or keep inspecting snapshot evidence.", known: "Exact snapshot, pinned prior milestone count, runtime fingerprints, and attestation mode.", unknown: "Human attestation does not become automated probe evidence.", next: "Save only after the behavior is observed working or its approved probe passes." },
  { file: "14-watch-file-change-only.png", locale: "en-US", kind: "signal", variant: "watch", title: "WATCH — file change only", purpose: "Show that a source change alone is not called a regression.", state: "The local API probe has no observed behavior failure; the deterministic signal remains WATCH.", actions: "Run the probe, inspect technical details, or continue monitoring.", known: "Three files changed in one Episode and no comparable failure was observed.", unknown: "Whether the affected behavior still works has not been proven.", next: "Run the relevant comparable probe before making a regression claim." },
  { file: "15-confirmed-regression-friendly.png", locale: "en-US", kind: "signal", variant: "confirmed", title: "Confirmed regression — friendly view", purpose: "Explain a reproducible prior-pass to current-fail transition in novice language.", state: "A probe that passed at an accepted milestone failed twice at the current comparable source identity.", actions: "Inspect technical details, rerun the probe, or open change context.", known: "Prior accepted pass, current comparable fail, and retry reproduction.", unknown: "Root cause is not claimed.", next: "Inspect technical evidence and create an isolated Repair Workspace if needed." },
  { file: "16-confirmed-regression-technical.png", locale: "en-US", kind: "signal", variant: "confirmed", technical: true, title: "Confirmed regression — technical evidence", purpose: "Expose deterministic reason codes and exact source identity.", state: "The technical disclosure shows prior milestone, current snapshot identity, and reproducibility reasons.", actions: "Review structured evidence or collapse the technical disclosure.", known: "Exact reason codes, prior accepted baseline, attempts, expected result, and observed result.", unknown: "No automatic root-cause or repair claim is made.", next: "Use the evidence to scope a local isolated Repair Workspace." },
  { file: "17-repair-workspace.png", locale: "en-US", kind: "repair", variant: "confirmed", title: "Repair Workspace", purpose: "Create an isolated local materialization for manual repair work.", state: "The workspace is ready outside the live project with current source, evidence, and validation plan references.", actions: "Open or delete the Repair Workspace and inspect its technical manifest.", known: "Snapshot digest, bounded workspace location, included item classes, and live-project safety.", unknown: "MellowYak has not generated or applied a patch.", next: "Open the isolated workspace manually and follow the required rechecks." },
  { file: "18-non-git-project.png", locale: "en-US", kind: "overview", variant: "nonGit", title: "Non-Git project", purpose: "Show full local operation without requiring a Git repository.", state: "Source scan and monitoring are ready with snapshot-backed identity.", actions: "Open Runtime, Memory, Changes, Impact, Behaviors, scan, or source folder.", known: "Local source metadata, snapshot identity support, scan coverage, and monitoring status.", unknown: "Git branch and commit anchors do not exist for this project.", next: "Use Save Points and Episodes as the source-history vocabulary." },
  { file: "19-polyglot-project.png", locale: "en-US", kind: "runtime", variant: "polyglot", title: "Polyglot project", purpose: "Show multiple runtime profiles with an explicit primary and secondary selection.", state: "Node.js is primary and Python is secondary; both retain independent versions and tests.", actions: "Detect, validate, start either approved profile, inspect limitations, or configure probes.", known: "Per-runtime executable, health, tests, ports, and primary role.", unknown: "Neither runtime process is currently running.", next: "Start only the profile needed for the next relevant probe." },
  { file: "20-hebrew-runtime-wizard.png", locale: "he-IL", kind: "wizard", step: 3, title: "Runtime Wizard — Hebrew RTL", purpose: "Verify the runtime-selection step in complete Hebrew RTL layout.", state: "Detected runtimes, checkboxes, version hints, and primary selection are mirrored correctly.", actions: "Select runtimes, choose the primary profile, detect again, continue, or go back.", known: "The same synthetic runtime metadata used by the English screen.", unknown: "Execution remains unapproved until the later configuration step.", next: "Continue in Hebrew to configure executable and argv separately." },
  { file: "21-hebrew-known-good.png", locale: "he-IL", kind: "knownGood", title: "Known-Good Milestone — Hebrew RTL", purpose: "Verify the known-good workflow, data direction, and controls in Hebrew.", state: "The selected Save Point and milestone form are fully translated and right-to-left.", actions: "Name and save an attested milestone or inspect snapshot evidence.", known: "Exact local snapshot and existing pinned milestone count.", unknown: "Attestation remains manual until a supported probe passes.", next: "Save the milestone only after explicit verification." },
  { file: "22-hebrew-confirmed-regression.png", locale: "he-IL", kind: "signal", variant: "confirmed", title: "Confirmed regression — Hebrew RTL", purpose: "Verify friendly confirmed-regression copy in Hebrew while technical identifiers remain LTR.", state: "The reproducible prior-pass to current-fail transition is translated and mirrored.", actions: "Run again or expand technical details.", known: "Accepted prior pass, comparable current failures, and retry evidence.", unknown: "Root cause and automatic repair remain out of scope.", next: "Review evidence and create a separate Repair Workspace when needed." },
];

const requestedFiles = new Set((process.env.MELLOWYAK_CAPTURE_ONLY ?? "").split(",").map((value) => value.trim()).filter(Boolean));
const captureScreens = requestedFiles.size ? screens.filter((screen) => requestedFiles.has(screen.file) || requestedFiles.has(screen.file.replace(/\.png$/, ""))) : screens;
if (!captureScreens.length) throw new Error("MELLOWYAK_CAPTURE_ONLY did not match a Phase 7 screenshot filename.");

function isWizard(screen) { return screen.kind === "wizard"; }

function projectDetectionResponse(screen) {
  const project = projectFor(screen);
  return { ...detection, selected_path: project.repository_path, repository_path: project.repository_path, suggested_name: project.display_name };
}

function responseFor(screen, url, method, body = {}) {
  const parsed = new URL(url);
  const pathname = parsed.pathname;
  const project = projectFor(screen);
  if (pathname in setup) return setup[pathname];
  if (pathname === "/projects" && method === "GET") return { projects: isWizard(screen) ? [] : [project] };
  if (pathname === "/projects" && method === "POST") return project;
  if (pathname === "/projects/detect") return projectDetectionResponse(screen);
  if (pathname === "/alerts") return { alerts: [] };
  if (pathname === "/alerts/unread-count") return { count: 0 };
  if (pathname === `/projects/${PROJECT_ID}`) return project;
  if (pathname === `/projects/${PROJECT_ID}/impact/summary`) return { files_indexed: 298, languages: project.languages.length, language_counts: project.languages.reduce((result, value, index) => ({ ...result, [value]: 180 - index * 55 }), {}), direct_relationships: 884, tests_found: 48, sensitive_files: 3, unknown_references: 3, unsupported_files: 2, stale_relationships: 0 };
  if (pathname === `/projects/${PROJECT_ID}/capabilities`) return { mode: project.git.available ? "local_source_with_runtime" : "snapshot_backed_local_source", source_available: true, runtime_available: true, available: ["source_scan", "episodes", "snapshots", "runtime_profiles", "universal_probes"], unavailable: ["automatic_repair"], future_only: ["validated_apply"], source_remains_local: true };
  if (pathname === `/projects/${PROJECT_ID}/runtime/detect`) return { id: "runtime-detection-public", project_id: PROJECT_ID, status: "COMPLETED", candidates: runtimeCandidates, started_at: NOW, completed_at: NOW, error_code: null };
  if (pathname === `/projects/${PROJECT_ID}/runtime-profiles` && method === "GET") return { profiles: runtimeProfiles(screen) };
  if (pathname === `/projects/${PROJECT_ID}/runtime-profiles` && method === "POST") {
    const primary = Boolean(body.primary);
    return runtimeProfile({ id: `runtime-created-${String(body.runtime_type ?? "generic").toLowerCase()}`, name: String(body.display_name ?? "Approved runtime"), type: String(body.runtime_type ?? "GENERIC"), primary, executable: String(body.executable_reference ?? "approved-runtime"), argv: Array.isArray(body.argv) ? body.argv : [], port: Array.isArray(body.expected_ports) ? body.expected_ports[0] : null, health: body.health_definition?.url, tests: [], limitations: [] });
  }
  if (pathname === `/projects/${PROJECT_ID}/runtime-instances`) return { instances: runtimeInstances(screen) };
  if (pathname === `/projects/${PROJECT_ID}/snapshots` && method === "GET") {
    const initialForScreen = screen.kind === "memory" ? { ...initialSnapshot, pinned: false } : initialSnapshot;
    return { snapshots: [currentSnapshot, initialForScreen] };
  }
  if (pathname === `/projects/${PROJECT_ID}/snapshots` && method === "POST") return initialSnapshot;
  if (pathname === `/projects/${PROJECT_ID}/snapshots/${SNAPSHOT_CURRENT_ID}`) return currentSnapshot;
  if (pathname === `/projects/${PROJECT_ID}/snapshots/${SNAPSHOT_INITIAL_ID}`) return initialSnapshot;
  if (pathname.endsWith("/materialize")) return { snapshot_id: SNAPSHOT_CURRENT_ID, relative_path: "materialized/snapshot-public-current", file_count: currentSnapshot.included_count, logical_bytes: currentSnapshot.logical_bytes, verified: true, live_project_modified: false };
  if (pathname.endsWith("/pin") || pathname.endsWith("/unpin")) return { ...currentSnapshot, pinned: pathname.endsWith("/pin") };
  if (pathname === `/projects/${PROJECT_ID}/episodes`) return { episodes };
  if (pathname === `/projects/${PROJECT_ID}/milestones` && method === "GET") return { milestones: [milestone] };
  if (pathname === `/projects/${PROJECT_ID}/milestones/known-good`) return { ...milestone, display_name: String(body.display_name ?? milestone.display_name), snapshot_id: String(body.snapshot_id ?? milestone.snapshot_id), human_attested: Boolean(body.human_attested) };
  if (pathname === `/projects/${PROJECT_ID}/probes` && method === "GET") {
    if (["behavior", "probeBuilder"].includes(screen.kind)) return { probes: [] };
    return { probes: [apiProbe(screen)] };
  }
  if (pathname === `/projects/${PROJECT_ID}/probes` && method === "POST") return apiProbe(screen);
  if (pathname === `/projects/${PROJECT_ID}/runtimes`) return { runtimes: [browserRuntime] };
  if (pathname === `/projects/${PROJECT_ID}/captures`) return { captures: [] };
  if (pathname === `/projects/${PROJECT_ID}/behaviors`) return { behaviors: [behavior] };
  if (pathname === `/projects/${PROJECT_ID}/behavior-candidates`) return { candidates: [] };
  if (pathname === `/projects/${PROJECT_ID}/changes/current`) return change;
  if (pathname === `/projects/${PROJECT_ID}/changes/${CHANGE_ID}/impact`) return changeImpact;
  if (pathname === `/projects/${PROJECT_ID}/changes/${CHANGE_ID}/impact/paths`) return { paths: [{ id: "path-public-1", result: behaviorVersion.title, impact_class: "direct_human_confirmed", depth: 1, steps: [{ from: "src/checkout/summary.ts", edge: "PROTECTS", to: BEHAVIOR_ID }] }] };
  if (pathname === `/projects/${PROJECT_ID}/changes/${CHANGE_ID}/protection-plan`) return protectionPlan;
  if (pathname === `/projects/${PROJECT_ID}/changes/${CHANGE_ID}/gate`) return gate;
  if (pathname === `/projects/${PROJECT_ID}/regressions`) return { regressions: [regression] };
  if (pathname === `/projects/${PROJECT_ID}/regressions/${REGRESSION_ID}/repair-workspace`) return repairWorkspace;
  if (pathname === `/projects/${PROJECT_ID}/repair-workspaces/${repairWorkspace.id}`) return repairWorkspace;
  if (pathname === "/settings/notifications") return { native_enabled: true, regression_enabled: true, blocked_gate_enabled: true, needs_review_enabled: true, project_errors_enabled: true, verified_complete_enabled: false, regression_resolved_enabled: false, show_behavior_name: true, show_project_name: true, hide_details: false, critical_override: true };
  if (pathname === "/settings/quiet-mode") return { active: false, started_at: null, ends_at: null, until_turned_off: false, allow_critical: false, remaining_seconds: null };
  if (pathname === "/app/background-status") return { keep_running_on_close: true, start_at_login: false, start_at_login_supported: true, background_supported: true };
  return {};
}

async function waitForServer() {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    try { if ((await fetch(baseUrl)).ok) return; } catch { /* Vite is still starting */ }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Vite capture server did not start at ${baseUrl}`);
}

async function waitForApp(page) {
  await page.locator(".global-nav").waitFor();
  await page.locator(".startup-shell").waitFor({ state: "detached", timeout: 10_000 }).catch(() => undefined);
}

async function enterWizard(page, targetStep) {
  await page.locator(".actions button.primary").click();
  await page.locator(".runtime-wizard").waitFor();
  await page.locator(".wizard-step button.primary").click();
  await page.locator(".wizard-card .status-row").first().waitFor();
  await page.locator(".wizard-actions button.primary").click();
  await page.locator('.wizard-progress[aria-valuenow="2"]').waitFor();
  while (Number(await page.locator(".wizard-progress").getAttribute("aria-valuenow")) < targetStep) {
    await page.locator(".wizard-actions button.primary").click();
    await page.waitForTimeout(80);
  }
  await page.locator(`.wizard-progress[aria-valuenow="${targetStep}"]`).waitFor();
  if (targetStep === 4) {
    const profiles = page.locator(".wizard-profile-stack details");
    for (let index = 1; index < await profiles.count(); index += 1) {
      if (await profiles.nth(index).getAttribute("open") !== null) await profiles.nth(index).locator("summary").click();
    }
  }
}

async function openProject(page) {
  await page.locator(".health-row").first().click();
  await page.locator(".project-nav").waitFor();
}

async function openTab(page, position) {
  await openProject(page);
  await page.locator(`.project-nav button:nth-child(${position})`).click();
  await page.waitForTimeout(120);
}

async function prepareScreen(page, screen) {
  await waitForApp(page);
  if (screen.kind === "wizard") {
    await enterWizard(page, screen.step);
    return;
  }
  if (screen.kind === "overview") {
    await openProject(page);
    if (screen.openLimits) {
      await page.locator(".limits-control button").click();
      await page.locator(".limits-popover").waitFor();
    }
    return;
  }
  if (screen.kind === "runtime") {
    await openTab(page, 5);
    await page.locator(".runtime-profile-card").first().waitFor();
    return;
  }
  if (["memory", "snapshotDetail", "knownGood"].includes(screen.kind)) {
    await openTab(page, 6);
    await page.locator(".snapshot-list button").first().waitFor();
    if (screen.kind !== "memory") {
      await page.locator(".snapshot-list button").first().click();
      await page.locator(".snapshot-detail").waitFor();
    }
    if (screen.kind === "snapshotDetail") {
      await page.locator(".snapshot-detail .button-row button").first().click();
      await page.locator(".snapshot-entry-list").waitFor();
    }
    if (screen.kind === "knownGood") {
      await page.locator(".snapshot-detail .button-row button.primary").click();
      await page.locator(".milestone-form").waitFor();
    }
    return;
  }
  if (["behavior", "probeBuilder"].includes(screen.kind)) {
    await openTab(page, 4);
    await page.locator(".behavior-row").first().waitFor();
    await page.locator(".probe-panel").waitFor();
    if (screen.kind === "probeBuilder") {
      await page.locator(".probe-panel > .section-head button.primary").click();
      await page.locator(".probe-builder").waitFor();
      if (screen.fillProbe === "api") {
        await page.locator(".probe-builder input").nth(0).fill("Checkout API remains healthy");
        await page.locator(".probe-builder input").nth(1).fill("http://127.0.0.1:4310/health");
        await page.locator(".probe-builder input").nth(2).fill("200");
      }
      if (screen.fillProbe === "cli") {
        await page.locator(".probe-builder select").first().selectOption("CLI");
        await page.locator(".probe-builder input").nth(0).fill("Focused checkout test");
        await page.locator(".probe-builder input").nth(1).fill("node");
        await page.locator(".probe-builder textarea").fill("node_modules/vitest/vitest.mjs\nrun\ntests/checkout/summary.test.ts");
        await page.locator(".probe-builder input").nth(2).fill("0");
      }
    }
    return;
  }
  if (screen.kind === "signal") {
    await openTab(page, 5);
    await page.locator(".signal-explanation").waitFor();
    if (screen.technical) await page.locator(".signal-explanation details summary").click();
    return;
  }
  if (screen.kind === "repair") {
    await openTab(page, 2);
    await page.locator(".repair-workspace-panel").waitFor();
    await page.locator(".repair-workspace-panel button.primary").click();
    await page.locator(".repair-workspace-panel code").first().waitFor();
  }
}

function focusSelector(screen) {
  if (screen.kind === "snapshotDetail" || screen.kind === "knownGood") return ".snapshot-detail";
  if (screen.kind === "behavior" || screen.kind === "probeBuilder") return ".probe-panel";
  if (screen.kind === "signal") return ".signal-explanation";
  if (screen.kind === "repair") return ".repair-workspace-panel";
  return null;
}

function escapeHtml(value) {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

function guideMarkdown() {
  const lines = [
    "# MellowYak Phase 7 Screen Guide",
    "",
    "All screenshots use deterministic synthetic public fixture data. They contain no private repository path, credential, source content, prompt history, provider data, or user data.",
    "",
  ];
  screens.forEach((screen, index) => {
    lines.push(
      `## ${index + 1}. ${screen.title}`,
      "",
      `![${screen.title}](screenshots/${screen.file})`,
      "",
      `- Purpose: ${screen.purpose}`,
      `- Displayed state: ${screen.state}`,
      "- Source of data: Deterministic synthetic Phase 7 fixture data intercepted on the authenticated loopback API boundary.",
      `- Available actions: ${screen.actions}`,
      `- What is known: ${screen.known}`,
      `- What is not known: ${screen.unknown}`,
      `- Expected next step: ${screen.next}`,
      "",
    );
  });
  return `${lines.join("\n")}\n`;
}

function guideHtml() {
  const sections = screens.map((screen, index) => `<section><h1>${index + 1}. ${escapeHtml(screen.title)}</h1><img src="screenshots/${escapeHtml(screen.file)}" alt="${escapeHtml(screen.title)}"><dl><dt>Purpose</dt><dd>${escapeHtml(screen.purpose)}</dd><dt>Displayed state</dt><dd>${escapeHtml(screen.state)}</dd><dt>Source of data</dt><dd>Deterministic synthetic Phase 7 fixture data intercepted on the authenticated loopback API boundary.</dd><dt>Available actions</dt><dd>${escapeHtml(screen.actions)}</dd><dt>What is known</dt><dd>${escapeHtml(screen.known)}</dd><dt>What is not known</dt><dd>${escapeHtml(screen.unknown)}</dd><dt>Expected next step</dt><dd>${escapeHtml(screen.next)}</dd></dl></section>`).join("\n");
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>MellowYak Phase 7 Screen Guide</title><style>@page{size:A4 landscape;margin:10mm}*{box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;color:#102334;margin:0}section{page-break-after:always}h1{font-size:20px;margin:0 0 7px}img{display:block;max-width:100%;max-height:128mm;margin:0 auto 7px;border:1px solid #cad6dc;border-radius:8px}dl{display:grid;grid-template-columns:145px 1fr;gap:3px 10px;margin:0;font-size:9.5px;line-height:1.25}dt{font-weight:800}dd{margin:0}.cover{display:grid;place-items:center;text-align:center;min-height:170mm}.cover h1{font-size:34px}.cover p{max-width:760px;font-size:15px}</style></head><body><section class="cover"><div><h1>MellowYak Phase 7</h1><h2>Runtime Profiles, Snapshot Memory, and Universal Probes</h2><p>Deterministic synthetic delivery catalog · English base + Hebrew RTL · 2026-08-24</p><p>No private source, user path, credential, prompt, provider data, or live evidence is included.</p></div></section>${sections}</body></html>`;
}

await mkdir(screenshots, { recursive: true });
const browserPath = await findBrowser();
const server = spawn("npm", ["run", "dev", "--", "--host", "127.0.0.1", "--port", String(port), "--strictPort"], { cwd: desktop, stdio: ["ignore", "pipe", "pipe"] });
let serverOutput = "";
server.stdout.on("data", (chunk) => { serverOutput += chunk.toString(); });
server.stderr.on("data", (chunk) => { serverOutput += chunk.toString(); });

try {
  await waitForServer();
  const browser = await chromium.launch({ executablePath: browserPath, headless: true });
  try {
    for (const screen of captureScreens) {
      const context = await browser.newContext({ locale: screen.locale, viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1, colorScheme: "dark", reducedMotion: "reduce" });
      await context.addInitScript(() => {
        let callbackId = 0;
        const callbacks = new Map();
        window.__TAURI_INTERNALS__ = {
          callbacks,
          transformCallback: (callback, once = false) => { callbackId += 1; callbacks.set(callbackId, { callback, once }); return callbackId; },
          unregisterCallback: (id) => callbacks.delete(id),
          invoke: async (command) => {
            if (command === "engine_bootstrap") return { host: "127.0.0.1", port: 43127, token: "phase7-public-review-only" };
            if (command === "plugin:dialog|open") return "/fixture/local-service";
            if (command === "plugin:updater|check") return null;
            if (command.includes("listen")) return 1;
            if (command === "take_pending_route") return null;
            if (command === "get_start_at_login") return false;
            return null;
          },
        };
      });
      const page = await context.newPage();
      await page.route(`${engineOrigin}/**`, async (route) => {
        let body = {};
        try { body = route.request().postDataJSON() ?? {}; } catch { /* no JSON body */ }
        const payload = responseFor(screen, route.request().url(), route.request().method(), body);
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(payload) });
      });
      await page.goto(baseUrl, { waitUntil: "networkidle" });
      await prepareScreen(page, screen);
      const visibleCopy = await page.locator("body").innerText();
      if (visibleCopy.includes("Unknown probe type") || visibleCopy.includes("סוג בדיקה לא ידוע")) {
        throw new Error(`${screen.file}: stale probe type rendered as unknown`);
      }
      if (screen.locale.startsWith("he") && await page.locator('main[dir="rtl"]').count() !== 1) {
        throw new Error(`${screen.file}: Hebrew screen is not rooted in RTL`);
      }
      if (screen.file === "07-memory-save-points.png" && await page.locator(".snapshot-list .pin").count()) {
        throw new Error(`${screen.file}: unexpected pin/cursor-like marker in the Save Point list`);
      }
      const focus = focusSelector(screen);
      if (focus) await page.locator(focus).first().scrollIntoViewIfNeeded();
      else await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(200);
      await page.screenshot({ path: path.join(screenshots, screen.file), fullPage: !focus && screen.kind === "wizard" });
      await context.close();
      process.stdout.write(`${screen.file}\n`);
    }

    await writeFile(path.join(delivery, "PHASE_7_SCREEN_GUIDE.md"), guideMarkdown());
    await writeFile(path.join(delivery, "PHASE_7_SCREEN_GUIDE.html"), guideHtml());
    await writeFile(path.join(delivery, "PHASE_7_SCREENSHOT_MANIFEST.json"), `${JSON.stringify({ schema: "mellowyak.phase7.screenshot-delivery.v1", generated_at: NOW, fixture: "deterministic_synthetic_public", screenshots: screens.map(({ file, locale, title, purpose, state, actions, known, unknown, next }) => ({ file: `screenshots/${file}`, locale, title, purpose, displayed_state: state, source_of_data: "deterministic synthetic Phase 7 fixture intercepted at the loopback API boundary", available_actions: actions, known, unknown, expected_next_step: next })) }, null, 2)}\n`);

    const pdfPage = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    await pdfPage.goto(`file://${path.join(delivery, "PHASE_7_SCREEN_GUIDE.html")}`, { waitUntil: "networkidle" });
    await pdfPage.pdf({ path: path.join(delivery, "MellowYak-Phase-7-Screen-Guide.pdf"), format: "A4", landscape: true, printBackground: true, margin: { top: "10mm", right: "10mm", bottom: "10mm", left: "10mm" } });
    await pdfPage.close();
  } finally {
    await browser.close();
  }
} catch (reason) {
  if (serverOutput) process.stderr.write(serverOutput);
  throw reason;
} finally {
  server.kill("SIGTERM");
}
