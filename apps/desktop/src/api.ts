import { invoke } from "@tauri-apps/api/core";
import type { paths } from "./generated/api";

export type Health = paths["/health"]["get"]["responses"][200]["content"]["application/json"];
export type Readiness = paths["/readiness"]["get"]["responses"][200]["content"]["application/json"];
export type Installation = paths["/installation"]["get"]["responses"][200]["content"]["application/json"];
export type Privacy = paths["/settings/privacy"]["get"]["responses"][200]["content"]["application/json"];
export type StoragePaths = paths["/storage/paths"]["get"]["responses"][200]["content"]["application/json"];

export interface EngineBootstrap {
  host: "127.0.0.1" | "::1";
  port: number;
  token: string;
}
export interface SetupSnapshot {
  health: Health;
  readiness: Readiness;
  installation: Installation;
  privacy: Privacy;
  storage: StoragePaths;
}

export interface OnboardingState {
  completed: boolean;
  current_step: string;
  replay_active: boolean;
  selected_path: "real_project" | "demo_lab" | "existing_installation" | null;
  completed_at: string | null;
  requires_first_run: boolean;
  source_modified: false;
}

export interface DisconnectedProject {
  project_id: string;
  project_name: string;
  state: "CONNECTED" | "DISCONNECTED" | "MISSING" | "PAUSED" | "NEEDS_ATTENTION";
  last_known_safe_path: string;
  last_source_identity: { head_sha: string | null; worktree_fingerprint: string | null };
  disconnect_time: string | null;
  data_retained: boolean;
  data_size_bytes: number;
  behavior_count: number;
  regression_count: number;
  last_activity: string;
  source_modified: false;
}

export interface Diagnostics {
  run_id: string;
  desktop_version: string;
  engine_version: string;
  schema_migration: string;
  installation_identity: string;
  local_api_state: string;
  loopback_address: string;
  bearer_token_exposed: false;
  data_root: "<DATA_ROOT>";
  data_root_size_bytes: number;
  evidence_size_bytes: number;
  projects: number;
  snapshot_objects: number;
  incomplete_transactions: number;
  recovery_required: number;
  browser_runtime_available: boolean;
  runtime_adapter_available: boolean;
  tray: TrayState;
  notification_permission: string;
  updater_state: string;
  signing_state: string;
  platform: string;
  architecture: string;
  recent_engine_starts: string[];
  self_test_last_result: string;
  outbound_product_network: false;
  cloud_connected: false;
}

export interface TrayState {
  state: string;
  unread_alert_count: number;
  critical_alert_count: number;
  active_project_count: number;
  paused_project_count: number;
  quiet_mode_active?: boolean;
  projects: Array<{ project_id: string; name: string; monitoring_state: string; muted: boolean }>;
  recent_alerts: Array<{ alert_id: string; severity: string; title_key: string }>;
  private_paths_exposed: false;
  source_content_exposed: false;
}

export interface ActivityPreferences {
  activity_mode: "normal" | "reduced" | "battery_saver";
  notification_permission: string;
  updater_state: string;
  last_update_check_at: string | null;
  core_file_observation: true;
  snapshot_correctness: true;
  critical_alerts: true;
  deferred: string[];
}

export type StartupStatus =
  | "starting"
  | "loading_database"
  | "loading_capabilities"
  | "discovering_projects"
  | "finalizing"
  | "ready"
  | "error";

export interface StartupResult {
  snapshot: SetupSnapshot;
  projects: Project[];
}

export interface GitState {
  available: boolean;
  branch: string | null;
  head_sha: string | null;
  is_detached: boolean;
  is_dirty: boolean;
  staged: string[];
  unstaged: string[];
  untracked: string[];
  ignored_count: number;
  worktree_fingerprint: string;
  error: string | null;
}

export interface ProjectDetection {
  selected_path: string;
  repository_path: string;
  suggested_name: string;
  git: GitState;
  languages: string[];
  language_counts: Record<string, number>;
  frameworks: string[];
  tests: string[];
  runtime_hints: string[];
  candidate_files: number;
  ignored_paths: number;
  relationship_coverage: string;
  unsupported_coverage: string;
  source_remains_local: boolean;
}

export interface ScanRun {
  id: string;
  status: "running" | "completed" | "cancelled" | "failed";
  scan_version: string;
  started_at: string;
  completed_at: string | null;
  total_candidates: number;
  processed_files: number;
  included_files: number;
  excluded_files: number;
  binary_files: number;
  sensitive_files: number;
  failed_files: number;
  unknown_items: number;
  unsupported_files: number;
  test_files: number;
  relationship_count: number;
  duration_seconds: number | null;
  error_summary: string | null;
}

export interface Project {
  id: string;
  display_name: string;
  display_path: string;
  repository_path: string;
  monitoring_mode: "passive" | "paused";
  monitoring_status: string;
  last_scan_status: string | null;
  last_scan_at: string | null;
  created_at: string;
  updated_at: string | null;
  languages: string[];
  frameworks: string[];
  tests: string[];
  runtime_hints: string[];
  git: GitState;
  scan: ScanRun | null;
  source_remains_local: boolean;
  disconnected: boolean;
  source_available: boolean;
  notifications_muted: boolean;
  project_type?: ProjectType;
  runtime_setup_status?: "INCOMPLETE" | "READY" | "READY_WITH_LIMITS";
  observation_level?: "LIGHT" | "DEEP";
  snapshot_retention_days?: number;
  snapshot_soft_cap_bytes?: number;
  phase7?: Record<string, unknown>;
}

export type ProjectType =
  | "WEB_APP"
  | "API_SERVICE"
  | "DESKTOP_APP"
  | "CLI_TOOL"
  | "MOBILE_APP"
  | "BACKGROUND_WORKER"
  | "LIBRARY"
  | "MIXED_POLYGLOT"
  | "OTHER";

export type RuntimeType = "NODE" | "PYTHON" | "PHP" | "TAURI_RUST" | "RUBY" | "JAVA" | "GENERIC";
export type ExecutionMode = "MANAGED" | "EXTERNAL" | "MANUAL";
export type ProbeType = "BROWSER" | "HTTP" | "CLI" | "PROCESS" | "TEST" | "MANUAL";

export interface RuntimeCandidate {
  runtime_type: RuntimeType | string;
  display_name?: string;
  runtime_version?: string | null;
  executable_reference?: string | null;
  relative_working_directory?: string;
  dependency_manifests?: string[];
  test_definitions?: Array<Record<string, unknown>>;
  limitations?: string[];
  detected?: boolean;
  [key: string]: unknown;
}

export interface RuntimeDetection {
  id: string;
  project_id: string;
  status: string;
  candidates: RuntimeCandidate[];
  started_at: string;
  completed_at: string | null;
  error_code: string | null;
}

export interface RuntimeProfileVersion {
  id: string;
  version_number: number;
  runtime_type: RuntimeType | string;
  adapter_version: string;
  execution_mode: ExecutionMode | string;
  executable_reference: string | null;
  argv: string[];
  relative_working_directory: string;
  runtime_version: string | null;
  dependency_fingerprint: string | null;
  health_definition: Record<string, unknown>;
  expected_ports: number[];
  test_definitions: Array<Record<string, unknown>>;
  environment_schema: string[];
  network_policy: string;
  limitations: string[];
  approved_at: string | null;
  detected_at: string | null;
  created_at: string;
}

export interface RuntimeProfile {
  id: string;
  project_id: string;
  display_name: string;
  current_version_id: string;
  primary: boolean;
  status: string;
  current_version: RuntimeProfileVersion;
  versions: RuntimeProfileVersion[];
  created_at: string;
  updated_at: string;
}

export interface RuntimeProfileInput {
  display_name: string;
  runtime_type: RuntimeType | string;
  primary?: boolean;
  execution_mode?: ExecutionMode | string;
  executable_reference?: string | null;
  argv?: string[];
  relative_working_directory?: string;
  runtime_version?: string | null;
  dependency_fingerprint?: string | null;
  health_definition?: Record<string, unknown>;
  expected_ports?: number[];
  test_definitions?: Array<Record<string, unknown>>;
  environment_schema?: string[];
  network_policy?: string;
  limitations?: string[];
  approved?: boolean;
}

export interface RuntimeInstance {
  id: string;
  project_id: string;
  profile_id: string;
  profile_version_id: string;
  correlation_id: string;
  status: string;
  process_id: number | null;
  started_at: string;
  stopped_at: string | null;
  exit_code: number | null;
  observation: Record<string, unknown>;
}

export interface SourceSnapshot {
  id: string;
  project_id: string;
  parent_snapshot_id: string | null;
  episode_id: string | null;
  manifest_digest: string;
  creation_reason: string;
  source_identity: Record<string, unknown>;
  git_anchor: Record<string, unknown>;
  included_count: number;
  excluded_count: number;
  sensitive_count: number;
  unsupported_count: number;
  logical_bytes: number;
  physical_bytes_added: number;
  reused_bytes: number;
  pinned: boolean;
  integrity_status: string;
  created_at: string;
  entries?: Array<Record<string, unknown>>;
  runtime_profile_fingerprints?: Array<Record<string, unknown> | string>;
}

export interface SnapshotMaterialization {
  snapshot_id: string;
  relative_path: string;
  file_count: number;
  logical_bytes: number;
  verified: boolean;
  live_project_modified: false;
}

export interface SourceEpisode {
  id: string;
  project_id: string;
  started_at: string;
  ended_at: string | null;
  event_count: number;
  added_paths: string[];
  modified_paths: string[];
  deleted_paths: string[];
  renamed_paths: Array<Record<string, string>>;
  dependency_changes: string[];
  runtime_events: Array<Record<string, unknown>>;
  base_snapshot_id: string | null;
  resulting_snapshot_id: string | null;
  git_anchor: Record<string, unknown>;
  status: string;
  error_code: string | null;
}

export interface SnapshotMilestone {
  id: string;
  project_id: string;
  snapshot_id: string;
  display_name: string;
  behavior_id: string | null;
  behavior_version_id: string | null;
  probe_version_id: string | null;
  runtime_profile_versions: string[];
  environment_summary: Record<string, unknown>;
  limitations: string[];
  status: string;
  human_attested: boolean;
  pinned: boolean;
  created_at: string;
}

export interface ProbeVersion {
  id: string;
  version_number: number;
  runtime_profile_version_id: string | null;
  definition: Record<string, unknown>;
  timeout_seconds: number;
  retry_policy: Record<string, unknown>;
  expected_result: Record<string, unknown>;
  evidence_policy: Record<string, unknown>;
  source_links: Array<Record<string, unknown>>;
  runtime_links: Array<Record<string, unknown>>;
  approved_at: string | null;
  created_at: string;
}

export interface ProbeDefinition {
  id: string;
  project_id: string;
  behavior_id: string | null;
  display_name: string;
  probe_type: ProbeType | string;
  current_version_id: string;
  status: string;
  current_version: ProbeVersion;
  versions: ProbeVersion[];
  last_run: ProbeRun | null;
  created_at: string;
  updated_at: string;
}

export interface ProbeInput {
  display_name: string;
  probe_type: ProbeType | string;
  behavior_id?: string | null;
  runtime_profile_version_id?: string | null;
  definition?: Record<string, unknown>;
  timeout_seconds?: number;
  retry_policy?: Record<string, unknown>;
  expected_result?: Record<string, unknown>;
  evidence_policy?: Record<string, unknown>;
  source_links?: Array<Record<string, unknown>>;
  runtime_links?: Array<Record<string, unknown>>;
  approved?: boolean;
}

export interface ProbeRun {
  id: string;
  project_id: string;
  probe_id: string;
  probe_version_id: string;
  snapshot_id: string;
  episode_id: string | null;
  runtime_profile_version_id: string | null;
  source_identity: Record<string, unknown>;
  status: string;
  result: string;
  attempt_count: number;
  expected: Record<string, unknown>;
  observed: Record<string, unknown>;
  evidence: Record<string, unknown>;
  limitations: string[];
  reproducible: boolean;
  signal: Record<string, unknown> | null;
  started_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
}

export interface RepairWorkspace {
  id: string;
  project_id: string;
  regression_id: string | null;
  signal_id: string | null;
  snapshot_id: string;
  relative_path: string;
  manifest_digest: string;
  base_manifest_digest?: string | null;
  workspace_manifest_digest?: string | null;
  runtime_profile_versions?: string[];
  validation_policy?: Record<string, unknown>;
  status: string;
  instructions: string | null;
  items: Array<Record<string, unknown>>;
  created_at: string;
  deleted_at: string | null;
}

export interface RepairCandidateFile {
  ordinal: number;
  relative_path: string;
  operation: "ADD" | "MODIFY" | "DELETE" | "RENAME" | "MODE_CHANGE" | string;
  base_digest: string | null;
  candidate_digest: string | null;
  byte_size: number;
  classification: string;
  rename_source?: string | null;
  validation_eligible: boolean;
  apply_eligible: boolean;
  excluded: boolean;
  exclusion_reason?: string | null;
  warning_state?: string | null;
}

export interface RepairCandidate {
  id: string;
  project_id: string;
  workspace_id: string;
  revision: number;
  state: string;
  base_manifest_digest: string;
  workspace_manifest_digest: string;
  candidate_digest: string;
  source_snapshot_id: string;
  file_count: number;
  logical_bytes: number;
  binary_count: number;
  warnings: string[];
  limitations: string[];
  files: RepairCandidateFile[];
  created_at: string;
  updated_at: string;
}

export interface CandidateValidation {
  id: string;
  project_id: string;
  candidate_id: string;
  candidate_digest: string;
  workspace_manifest_digest: string;
  runtime_profile_versions: string[];
  status: string;
  evidence_digest: string | null;
  limitations: string[];
  started_at: string;
  completed_at: string | null;
  items: Array<Record<string, unknown>>;
}

export interface ApplyTransaction {
  id: string;
  project_id: string;
  candidate_id: string;
  validation_id: string;
  state: string;
  expected_source_snapshot_id: string;
  expected_source_manifest_digest: string;
  safety_snapshot_id: string | null;
  post_apply_snapshot_id: string | null;
  confirmation_expires_at: string;
  confirmation_used: boolean;
  confirmation_nonce?: string | null;
  capabilities: string[];
  journal_relative_path: string;
  error_code: string | null;
  files: Array<Record<string, unknown>>;
  events: Array<Record<string, unknown>>;
  rollbacks: Array<Record<string, unknown>>;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface DemoLabRun {
  id: string;
  project_id: string | null;
  synthetic: boolean;
  scenario: string;
  status: string;
  state: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ProductSelfTestRun {
  id: string;
  status: "PASS" | "PARTIAL" | "FAILED" | string;
  steps: Array<Record<string, unknown>>;
  duration_ms: number;
  report_relative_path: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface LocalAlert {
  id: string; project_id: string | null; change_id: string | null; behavior_id: string | null;
  regression_id: string | null; gate_id: string | null; severity: string; category: string;
  title_key: string; summary_key: string; parameters: Record<string, unknown>;
  route: Record<string, unknown>; read: boolean; resolved: boolean; created_at: string; updated_at: string;
}

export interface QuietMode { active: boolean; started_at: string | null; ends_at: string | null; until_turned_off: boolean; allow_critical: boolean; remaining_seconds: number | null; }
export interface NotificationSettings { native_enabled: boolean; regression_enabled: boolean; blocked_gate_enabled: boolean; needs_review_enabled: boolean; project_errors_enabled: boolean; verified_complete_enabled: boolean; regression_resolved_enabled: boolean; show_behavior_name: boolean; show_project_name: boolean; hide_details: boolean; critical_override: boolean; }
export interface ProjectCapabilities { mode: string; source_available: boolean; runtime_available: boolean; available: string[]; unavailable: string[]; future_only: string[]; source_remains_local: true; }

export interface ImpactSummary {
  files_indexed: number;
  languages: number;
  language_counts: Record<string, number>;
  direct_relationships: number;
  tests_found: number;
  sensitive_files: number;
  unknown_references: number;
  unsupported_files: number;
  stale_relationships: number;
}

export interface Change {
  id: string;
  project_id: string;
  change_kind: "committed" | "uncommitted_worktree";
  revision: number;
  base_head_sha: string | null;
  head_sha: string | null;
  worktree_fingerprint: string;
  changed_paths: string[];
  task_intent: string | null;
  status: "change_detected" | "no_changes";
  created_at: string;
  updated_at: string;
}

export interface ImpactAnalysis {
  id: string;
  project_id: string;
  change_id: string;
  analysis_revision: number;
  base_head_sha: string | null;
  head_sha: string | null;
  worktree_fingerprint: string;
  scan_revision: string | null;
  algorithm_version: string;
  status: string;
  changed_file_count: number;
  impacted_node_count: number;
  unknown_count: number;
  stale_count: number;
  heuristic_count: number;
  truncated: boolean;
  truncation_reasons: string[];
  duration_ms: number;
  stale: boolean;
  stale_reasons: string[];
  created_at: string;
}

export interface ImpactResult {
  id: string;
  node_id: string | null;
  node_type: string;
  display_name: string;
  relative_path: string | null;
  impact_class: string;
  minimum_depth: number;
  strongest_provenance: string;
  stale: boolean;
  unknown: boolean;
  explanation: string;
  path_count: number;
  ranking_score: number;
  ranking_reasons: string[];
  unknown_reason: string | null;
}

export interface ChangeImpact {
  analysis: ImpactAnalysis;
  results: ImpactResult[];
}

export interface ContextReceipt {
  schema: "mellowyak.context_receipt.v1";
  id: string;
  project: { id: string; name: string };
  change_id: string;
  analysis_id: string;
  request: string | null;
  source_revision: Record<string, unknown>;
  selected_files: Array<{
    relative_path: string;
    type: string;
    reason_selected: string;
    relationship_provenance: string;
    relevance_class: string;
    stale: boolean;
    size: number;
    content_eligible: boolean;
    selection_reasons: string[];
  }>;
  selected_symbols: string[];
  related_tests: string[];
  relationship_paths: Array<Record<string, unknown>>;
  constraints: Record<string, unknown>;
  unknowns: Array<{ path: string; reason: string }>;
  excluded_context: Array<{ path: string; reason: string }>;
  selection_reasons: string[];
  size_metrics: Record<string, number>;
  truncated: boolean;
  stale: boolean;
  source_uploaded: false;
  created_at: string;
}

export interface BehaviorCandidate {
  id: string;
  title?: string;
  source_type?: string;
  source_key?: string;
  status: "CANDIDATE" | "DISMISSED" | "PROMOTED_STUB";
  evidence?: string;
  verification: "not_configured";
  not_protected: true;
  created_at?: string;
  updated_at?: string;
  behavior_draft_id?: string;
}

export interface BehaviorVersion {
  id: string;
  version_number: number;
  title: string;
  description: string;
  expected_outcome: string;
  criticality: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  persona: string;
  preconditions: string;
  starting_state: string;
  expected_assertions: Array<Record<string, unknown>>;
  limitations: string[];
  verification_not_configured: true;
  created_by_type: string;
  source_candidate_id: string | null;
  content_digest: string;
  supersedes_version_id: string | null;
  source_revision: Record<string, unknown>;
  created_at: string;
}

export interface ProtectedBehavior {
  id: string;
  project_id: string;
  stable_key: string;
  display_name: string;
  lifecycle_state: "DRAFT" | "PROTECTED" | "ARCHIVED";
  current_version_id: string;
  last_accepted_baseline_id: string | null;
  always_recheck: boolean;
  current_version: BehaviorVersion;
  versions: BehaviorVersion[];
  links: Array<{ id: string; link_type: string; link_key: string; provenance: string }>;
  baselines: Array<{
    id: string;
    status: "CAPTURED" | "REVIEWED" | "ACCEPTED" | "REVOKED" | "STALE";
    behavior_version_id: string;
    evidence_bundle_id: string;
    created_at: string;
  }>;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface RuntimeConfiguration {
  id: string;
  project_id: string;
  display_name: string;
  base_url: string;
  allowed_origin: string;
  starting_path: string;
  viewport_width: number;
  viewport_height: number;
  locale: string;
  timezone: string;
  browser_type: "chromium";
  capture_screenshots: boolean;
  capture_trace: boolean;
  capture_video: boolean;
  capture_network: boolean;
  created_at: string;
  updated_at: string;
}

export interface BrowserCapture {
  id: string;
  project_id: string;
  behavior_id: string;
  behavior_version_id: string;
  runtime_configuration_id: string;
  status: "STARTING" | "RECORDING" | "STOPPING" | "REVIEW_REQUIRED" | "ACCEPTED" | "CANCELLED" | "FAILED" | "STALE_SOURCE";
  entry_url: string;
  source_revision: Record<string, unknown>;
  source_stale: boolean;
  steps: Array<{
    id: string;
    ordinal: number;
    event_type: string;
    page_url: string;
    selector: string | null;
    metadata: Record<string, unknown>;
    occurred_at: string;
    included: boolean;
    label: string;
  }>;
  observations: Array<{
    id: string;
    observation_type: string;
    metadata: Record<string, unknown>;
    observed_at: string;
    included: boolean;
  }>;
  started_at: string;
  stopped_at: string | null;
  error_code: string | null;
  paused: boolean;
  browser_version: string | null;
  expected_assertions: Array<Record<string, unknown>>;
}

export interface EvidenceArtifact {
  id: string;
  project_id: string;
  sha256: string;
  size_bytes: number;
  media_type: string;
  redaction_state: string;
  integrity_verified: boolean;
  created_at: string;
}

export interface EvidenceBundle {
  id: string;
  project_id: string;
  capture_id: string;
  manifest_sha256: string;
  status: string;
  bundle_type: string;
  verification_run_id: string | null;
  items: Array<{ ordinal: number; item_type: string; artifact: EvidenceArtifact }>;
  created_at: string;
}

export interface EvidenceList {
  bundles: Array<{ id: string; capture_id: string; manifest_sha256: string; status: string; bundle_type: string; verification_run_id: string | null; created_at: string }>;
  artifacts: EvidenceArtifact[];
}

export interface ImpactExplorerItem {
  node: { type: string; label: string; relative_path: string | null };
  relationships: Array<{
    direction: "incoming" | "outgoing";
    type: string;
    target_type: string;
    target: string;
    target_path: string | null;
    provenance: string;
    parser_adapter: string;
    source_scan_revision: string;
    stale: boolean;
  }>;
  recent_changes: string[];
}

export interface ProtectionPlanItem {
  id: string;
  behavior_id: string;
  behavior_name: string;
  behavior_version_id: string;
  baseline_id: string | null;
  selection_class: "REQUIRED" | "SUGGESTED" | "SKIPPED" | "NEEDS_REVIEW" | "UNKNOWN";
  selection_reason: string;
  impact_path: Array<Record<string, unknown>>;
  criticality: string;
  verification_method: "BROWSER_REPLAY" | "HUMAN_ATTESTATION";
  current_result_id: string | null;
}

export interface ProtectionPlan {
  id: string;
  project_id: string;
  change_id: string;
  source_identity: Record<string, unknown>;
  status: string;
  counts: { required: number; suggested: number; skipped: number; needs_review: number; unknown: number };
  items: ProtectionPlanItem[];
}

export interface VerificationRunItem {
  id: string;
  behavior_id: string;
  result: string;
  adapter: string;
  evidence_bundle_id: string | null;
  duration_ms: number;
  failure_reason: string | null;
  assertions: Array<Record<string, unknown>>;
}

export interface VerificationRun {
  id: string;
  project_id: string;
  change_id: string;
  plan_id: string;
  source_identity: Record<string, unknown>;
  status: string;
  items: VerificationRunItem[];
}

export interface GateDecision {
  id: string;
  state: string;
  reason: string;
  source_identity: Record<string, unknown>;
  limitations: string[];
  decision_digest: string;
}

export interface RegressionFinding {
  id: string;
  change_id: string;
  behavior_id: string;
  baseline_id: string | null;
  verification_run_item_id: string;
  status: string;
  decision_reason: string;
  source_identity: Record<string, unknown>;
}

export interface RepairContext {
  id: string;
  schema_version: string;
  digest: string;
  size_bytes: number;
  payload: Record<string, unknown>;
  saved_relative_path: string | null;
}

let bootstrapPromise: Promise<EngineBootstrap> | undefined;

async function waitForBootstrap(): Promise<EngineBootstrap> {
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    try {
      return await invoke<EngineBootstrap>("engine_bootstrap");
    } catch (reason) {
      if (!String(reason).includes("ENGINE_STARTING")) throw reason;
      await new Promise((resolve) => window.setTimeout(resolve, 250));
    }
  }
  throw new Error("SIDECAR_HANDSHAKE_TIMEOUT");
}

function bootstrap(): Promise<EngineBootstrap> {
  bootstrapPromise ??= waitForBootstrap();
  return bootstrapPromise;
}

async function engineFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const connection = await bootstrap();
  const response = await fetch(`http://${connection.host}:${connection.port}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${connection.token}`,
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `LOCAL_ENGINE_${response.status}`);
  }
  const body = await response.text();
  return (body ? JSON.parse(body) : {}) as T;
}

export async function loadSetupSnapshot(): Promise<SetupSnapshot> {
  const [health, readiness, installation, privacy, storage] = await Promise.all([
    engineFetch<Health>("/health"),
    engineFetch<Readiness>("/readiness"),
    engineFetch<Installation>("/installation"),
    engineFetch<Privacy>("/settings/privacy"),
    engineFetch<StoragePaths>("/storage/paths"),
  ]);
  return { health, readiness, installation, privacy, storage };
}

export async function loadStartup(
  onStatus: (status: Exclude<StartupStatus, "ready" | "error">) => void,
): Promise<StartupResult> {
  onStatus("starting");
  const health = await engineFetch<Health>("/health");
  if (health.status !== "ready") throw new Error("LOCAL_ENGINE_UNAVAILABLE");

  onStatus("loading_database");
  if (health.database_status !== "ready") throw new Error("LOCAL_ENGINE_UNAVAILABLE");
  const [installation, storage] = await Promise.all([
    engineFetch<Installation>("/installation"),
    engineFetch<StoragePaths>("/storage/paths"),
  ]);

  onStatus("loading_capabilities");
  const [readiness, privacy] = await Promise.all([
    engineFetch<Readiness>("/readiness"),
    engineFetch<Privacy>("/settings/privacy"),
  ]);
  if (!readiness.ready) throw new Error("LOCAL_ENGINE_UNAVAILABLE");

  onStatus("discovering_projects");
  const projects = await listProjects();

  onStatus("finalizing");
  const snapshot = { health, readiness, installation, privacy, storage };
  return { snapshot, projects };
}

export async function openDataFolder(): Promise<void> {
  await engineFetch("/system/open-data-folder", { method: "POST", body: "{}" });
}

export async function listProjects(): Promise<Project[]> {
  const response = await engineFetch<{ projects: Project[] }>("/projects");
  return response.projects;
}

export async function getOnboarding(): Promise<OnboardingState> {
  return engineFetch<OnboardingState>("/app/onboarding");
}

export async function updateOnboarding(
  currentStep: string,
  selectedPath: OnboardingState["selected_path"],
  completed = false,
): Promise<OnboardingState> {
  return engineFetch<OnboardingState>("/app/onboarding", {
    method: "PUT",
    body: JSON.stringify({ current_step: currentStep, selected_path: selectedPath, completed }),
  });
}

export async function replayOnboarding(): Promise<OnboardingState> {
  return engineFetch<OnboardingState>("/app/onboarding/replay", { method: "POST", body: "{}" });
}

export async function listDisconnectedProjects(): Promise<DisconnectedProject[]> {
  const response = await engineFetch<{ projects: DisconnectedProject[] }>("/projects/disconnected");
  return response.projects;
}

export async function previewProjectIdentity(projectId: string, path: string): Promise<Record<string, unknown>> {
  return engineFetch(`/projects/${encodeURIComponent(projectId)}/identity-preview?path=${encodeURIComponent(path)}`);
}

export async function reconnectProject(projectId: string, path: string): Promise<Record<string, unknown>> {
  return engineFetch(`/projects/${encodeURIComponent(projectId)}/reconnect`, {
    method: "POST",
    body: JSON.stringify({ path }),
  });
}

export async function relocateProject(projectId: string, path: string): Promise<Record<string, unknown>> {
  return engineFetch(`/projects/${encodeURIComponent(projectId)}/relocate`, {
    method: "POST",
    body: JSON.stringify({ path }),
  });
}

export async function getDiagnostics(): Promise<Diagnostics> {
  return engineFetch<Diagnostics>("/diagnostics");
}

export async function verifyStorageIntegrity(): Promise<Record<string, unknown>> {
  return engineFetch("/diagnostics/storage-integrity", { method: "POST", body: "{}" });
}

export async function exportSupportBundle(): Promise<Record<string, unknown>> {
  return engineFetch("/diagnostics/support-bundle", { method: "POST", body: "{}" });
}

export async function getActivityPreferences(): Promise<ActivityPreferences> {
  return engineFetch<ActivityPreferences>("/app/activity-mode");
}

export async function setActivityMode(
  activityMode: ActivityPreferences["activity_mode"],
): Promise<ActivityPreferences> {
  return engineFetch<ActivityPreferences>("/app/activity-mode", {
    method: "PUT",
    body: JSON.stringify({ activity_mode: activityMode }),
  });
}

export async function getTrayState(): Promise<TrayState> {
  return engineFetch<TrayState>("/tray/state");
}

export async function updateNativeTray(state: TrayState): Promise<void> {
  await invoke("update_tray_state", { state });
}

export async function validateNotificationRoute(route: Record<string, string>): Promise<Record<string, unknown>> {
  return engineFetch("/notifications/activate", {
    method: "POST",
    body: JSON.stringify({ route }),
  });
}

export async function detectProject(path: string): Promise<ProjectDetection> {
  return engineFetch<ProjectDetection>("/projects/detect", {
    method: "POST",
    body: JSON.stringify({ path }),
  });
}

export async function createProject(
  path: string,
  displayName: string,
  monitoringMode: "passive" | "paused" = "passive",
  options: {
    project_type?: ProjectType;
    observation_level?: "LIGHT" | "DEEP";
    snapshot_retention_days?: number;
    snapshot_soft_cap_bytes?: number;
  } = {},
): Promise<Project> {
  return engineFetch<Project>("/projects", {
    method: "POST",
    body: JSON.stringify({ path, display_name: displayName, monitoring_mode: monitoringMode, ...options }),
  });
}

export async function getProject(projectId: string): Promise<Project> {
  return engineFetch<Project>(`/projects/${encodeURIComponent(projectId)}`);
}

export async function getImpactSummary(projectId: string): Promise<ImpactSummary> {
  return engineFetch<ImpactSummary>(`/projects/${encodeURIComponent(projectId)}/impact/summary`);
}

export async function getCurrentChange(projectId: string): Promise<Change> {
  return engineFetch<Change>(`/projects/${encodeURIComponent(projectId)}/changes/current`);
}

export async function setChangeIntent(projectId: string, changeId: string, intent: string): Promise<Change> {
  return engineFetch<Change>(`/projects/${encodeURIComponent(projectId)}/changes/${encodeURIComponent(changeId)}/intent`, {
    method: "POST",
    body: JSON.stringify({ intent }),
  });
}

export async function analyzeChange(projectId: string, changeId: string): Promise<ChangeImpact> {
  return engineFetch<ChangeImpact>(`/projects/${encodeURIComponent(projectId)}/changes/${encodeURIComponent(changeId)}/analyze`, {
    method: "POST",
    body: "{}",
  });
}

export async function getChangeImpact(projectId: string, changeId: string): Promise<ChangeImpact> {
  return engineFetch<ChangeImpact>(`/projects/${encodeURIComponent(projectId)}/changes/${encodeURIComponent(changeId)}/impact`);
}

export async function getImpactPaths(projectId: string, changeId: string): Promise<Array<Record<string, unknown>>> {
  const response = await engineFetch<{ paths: Array<Record<string, unknown>> }>(`/projects/${encodeURIComponent(projectId)}/changes/${encodeURIComponent(changeId)}/impact/paths`);
  return response.paths;
}

export async function createContextReceipt(projectId: string, changeId: string): Promise<ContextReceipt> {
  return engineFetch<ContextReceipt>(`/projects/${encodeURIComponent(projectId)}/changes/${encodeURIComponent(changeId)}/context-receipt`, {
    method: "POST",
    body: "{}",
  });
}

export async function getContextReceipt(projectId: string, changeId: string): Promise<ContextReceipt> {
  return engineFetch<ContextReceipt>(`/projects/${encodeURIComponent(projectId)}/changes/${encodeURIComponent(changeId)}/context-receipt`);
}

export async function listBehaviorCandidates(projectId: string): Promise<BehaviorCandidate[]> {
  const response = await engineFetch<{ candidates: BehaviorCandidate[] }>(`/projects/${encodeURIComponent(projectId)}/behavior-candidates`);
  return response.candidates;
}

export async function updateBehaviorCandidate(projectId: string, candidateId: string, action: "keep" | "dismiss" | "prepare"): Promise<BehaviorCandidate> {
  return engineFetch<BehaviorCandidate>(`/projects/${encodeURIComponent(projectId)}/behavior-candidates/${encodeURIComponent(candidateId)}/${action}`, {
    method: "POST",
    body: "{}",
  });
}

export async function listBehaviors(projectId: string): Promise<ProtectedBehavior[]> {
  const response = await engineFetch<{ behaviors: ProtectedBehavior[] }>(`/projects/${encodeURIComponent(projectId)}/behaviors`);
  return response.behaviors;
}

export async function createBehavior(
  projectId: string,
  value: { title: string; description: string; expected_outcome: string; criticality: string; persona: string; preconditions: string },
): Promise<ProtectedBehavior> {
  return engineFetch<ProtectedBehavior>(`/projects/${encodeURIComponent(projectId)}/behaviors`, {
    method: "POST",
    body: JSON.stringify(value),
  });
}

export async function updateBehavior(
  projectId: string,
  behaviorId: string,
  value: { title: string; description: string; expected_outcome: string; criticality: string; persona: string; preconditions: string },
): Promise<ProtectedBehavior> {
  return engineFetch<ProtectedBehavior>(`/projects/${encodeURIComponent(projectId)}/behaviors/${encodeURIComponent(behaviorId)}/versions`, {
    method: "POST",
    body: JSON.stringify(value),
  });
}

export async function archiveBehavior(projectId: string, behaviorId: string): Promise<ProtectedBehavior> {
  return engineFetch<ProtectedBehavior>(`/projects/${encodeURIComponent(projectId)}/behaviors/${encodeURIComponent(behaviorId)}/archive`, {
    method: "POST",
    body: "{}",
  });
}

export async function listRuntimes(projectId: string): Promise<RuntimeConfiguration[]> {
  const response = await engineFetch<{ runtimes: RuntimeConfiguration[] }>(`/projects/${encodeURIComponent(projectId)}/runtimes`);
  return response.runtimes;
}

export async function configureRuntime(projectId: string, displayName: string, baseUrl: string): Promise<RuntimeConfiguration> {
  return engineFetch<RuntimeConfiguration>(`/projects/${encodeURIComponent(projectId)}/runtimes`, {
    method: "POST",
    body: JSON.stringify({ display_name: displayName, base_url: baseUrl }),
  });
}

export async function listCaptures(projectId: string): Promise<BrowserCapture[]> {
  const response = await engineFetch<{ captures: BrowserCapture[] }>(`/projects/${encodeURIComponent(projectId)}/captures`);
  return response.captures;
}

export async function startCapture(projectId: string, behaviorId: string, runtimeConfigurationId: string): Promise<BrowserCapture> {
  return engineFetch<BrowserCapture>(`/projects/${encodeURIComponent(projectId)}/captures`, {
    method: "POST",
    body: JSON.stringify({ behavior_id: behaviorId, runtime_configuration_id: runtimeConfigurationId }),
  });
}

export async function stopCapture(projectId: string, captureId: string): Promise<BrowserCapture> {
  return engineFetch<BrowserCapture>(`/projects/${encodeURIComponent(projectId)}/captures/${encodeURIComponent(captureId)}/stop`, {
    method: "POST",
    body: "{}",
  });
}

export async function pauseCapture(projectId: string, captureId: string): Promise<BrowserCapture> {
  return engineFetch<BrowserCapture>(`/projects/${encodeURIComponent(projectId)}/captures/${encodeURIComponent(captureId)}/pause`, { method: "POST", body: "{}" });
}

export async function resumeCapture(projectId: string, captureId: string): Promise<BrowserCapture> {
  return engineFetch<BrowserCapture>(`/projects/${encodeURIComponent(projectId)}/captures/${encodeURIComponent(captureId)}/resume`, { method: "POST", body: "{}" });
}

export async function submitCaptureReview(
  projectId: string,
  captureId: string,
  expectedAssertions: Array<Record<string, unknown>>,
  notes: string,
  stepUpdates: Array<{ id: string; label?: string; included?: boolean }> = [],
  excludedObservationIds: string[] = [],
): Promise<BrowserCapture> {
  return engineFetch<BrowserCapture>(`/projects/${encodeURIComponent(projectId)}/captures/${encodeURIComponent(captureId)}/review`, {
    method: "POST",
    body: JSON.stringify({ expected_assertions: expectedAssertions, notes, step_updates: stepUpdates, excluded_observation_ids: excludedObservationIds }),
  });
}

export async function revokeBaseline(projectId: string, behaviorId: string, deleteEvidence = false): Promise<void> {
  await engineFetch(`/projects/${encodeURIComponent(projectId)}/behaviors/${encodeURIComponent(behaviorId)}/baseline/revoke`, {
    method: "POST", body: JSON.stringify({ confirmation: true, delete_evidence: deleteEvidence }),
  });
}

export async function cancelCapture(projectId: string, captureId: string): Promise<BrowserCapture> {
  return engineFetch<BrowserCapture>(`/projects/${encodeURIComponent(projectId)}/captures/${encodeURIComponent(captureId)}/cancel`, {
    method: "POST",
    body: "{}",
  });
}

export async function acceptBaseline(projectId: string, captureId: string, reviewer: string, notes: string): Promise<{ evidence_bundle_id: string }> {
  return engineFetch<{ evidence_bundle_id: string }>(`/projects/${encodeURIComponent(projectId)}/captures/${encodeURIComponent(captureId)}/accept-baseline`, {
    method: "POST",
    body: JSON.stringify({ reviewer, notes }),
  });
}

export async function getEvidenceBundle(projectId: string, bundleId: string): Promise<EvidenceBundle> {
  return engineFetch<EvidenceBundle>(`/projects/${encodeURIComponent(projectId)}/evidence/bundles/${encodeURIComponent(bundleId)}`);
}

export async function listEvidence(projectId: string): Promise<EvidenceList> {
  return engineFetch<EvidenceList>(`/projects/${encodeURIComponent(projectId)}/evidence`);
}

export async function deleteEvidenceArtifact(projectId: string, artifactId: string): Promise<void> {
  await engineFetch(`/projects/${encodeURIComponent(projectId)}/evidence/artifacts/${encodeURIComponent(artifactId)}`, { method: "DELETE" });
}

export async function searchImpact(projectId: string, query: string): Promise<ImpactExplorerItem[]> {
  const response = await engineFetch<{ results: ImpactExplorerItem[] }>(`/projects/${encodeURIComponent(projectId)}/impact/search?query=${encodeURIComponent(query)}`);
  return response.results;
}

export async function startProjectScan(projectId: string): Promise<void> {
  await engineFetch(`/projects/${encodeURIComponent(projectId)}/scan`, {
    method: "POST",
    body: "{}",
  });
}

export async function cancelProjectScan(projectId: string): Promise<void> {
  await engineFetch(`/projects/${encodeURIComponent(projectId)}/scan/cancel`, {
    method: "POST",
    body: "{}",
  });
}

export async function setProjectMonitoring(projectId: string, active: boolean): Promise<void> {
  await engineFetch(
    `/projects/${encodeURIComponent(projectId)}/monitoring/${active ? "resume" : "pause"}`,
    { method: "POST", body: "{}" },
  );
}

export async function openProjectFolder(projectId: string): Promise<void> {
  await engineFetch(`/projects/${encodeURIComponent(projectId)}/open-folder`, {
    method: "POST",
    body: "{}",
  });
}

export async function listAlerts(state = "all"): Promise<LocalAlert[]> {
  const response = await engineFetch<{ alerts?: LocalAlert[] }>(`/alerts?state=${encodeURIComponent(state)}`);
  return Array.isArray(response.alerts) ? response.alerts : [];
}
export async function unreadAlertCount(): Promise<number> { return (await engineFetch<{count:number}>("/alerts/unread-count")).count; }
export async function setAlertState(id: string, action: "read"|"unread"|"resolve"): Promise<LocalAlert> { return engineFetch<LocalAlert>(`/alerts/${encodeURIComponent(id)}/${action}`, {method:"POST",body:"{}"}); }
export async function clearResolvedAlerts(): Promise<number> { return (await engineFetch<{cleared:number}>("/alerts/clear-resolved",{method:"POST",body:"{}"})).cleared; }
export async function getNotificationSettings(): Promise<NotificationSettings> { return engineFetch<NotificationSettings>("/settings/notifications"); }
export async function putNotificationSettings(value: Partial<NotificationSettings>): Promise<NotificationSettings> { return engineFetch<NotificationSettings>("/settings/notifications",{method:"PUT",body:JSON.stringify(value)}); }
export async function getQuietMode(): Promise<QuietMode> { return engineFetch<QuietMode>("/settings/quiet-mode"); }
export async function startQuietMode(duration: "one_hour"|"until_tomorrow"|"until_off", allowCritical=false): Promise<QuietMode> { return engineFetch<QuietMode>("/settings/quiet-mode/start",{method:"POST",body:JSON.stringify({duration,allow_critical:allowCritical})}); }
export async function stopQuietMode(): Promise<QuietMode> { return engineFetch<QuietMode>("/settings/quiet-mode/stop",{method:"POST",body:"{}"}); }
export async function getProjectCapabilities(projectId: string): Promise<ProjectCapabilities> {
  const response = await engineFetch<Partial<ProjectCapabilities>>(
    `/projects/${encodeURIComponent(projectId)}/capabilities`,
  );
  return {
    mode: response.mode ?? "local_source",
    source_available: response.source_available ?? true,
    runtime_available: response.runtime_available ?? false,
    available: Array.isArray(response.available) ? response.available : [],
    unavailable: Array.isArray(response.unavailable) ? response.unavailable : [],
    future_only: Array.isArray(response.future_only) ? response.future_only : [],
    source_remains_local: true,
  };
}
export async function setProjectMuted(projectId:string, muted:boolean): Promise<void> { await engineFetch(`/projects/${encodeURIComponent(projectId)}/notification-preferences`,{method:"PUT",body:JSON.stringify({muted})}); }
export async function disconnectProject(projectId:string): Promise<void> { await engineFetch(`/projects/${encodeURIComponent(projectId)}/disconnect`,{method:"POST",body:"{}"}); }
export async function deletionPreview(projectId:string): Promise<Record<string,unknown>> { return engineFetch(`/projects/${encodeURIComponent(projectId)}/deletion-preview`); }
export async function deleteProjectLocalData(projectId:string, confirmation:string): Promise<void> { await engineFetch(`/projects/${encodeURIComponent(projectId)}/delete-local-data`,{method:"POST",body:JSON.stringify({confirmation})}); }
export async function getBackgroundStatus(): Promise<Record<string,boolean>> { return engineFetch("/app/background-status"); }
export async function putBackgroundStatus(value:Record<string,boolean>): Promise<Record<string,boolean>> { return engineFetch("/app/background-status",{method:"PUT",body:JSON.stringify(value)}); }
export async function setDesktopCloseBehavior(enabled:boolean): Promise<void> { await invoke("set_keep_running_on_close",{enabled}); }
export async function getDesktopStartAtLogin(): Promise<boolean> { return invoke<boolean>("get_start_at_login"); }
export async function setDesktopStartAtLogin(enabled:boolean): Promise<boolean> { return invoke<boolean>("set_start_at_login",{enabled}); }
export async function takePendingDesktopRoute(): Promise<string|null> { return invoke<string|null>("take_pending_route"); }
export async function showDesktopNotification(title:string,body:string,route:string): Promise<void> { await invoke("show_native_notification",{title,body,route}); }

export async function createProtectionPlan(projectId: string, changeId: string): Promise<ProtectionPlan> {
  return engineFetch<ProtectionPlan>(`/projects/${encodeURIComponent(projectId)}/changes/${encodeURIComponent(changeId)}/protection-plan`, { method: "POST", body: "{}" });
}

export async function getProtectionPlan(projectId: string, changeId: string): Promise<ProtectionPlan> {
  const response = await engineFetch<Partial<ProtectionPlan>>(
    `/projects/${encodeURIComponent(projectId)}/changes/${encodeURIComponent(changeId)}/protection-plan`,
  );
  if (!response.id || !response.counts || !Array.isArray(response.items)) {
    throw new Error("PROTECTION_PLAN_NOT_AVAILABLE");
  }
  return response as ProtectionPlan;
}

export async function verifyRequired(projectId: string, changeId: string, planId: string, itemIds: string[] = []): Promise<VerificationRun> {
  return engineFetch<VerificationRun>(`/projects/${encodeURIComponent(projectId)}/changes/${encodeURIComponent(changeId)}/verify`, { method: "POST", body: JSON.stringify({ plan_id: planId, item_ids: itemIds }) });
}

export async function cancelVerification(projectId: string, runId: string): Promise<VerificationRun> {
  return engineFetch<VerificationRun>(`/projects/${encodeURIComponent(projectId)}/verification-runs/${encodeURIComponent(runId)}/cancel`, { method: "POST", body: "{}" });
}

export async function openEvidenceArtifact(projectId: string, artifactId: string): Promise<void> {
  await engineFetch(`/projects/${encodeURIComponent(projectId)}/evidence/${encodeURIComponent(artifactId)}/open-local`, { method: "POST", body: "{}" });
}

export async function retryVerification(projectId: string, runId: string): Promise<VerificationRun> {
  return engineFetch<VerificationRun>(`/projects/${encodeURIComponent(projectId)}/verification-runs/${encodeURIComponent(runId)}/retry`, { method: "POST", body: "{}" });
}

export async function submitHumanResult(projectId: string, runId: string, runItemId: string, result: string, note: string): Promise<VerificationRun> {
  return engineFetch<VerificationRun>(`/projects/${encodeURIComponent(projectId)}/verification-runs/${encodeURIComponent(runId)}/human-result`, { method: "POST", body: JSON.stringify({ run_item_id: runItemId, result, note, confirmed: true }) });
}

export async function getGate(projectId: string, changeId: string): Promise<GateDecision> {
  return engineFetch<GateDecision>(`/projects/${encodeURIComponent(projectId)}/changes/${encodeURIComponent(changeId)}/gate`);
}

export async function listRegressions(projectId: string): Promise<RegressionFinding[]> {
  const response = await engineFetch<{ regressions: RegressionFinding[] }>(`/projects/${encodeURIComponent(projectId)}/regressions`);
  return response.regressions;
}

export async function createRepairContext(projectId: string, regressionId: string): Promise<RepairContext> {
  return engineFetch<RepairContext>(`/projects/${encodeURIComponent(projectId)}/regressions/${encodeURIComponent(regressionId)}/repair-context`, { method: "POST", body: "{}" });
}

export async function copyRepairContext(projectId: string, contextId: string): Promise<string> {
  const response = await engineFetch<{ text: string }>(`/projects/${encodeURIComponent(projectId)}/repair-contexts/${encodeURIComponent(contextId)}/copy`, { method: "POST", body: "{}" });
  return response.text;
}

export async function saveRepairContext(projectId: string, contextId: string): Promise<string> {
  const response = await engineFetch<{ relative_path: string }>(`/projects/${encodeURIComponent(projectId)}/repair-contexts/${encodeURIComponent(contextId)}/save-local`, { method: "POST", body: "{}" });
  return response.relative_path;
}

export async function detectProjectRuntimes(projectId: string): Promise<RuntimeDetection> {
  return engineFetch<RuntimeDetection>(`/projects/${encodeURIComponent(projectId)}/runtime/detect`, {
    method: "POST",
    body: "{}",
  });
}

export async function listRuntimeProfiles(projectId: string): Promise<RuntimeProfile[]> {
  const response = await engineFetch<{ profiles?: RuntimeProfile[] }>(`/projects/${encodeURIComponent(projectId)}/runtime-profiles`);
  return Array.isArray(response.profiles) ? response.profiles : [];
}

export async function createRuntimeProfile(projectId: string, value: RuntimeProfileInput): Promise<RuntimeProfile> {
  return engineFetch<RuntimeProfile>(`/projects/${encodeURIComponent(projectId)}/runtime-profiles`, {
    method: "POST",
    body: JSON.stringify(value),
  });
}

export async function getRuntimeProfile(projectId: string, profileId: string): Promise<RuntimeProfile> {
  return engineFetch<RuntimeProfile>(`/projects/${encodeURIComponent(projectId)}/runtime-profiles/${encodeURIComponent(profileId)}`);
}

export async function validateRuntimeProfile(projectId: string, profileId: string): Promise<RuntimeProfile> {
  return engineFetch<RuntimeProfile>(`/projects/${encodeURIComponent(projectId)}/runtime-profiles/${encodeURIComponent(profileId)}/validate`, { method: "POST", body: "{}" });
}

export async function startRuntimeProfile(projectId: string, profileId: string): Promise<RuntimeInstance> {
  return engineFetch<RuntimeInstance>(`/projects/${encodeURIComponent(projectId)}/runtime-profiles/${encodeURIComponent(profileId)}/start`, { method: "POST", body: "{}" });
}

export async function stopRuntimeProfile(projectId: string, profileId: string): Promise<RuntimeInstance> {
  return engineFetch<RuntimeInstance>(`/projects/${encodeURIComponent(projectId)}/runtime-profiles/${encodeURIComponent(profileId)}/stop`, { method: "POST", body: "{}" });
}

export async function listRuntimeInstances(projectId: string): Promise<RuntimeInstance[]> {
  const response = await engineFetch<{ instances?: RuntimeInstance[] }>(`/projects/${encodeURIComponent(projectId)}/runtime-instances`);
  return Array.isArray(response.instances) ? response.instances : [];
}

export async function listSnapshots(projectId: string): Promise<SourceSnapshot[]> {
  const response = await engineFetch<{ snapshots?: SourceSnapshot[] }>(`/projects/${encodeURIComponent(projectId)}/snapshots`);
  return Array.isArray(response.snapshots) ? response.snapshots : [];
}

export async function createSnapshot(projectId: string, creationReason = "MANUAL_SAVE_POINT", episodeId: string | null = null): Promise<SourceSnapshot> {
  return engineFetch<SourceSnapshot>(`/projects/${encodeURIComponent(projectId)}/snapshots`, {
    method: "POST",
    body: JSON.stringify({ creation_reason: creationReason, episode_id: episodeId }),
  });
}

export async function getSnapshot(projectId: string, snapshotId: string): Promise<SourceSnapshot> {
  return engineFetch<SourceSnapshot>(`/projects/${encodeURIComponent(projectId)}/snapshots/${encodeURIComponent(snapshotId)}`);
}

export async function materializeSnapshot(projectId: string, snapshotId: string): Promise<SnapshotMaterialization> {
  return engineFetch<SnapshotMaterialization>(`/projects/${encodeURIComponent(projectId)}/snapshots/${encodeURIComponent(snapshotId)}/materialize`, { method: "POST", body: "{}" });
}

export async function setSnapshotPinned(projectId: string, snapshotId: string, pinned: boolean): Promise<SourceSnapshot> {
  return engineFetch<SourceSnapshot>(`/projects/${encodeURIComponent(projectId)}/snapshots/${encodeURIComponent(snapshotId)}/${pinned ? "pin" : "unpin"}`, { method: "POST", body: "{}" });
}

export async function listEpisodes(projectId: string): Promise<SourceEpisode[]> {
  const response = await engineFetch<{ episodes?: SourceEpisode[] }>(`/projects/${encodeURIComponent(projectId)}/episodes`);
  return Array.isArray(response.episodes) ? response.episodes : [];
}

export async function getEpisode(projectId: string, episodeId: string): Promise<SourceEpisode> {
  return engineFetch<SourceEpisode>(`/projects/${encodeURIComponent(projectId)}/episodes/${encodeURIComponent(episodeId)}`);
}

export async function listMilestones(projectId: string): Promise<SnapshotMilestone[]> {
  const response = await engineFetch<{ milestones?: SnapshotMilestone[] }>(`/projects/${encodeURIComponent(projectId)}/milestones`);
  return Array.isArray(response.milestones) ? response.milestones : [];
}

export async function createKnownGoodMilestone(projectId: string, value: {
  snapshot_id: string;
  display_name: string;
  behavior_id?: string | null;
  behavior_version_id?: string | null;
  probe_version_id?: string | null;
  human_attested?: boolean;
}): Promise<SnapshotMilestone> {
  return engineFetch<SnapshotMilestone>(`/projects/${encodeURIComponent(projectId)}/milestones/known-good`, { method: "POST", body: JSON.stringify(value) });
}

export async function listProbes(projectId: string): Promise<ProbeDefinition[]> {
  const response = await engineFetch<{ probes?: ProbeDefinition[] }>(`/projects/${encodeURIComponent(projectId)}/probes`);
  return Array.isArray(response.probes) ? response.probes : [];
}

export async function createProbe(projectId: string, value: ProbeInput): Promise<ProbeDefinition> {
  return engineFetch<ProbeDefinition>(`/projects/${encodeURIComponent(projectId)}/probes`, { method: "POST", body: JSON.stringify(value) });
}

export async function getProbe(projectId: string, probeId: string): Promise<ProbeDefinition> {
  return engineFetch<ProbeDefinition>(`/projects/${encodeURIComponent(projectId)}/probes/${encodeURIComponent(probeId)}`);
}

export async function runProbe(projectId: string, probeId: string, snapshotId: string | null = null): Promise<ProbeRun> {
  return engineFetch<ProbeRun>(`/projects/${encodeURIComponent(projectId)}/probes/${encodeURIComponent(probeId)}/run`, { method: "POST", body: JSON.stringify({ snapshot_id: snapshotId }) });
}

export async function cancelProbe(projectId: string, probeId: string): Promise<{ status: string }> {
  return engineFetch<{ status: string }>(`/projects/${encodeURIComponent(projectId)}/probes/${encodeURIComponent(probeId)}/cancel`, { method: "POST", body: "{}" });
}

export async function createRepairWorkspace(projectId: string, regressionId: string): Promise<RepairWorkspace> {
  return engineFetch<RepairWorkspace>(`/projects/${encodeURIComponent(projectId)}/regressions/${encodeURIComponent(regressionId)}/repair-workspace`, { method: "POST", body: "{}" });
}

export async function getRepairWorkspace(projectId: string, workspaceId: string): Promise<RepairWorkspace> {
  return engineFetch<RepairWorkspace>(`/projects/${encodeURIComponent(projectId)}/repair-workspaces/${encodeURIComponent(workspaceId)}`);
}

export async function openRepairWorkspace(projectId: string, workspaceId: string, target = "FOLDER"): Promise<{ status: string }> {
  return engineFetch<{ status: string }>(`/projects/${encodeURIComponent(projectId)}/repair-workspaces/${encodeURIComponent(workspaceId)}/open`, { method: "POST", body: JSON.stringify({ target }) });
}

export async function deleteRepairWorkspace(projectId: string, workspaceId: string): Promise<void> {
  await engineFetch(`/projects/${encodeURIComponent(projectId)}/repair-workspaces/${encodeURIComponent(workspaceId)}`, { method: "DELETE" });
}

export async function createRepairCandidate(projectId: string, workspaceId: string): Promise<RepairCandidate> {
  return engineFetch<RepairCandidate>(`/projects/${encodeURIComponent(projectId)}/repair-workspaces/${encodeURIComponent(workspaceId)}/candidates`, { method: "POST", body: "{}" });
}

export async function refreshRepairCandidate(projectId: string, candidateId: string): Promise<RepairCandidate> {
  return engineFetch<RepairCandidate>(`/projects/${encodeURIComponent(projectId)}/repair-candidates/${encodeURIComponent(candidateId)}/refresh`, { method: "POST", body: "{}" });
}

export async function excludeRepairCandidateFiles(projectId: string, candidateId: string, paths: string[]): Promise<RepairCandidate> {
  return engineFetch<RepairCandidate>(`/projects/${encodeURIComponent(projectId)}/repair-candidates/${encodeURIComponent(candidateId)}/exclude`, { method: "POST", body: JSON.stringify({ paths }) });
}

export async function restoreRepairWorkspaceFile(projectId: string, candidateId: string, relativePath: string): Promise<RepairCandidate> {
  return engineFetch<RepairCandidate>(`/projects/${encodeURIComponent(projectId)}/repair-candidates/${encodeURIComponent(candidateId)}/restore-workspace-file`, { method: "POST", body: JSON.stringify({ relative_path: relativePath }) });
}

export async function getRepairCandidateDiff(projectId: string, candidateId: string, relativePath: string): Promise<{ candidate_id: string; relative_path: string; available: boolean; reason: string | null; lines: string[]; truncated: boolean }> {
  return engineFetch(`/projects/${encodeURIComponent(projectId)}/repair-candidates/${encodeURIComponent(candidateId)}/diff?relative_path=${encodeURIComponent(relativePath)}`);
}

export async function validateRepairCandidate(projectId: string, candidateId: string): Promise<CandidateValidation> {
  return engineFetch<CandidateValidation>(`/projects/${encodeURIComponent(projectId)}/repair-candidates/${encodeURIComponent(candidateId)}/validate`, { method: "POST", body: "{}" });
}

export async function prepareRepairApply(projectId: string, candidateId: string): Promise<ApplyTransaction> {
  return engineFetch<ApplyTransaction>(`/projects/${encodeURIComponent(projectId)}/repair-candidates/${encodeURIComponent(candidateId)}/apply/prepare`, { method: "POST", body: "{}" });
}

export async function confirmRepairApply(projectId: string, candidateId: string, confirmationNonce: string): Promise<ApplyTransaction> {
  return engineFetch<ApplyTransaction>(`/projects/${encodeURIComponent(projectId)}/repair-candidates/${encodeURIComponent(candidateId)}/apply/confirm`, { method: "POST", body: JSON.stringify({ confirmation_nonce: confirmationNonce, deliberate_confirmation: true }) });
}

export async function rollbackRepairApply(projectId: string, transactionId: string): Promise<ApplyTransaction> {
  return engineFetch<ApplyTransaction>(`/projects/${encodeURIComponent(projectId)}/apply-transactions/${encodeURIComponent(transactionId)}/rollback`, { method: "POST", body: "{}" });
}

export async function exportPortableRepair(projectId: string, workspaceId: string, selectedPaths: string[]): Promise<{ id: string; workspace_id: string; relative_path: string; file_count: number; logical_bytes: number; uploaded: boolean }> {
  return engineFetch(`/projects/${encodeURIComponent(projectId)}/repair-workspaces/${encodeURIComponent(workspaceId)}/export-portable`, { method: "POST", body: JSON.stringify({ selected_paths: selectedPaths }) });
}

export async function createDemoLab(selectedParent: string): Promise<DemoLabRun> {
  return engineFetch<DemoLabRun>("/demo-lab/create", { method: "POST", body: JSON.stringify({ selected_parent: selectedParent }) });
}

export async function runDemoAction(demoId: string, action: "inject-regression" | "create-bad-candidate" | "create-valid-candidate" | "apply-valid" | "simulate-post-apply-failure" | "reset"): Promise<DemoLabRun> {
  return engineFetch<DemoLabRun>(`/demo-lab/${encodeURIComponent(demoId)}/${action}`, { method: "POST", body: "{}" });
}

export async function runProductSelfTest(): Promise<ProductSelfTestRun> {
  return engineFetch<ProductSelfTestRun>("/self-test", { method: "POST", body: "{}" });
}

export async function exportProductSelfTest(runId: string): Promise<{ run_id: string; relative_path: string | null; private_paths_included: boolean; exported: boolean }> {
  return engineFetch(`/self-test/${encodeURIComponent(runId)}/export`, { method: "POST", body: "{}" });
}

export function resetBootstrapForTests(): void {
  bootstrapPromise = undefined;
}
