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

export function resetBootstrapForTests(): void {
  bootstrapPromise = undefined;
}
