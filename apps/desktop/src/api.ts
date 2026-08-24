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
}

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
  return (await response.json()) as T;
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
): Promise<Project> {
  return engineFetch<Project>("/projects", {
    method: "POST",
    body: JSON.stringify({ path, display_name: displayName, monitoring_mode: monitoringMode }),
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

export async function createProtectionPlan(projectId: string, changeId: string): Promise<ProtectionPlan> {
  return engineFetch<ProtectionPlan>(`/projects/${encodeURIComponent(projectId)}/changes/${encodeURIComponent(changeId)}/protection-plan`, { method: "POST", body: "{}" });
}

export async function getProtectionPlan(projectId: string, changeId: string): Promise<ProtectionPlan> {
  return engineFetch<ProtectionPlan>(`/projects/${encodeURIComponent(projectId)}/changes/${encodeURIComponent(changeId)}/protection-plan`);
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

export function resetBootstrapForTests(): void {
  bootstrapPromise = undefined;
}
