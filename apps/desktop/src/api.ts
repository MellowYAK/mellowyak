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

let bootstrapPromise: Promise<EngineBootstrap> | undefined;

function bootstrap(): Promise<EngineBootstrap> {
  bootstrapPromise ??= invoke<EngineBootstrap>("engine_bootstrap");
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
