import { cleanup, configure, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { App } from "./App";
import { resetBootstrapForTests, type Project } from "./api";
import { phase10CaptureStates } from "./Phase10Experience";
import { phase12CaptureStates } from "./Phase12Experience";
import { ProjectsScreen } from "./ProductScreens";

const dialogOpen = vi.fn();
const tauriInvoke = vi.hoisted(() => vi.fn());
const updaterCheck = vi.hoisted(() => vi.fn());
const relaunch = vi.hoisted(() => vi.fn());

vi.mock("@tauri-apps/api/core", () => ({ invoke: (...args: unknown[]) => tauriInvoke(...args) }));
vi.mock("@tauri-apps/plugin-dialog", () => ({ open: (...args: unknown[]) => dialogOpen(...args) }));
vi.mock("@tauri-apps/plugin-updater", () => ({ check: (...args: unknown[]) => updaterCheck(...args) }));
vi.mock("@tauri-apps/plugin-process", () => ({ relaunch: (...args: unknown[]) => relaunch(...args) }));

configure({ asyncUtilTimeout: 3_000 });

const responses: Record<string, unknown> = {
  "/health": { status: "ready", mode: "local", engine_version: "0.1.0", app_version: "0.1.0", database_status: "ready", database_schema_version: "0005_verification_regression_gate", data_root: "/local/MellowYak", cloud_connected: false, outbound_network_enabled: false, uptime_seconds: 1 },
  "/readiness": { ready: true, checks: { local_only: true, database_ready: true } },
  "/installation": { installation_id: "install-1", created_at: "2026-08-23T00:00:00Z", last_started_at: "2026-08-23T00:00:00Z", app_version: "0.1.0", engine_version: "0.1.0", database_schema_version: "0005_verification_regression_gate" },
  "/settings/privacy": { mode: "local", cloud_connected: false, outbound_network_enabled: false, source_upload_enabled: false, telemetry_upload_enabled: false, account_required: false },
  "/storage/paths": { data_root: "/local/MellowYak", database: "/local/MellowYak/database", evidence: "/local/MellowYak/evidence", projects: "/local/MellowYak/projects", cache: "/local/MellowYak/cache", logs: "/local/MellowYak/logs", runtime: "/local/MellowYak/runtime", backups: "/local/MellowYak/backups" },
  "/projects": { projects: [] },
  "/app/onboarding": { completed: true, current_step: "complete", replay_active: false, selected_path: "existing_installation", completed_at: "2026-08-25T00:00:00Z", requires_first_run: false, source_modified: false },
  "/tray/state": { state: "MONITORING", unread_alert_count: 0, critical_alert_count: 0, active_project_count: 0, paused_project_count: 0, projects: [], recent_alerts: [], private_paths_exposed: false, source_content_exposed: false },
  "/projects/detect": {
    selected_path: "/work/demo", repository_path: "/work/demo", suggested_name: "demo",
    git: { available: true, branch: "main", head_sha: "1234567890abcdef", is_detached: false, is_dirty: true, staged: ["src/a.ts"], unstaged: [], untracked: ["notes.txt"], ignored_count: 2, worktree_fingerprint: "fp", error: null },
    languages: ["TypeScript"], language_counts: { TypeScript: 4 }, frameworks: ["React"], tests: ["Vitest"], runtime_hints: ["Node.js application hint"], candidate_files: 8, ignored_paths: 2, relationship_coverage: "bounded deterministic adapters", unsupported_coverage: "reported during initial scan", source_remains_local: true
  },
  "/workflow/state-model": {
    behavior: { KNOWN_GOOD: ["CAPTURING", "NEEDS_REVIEW", "DISABLED"] },
    regression: { CONFIRMED: ["REVIEWED", "DISMISSED", "RESOLVED"] },
    apply: {
      AWAITING_CONFIRMATION: ["BLOCKED", "CANCELLED", "PREFLIGHT"],
      COMMITTED: [],
      ROLLED_BACK: [],
    },
    updater: {
      NOT_CHECKED: ["CHECKING", "PRODUCTION_CHANNEL_UNPUBLISHED"],
      INVALID_SIGNATURE: ["CHECKING"],
      UPDATED: [],
      PRODUCTION_CHANNEL_UNPUBLISHED: ["CHECKING"],
    },
  },
};

const git = { available: true, branch: "main", head_sha: "1234567890abcdef", is_detached: false, is_dirty: true, staged: ["src/a.ts"], unstaged: [], untracked: [], ignored_count: 2, worktree_fingerprint: "fp", error: null };
const scan = { id: "scan-1", status: "completed", scan_version: "1", started_at: "2026-08-24T00:00:00Z", completed_at: "2026-08-24T00:00:01Z", total_candidates: 2, processed_files: 2, included_files: 2, excluded_files: 0, binary_files: 0, sensitive_files: 0, failed_files: 0, unknown_items: 0, unsupported_files: 0, test_files: 1, relationship_count: 1, duration_seconds: 1, error_summary: null };
const project = { id: "project-1", display_name: "demo", display_path: "/work/demo", repository_path: "/work/demo", monitoring_mode: "passive", monitoring_status: "active", last_scan_status: "completed", last_scan_at: "2026-08-24T00:00:01Z", created_at: "2026-08-24T00:00:00Z", updated_at: null, languages: ["TypeScript"], frameworks: ["React"], tests: ["Vitest"], runtime_hints: [], git, scan, source_remains_local: true };
function responseFor(path: string): unknown {
  const listed = (responses["/projects"] as { projects?: Array<typeof project> } | undefined)?.projects ?? [];
  const projects = listed.map((item) => ({
    id: item.id,
    display_name: item.display_name,
    state: "READY_WITH_LIMITS",
    monitoring_state: item.monitoring_status,
    source_available: true,
    runtime_state: "INCOMPLETE",
    last_episode: null,
    last_save_point: null,
    protected_behavior_count: 0,
    latest_check: null,
    open_regression_count: 0,
    recovery_required_count: 0,
    last_activity_at: item.last_scan_at ?? item.created_at,
    limitations: ["NO_PROTECTED_BEHAVIORS", "RUNTIME_NOT_CONFIGURED", "NO_CHECK_RESULT"],
  }));
  if (path.endsWith("/overview")) {
    const projectId = path.split("/")[2];
    const projectSummary = projects.find((item) => item.id === projectId);
    if (!projectSummary) return responses[path];
    return {
      project: projectSummary,
      source_identity: { branch: "main", head_sha: "1234567890abcdef", worktree_fingerprint: "fp" },
      last_known_good: null,
      latest_checks: [],
      recent_activity: [],
      storage: { integrity_state: "READY", snapshot_count: 0, logical_bytes: 0 },
      known: ["PROJECT_REGISTERED", "SOURCE_AVAILABLE"],
      unknowns: ["NO_PROTECTED_BEHAVIORS", "RUNTIME_NOT_CONFIGURED", "NO_CHECK_RESULT"],
    };
  }
  if (path !== "/home/summary") return responses[path];
  return {
    state: projects.length ? "NO_CONFIRMED_ISSUE_FOUND" : "NO_PROJECTS",
    counts: {
      monitored: projects.length,
      paused: 0,
      disconnected: 0,
      needs_setup: projects.length,
      confirmed_regressions: 0,
      needs_review: 0,
      blocked_or_recovery: 0,
      unread_alerts: 0,
    },
    projects,
    attention: [],
    recent_activity: [],
    known: ["LOCAL_DATABASE", "REGISTERED_PROJECTS"],
    unknowns: ["INCOMPLETE_COVERAGE"],
  };
}
const change = { id: "change-1", project_id: "project-1", change_kind: "uncommitted_worktree", revision: 1, base_head_sha: git.head_sha, head_sha: git.head_sha, worktree_fingerprint: "fp", changed_paths: ["src/a.ts"], task_intent: null, status: "change_detected", created_at: "2026-08-24T00:00:00Z", updated_at: "2026-08-24T00:00:00Z" };
const analysis = { id: "analysis-1", project_id: "project-1", change_id: "change-1", analysis_revision: 1, base_head_sha: git.head_sha, head_sha: git.head_sha, worktree_fingerprint: "fp", scan_revision: "scan-1", algorithm_version: "reverse-impact-v1", status: "completed", changed_file_count: 1, impacted_node_count: 2, unknown_count: 1, stale_count: 0, heuristic_count: 0, truncated: false, truncation_reasons: [], duration_ms: 2, stale: false, stale_reasons: [], created_at: "2026-08-24T00:00:00Z" };
const impact = { analysis, results: [
  { id: "result-1", node_id: "node-1", node_type: "FILE", display_name: "src/a.ts", relative_path: "src/a.ts", impact_class: "changed", minimum_depth: 0, strongest_provenance: "EXACT_PARSER", stale: false, unknown: false, explanation: "Changed file.", path_count: 1, ranking_score: 100, ranking_reasons: ["changed"], unknown_reason: null },
  { id: "result-2", node_id: null, node_type: "UNKNOWN", display_name: "missing-module", relative_path: null, impact_class: "unknown_boundary", minimum_depth: 1, strongest_provenance: "UNKNOWN", stale: false, unknown: true, explanation: "Resolution stopped at an unknown boundary.", path_count: 1, ranking_score: 1, ranking_reasons: ["unknown"], unknown_reason: "unresolved import" },
] };
const receipt = { schema: "mellowyak.context_receipt.v1", id: "receipt-1", project: { id: "project-1", name: "demo" }, change_id: "change-1", analysis_id: "analysis-1", request: "update parser", source_revision: {}, selected_files: [{ relative_path: "src/a.ts", type: "FILE", reason_selected: "Changed file.", relationship_provenance: "EXACT_PARSER", relevance_class: "changed", stale: false, size: 10, content_eligible: true, selection_reasons: ["changed"] }], selected_symbols: [], related_tests: [], relationship_paths: [], constraints: { source_content_included: false }, unknowns: [{ path: "missing-module", reason: "unresolved import" }], excluded_context: [], selection_reasons: ["changed"], size_metrics: { selected_files: 1, selected_source_bytes: 0 }, truncated: false, stale: false, source_uploaded: false, created_at: "2026-08-24T00:00:00Z" };

beforeEach(() => {
  window.history.replaceState({}, "", "/");
  document.documentElement.lang = "en";
  document.documentElement.dir = "ltr";
  Reflect.deleteProperty(window, "__TAURI_INTERNALS__");
  resetBootstrapForTests(); dialogOpen.mockReset(); dialogOpen.mockResolvedValue("/work/demo"); updaterCheck.mockReset(); relaunch.mockReset();
  tauriInvoke.mockReset();
  tauriInvoke.mockResolvedValue({ host: "127.0.0.1", port: 43123, token: "memory-only" });
  responses["/projects"] = { projects: [] };
  responses["/readiness"] = { ready: true, checks: { local_only: true, database_ready: true } };
  responses["/app/onboarding"] = { completed: true, current_step: "complete", replay_active: false, selected_path: "existing_installation", completed_at: "2026-08-25T00:00:00Z", requires_first_run: false, source_modified: false };
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const path = new URL(String(input)).pathname;
    return new Response(JSON.stringify(responseFor(path)), { status: 200, headers: { "Content-Type": "application/json" } });
  }));
});

test("waits for an asynchronously starting packaged engine without crashing", async () => {
  tauriInvoke.mockRejectedValueOnce("ENGINE_STARTING");
  render(<App />);
  expect(screen.getByText("Preparing your local engine")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByRole("heading", { name: "What is happening now?" })).toBeInTheDocument());
  expect(tauriInvoke.mock.calls.length).toBeGreaterThanOrEqual(2);
});

test("keeps the translated alert poll stable between scheduled refreshes", async () => {
  render(<App />);
  await waitFor(() => expect(screen.getByRole("heading", { name: "What is happening now?" })).toBeInTheDocument());
  await new Promise((resolve) => window.setTimeout(resolve, 100));
  const fetchMock = vi.mocked(fetch);
  const alertCalls = () => fetchMock.mock.calls.filter(([input]) => new URL(String(input)).pathname === "/alerts").length;
  const initialCalls = alertCalls();
  await new Promise((resolve) => window.setTimeout(resolve, 300));
  expect(alertCalls()).toBe(initialCalls);
});

test("renders deterministic Phase 9 diagnostics and Hebrew RTL capture states", async () => {
  window.history.replaceState({}, "", "/?phase9State=diagnostics");
  render(<App />);
  expect(screen.getByRole("heading", { name: "Diagnostics Center" })).toBeInTheDocument();
  cleanup();
  window.history.replaceState({}, "", "/?phase9State=hebrew-diagnostics");
  render(<App />);
  await waitFor(() => expect(document.documentElement.dir).toBe("rtl"));
  expect(screen.getByRole("heading", { name: "מרכז האבחון בעברית ובכיוון מימין לשמאל" })).toBeInTheDocument();
});

test("registers every required Phase 10 delivery state exactly once", () => {
  expect(phase10CaptureStates).toHaveLength(36);
  expect(new Set(phase10CaptureStates).size).toBe(36);
  expect(phase10CaptureStates).toContain("home-no-confirmed-issue");
  expect(phase10CaptureStates).toContain("native-tray-preview");
  expect(phase10CaptureStates).toContain("hebrew-diagnostics");
});

test("renders the Phase 10 operational Home without unresolved translation parameters", () => {
  window.history.replaceState({}, "", "/?phase10State=home-no-confirmed-issue");
  render(<App />);
  expect(screen.getByRole("heading", { name: "What is happening now?" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /MellowYak Demo/ })).toBeInTheDocument();
  expect(document.body.textContent).not.toMatch(/\{(?:behaviors|regressions|passed|failed|inconclusive)\}/);
});

test("renders the Phase 10 Hebrew Home as an RTL operational surface", async () => {
  window.history.replaceState({}, "", "/?phase10State=hebrew-home");
  render(<App />);
  await waitFor(() => expect(document.documentElement).toHaveAttribute("dir", "rtl"));
  expect(screen.getByRole("heading", { name: "מה קורה עכשיו?" })).toBeInTheDocument();
  expect(document.querySelector("main")).toHaveAttribute("dir", "rtl");
});

test("registers the exact Phase 12M delivery states behind the explicit fixture marker", () => {
  expect(phase12CaptureStates).toHaveLength(38);
  expect(new Set(phase12CaptureStates).size).toBe(38);
  expect(phase12CaptureStates[0]).toBe("00-reference-project-created");
  expect(phase12CaptureStates.at(-1)).toBe("37-hebrew-diagnostics");
});

test("traps modal focus, closes with Escape, and restores the project action trigger", async () => {
  const translations: Record<string, string> = {
    "projects.actions": "Project actions",
    "projects.action.disconnect": "Disconnect",
    "projects.disconnectTitle": "Disconnect project",
    "projects.disconnectBody": "Disconnect body",
    "projects.sourceSafe": "Source stays safe",
    "projects.disconnectConfirm": "Confirm disconnect",
    "common.cancel": "Cancel",
  };
  const t = (key: string) => translations[key] ?? key;
  render(<ProjectsScreen
    projects={[{ ...project, source_available: true, notifications_muted: false } as unknown as Project]}
    t={t}
    openProject={vi.fn()}
    reload={async () => undefined}
    add={vi.fn()}
  />);
  const trigger = screen.getByRole("button", { name: "Project actions" });
  fireEvent.click(trigger);
  fireEvent.click(screen.getByRole("button", { name: "Disconnect" }));
  expect(await screen.findByRole("dialog", { name: "Disconnect project" })).toBeInTheDocument();
  const cancel = screen.getByRole("button", { name: "Cancel" });
  const confirm = screen.getByRole("button", { name: "Confirm disconnect" });
  await waitFor(() => expect(cancel).toHaveFocus());
  fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
  expect(confirm).toHaveFocus();
  fireEvent.keyDown(document, { key: "Tab" });
  expect(cancel).toHaveFocus();
  fireEvent.keyDown(document, { key: "Escape" });
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(trigger).toHaveFocus();
});

test("shows a real accepted PASS without a contradictory prior Unknown result", async () => {
  window.history.replaceState({}, "", "/?phase12Fixture=mellowyak.phase12.screenshots.v1&phase12State=06-known-good-accepted-pass");
  render(<App />);
  expect(await screen.findByRole("heading", { name: "Known Good accepted with PASS" })).toBeInTheDocument();
  expect(screen.getAllByText("PASS").length).toBeGreaterThan(0);
  expect(document.body).not.toHaveTextContent("Prior result: Unknown");
});

test("keeps Apply incomplete before confirmation and removes confirmation after commit", async () => {
  window.history.replaceState({}, "", "/?phase12Fixture=mellowyak.phase12.screenshots.v1&phase12State=16-apply-awaiting-confirmation");
  render(<App />);
  expect(await screen.findByRole("heading", { name: "Apply awaits explicit confirmation" })).toBeInTheDocument();
  expect(screen.getAllByText("Not started").length).toBeGreaterThanOrEqual(3);
  expect(screen.getAllByText("Not created yet")).toHaveLength(2);
  cleanup();
  window.history.replaceState({}, "", "/?phase12Fixture=mellowyak.phase12.screenshots.v1&phase12State=20-applied-and-verified");
  render(<App />);
  expect(await screen.findByRole("heading", { name: "Applied and verified" })).toBeInTheDocument();
  expect(screen.queryByText("Continue with explicit confirmation")).not.toBeInTheDocument();
});

test("renders transaction rollback evidence and distinct updater truth", async () => {
  window.history.replaceState({}, "", "/?phase12Fixture=mellowyak.phase12.screenshots.v1&phase12State=23-rolled-back-byte-identical");
  render(<App />);
  expect(await screen.findByRole("heading", { name: "Rolled back byte-identically" })).toBeInTheDocument();
  expect(screen.getByText("api/selection_mode.txt")).toBeInTheDocument();
  expect(screen.getByText("VERIFIED")).toBeInTheDocument();
  expect(screen.getByText("UNCHANGED")).toBeInTheDocument();
  cleanup();
  window.history.replaceState({}, "", "/?phase12Fixture=mellowyak.phase12.screenshots.v1&phase12State=30-updater-invalid-signature");
  render(<App />);
  expect(await screen.findByRole("heading", { name: "Update signature rejected" })).toBeInTheDocument();
  expect(screen.getAllByText("Invalid signature").length).toBeGreaterThan(0);
});

test("renders the Phase 12M diagnostics surface in Hebrew RTL", async () => {
  window.history.replaceState({}, "", "/?phase12Fixture=mellowyak.phase12.screenshots.v1&phase12State=37-hebrew-diagnostics");
  render(<App />);
  expect(await screen.findByRole("heading", { name: "אבחון אמיתי בעברית" })).toBeInTheDocument();
  await waitFor(() => expect(document.documentElement).toHaveAttribute("dir", "rtl"));
  expect(document.querySelector("main")).toHaveAttribute("dir", "rtl");
});

test("shows persisted first run and completes the synthetic Demo Lab choice", async () => {
  const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
  const onboarding = {
    completed: false,
    current_step: "welcome",
    replay_active: false,
    selected_path: null,
    completed_at: null,
    requires_first_run: true,
    source_modified: false,
  };
  responses["/app/onboarding"] = onboarding;
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = new URL(String(input)).pathname;
    if (path === "/app/onboarding" && init?.method === "PUT") {
      const request = JSON.parse(String(init.body)) as { current_step: string; selected_path: string | null; completed: boolean };
      Object.assign(onboarding, {
        current_step: request.current_step,
        selected_path: request.selected_path,
        completed: request.completed,
        requires_first_run: !request.completed,
      });
      return new Response(JSON.stringify(onboarding), { status: 200 });
    }
    return new Response(JSON.stringify(responseFor(path)), { status: 200, headers: { "Content-Type": "application/json" } });
  }));
  render(<App />);
  expect(await screen.findByRole("heading", { name: "Welcome to MellowYak" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Continue" }));
  fireEvent.click(await screen.findByRole("radio", { name: /Try the synthetic Demo Lab/ }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Continue" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Continue" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Continue" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Continue" }));
  fireEvent.click(await screen.findByRole("button", { name: "Open Demo Lab" }));
  expect(await screen.findByRole("heading", { name: "Try MellowYak with a Demo Project" })).toBeInTheDocument();
  expect(consoleError).not.toHaveBeenCalledWith(expect.stringContaining("controlled input"));
  consoleError.mockRestore();
});

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

test("renders real engine values and local privacy status", async () => {
  render(<App />);
  expect(screen.getByText("Preparing your local engine")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByRole("heading", { name: "What is happening now?" })).toBeInTheDocument());
  expect(screen.getByRole("heading", { name: "No projects connected" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Connected projects" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Recent activity" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Add your first project" })).toBeInTheDocument();
});

test("does not report ready or render projects before real project discovery completes", async () => {
  let releaseProjects: (() => void) | undefined;
  const projectGate = new Promise<void>((resolve) => { releaseProjects = resolve; });
  responses["/projects"] = { projects: [project] };
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const path = new URL(String(input)).pathname;
    if (path === "/projects") await projectGate;
    return new Response(JSON.stringify(responseFor(path)), { status: 200, headers: { "Content-Type": "application/json" } });
  }));
  render(<App />);
  expect(await screen.findByText("Discovering local projects…")).toBeInTheDocument();
  expect(screen.queryByText("Your local engine is ready.")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /demo/i })).not.toBeInTheDocument();
  releaseProjects?.();
  expect(await screen.findByText("Your local engine is ready.")).toBeInTheDocument();
  expect(await screen.findByRole("button", { name: /demo/i })).toBeInTheDocument();
});

test("marks a failed real startup step and retries without a false ready state", async () => {
  responses["/readiness"] = { ready: false, checks: { local_only: true, database_ready: true } };
  render(<App />);
  expect(await screen.findByText("Local startup needs attention")).toBeInTheDocument();
  expect(screen.queryByText("Your local engine is ready.")).not.toBeInTheDocument();
  expect(screen.getByText("Loading verified capabilities").closest("li")).toHaveClass("failed");
  responses["/readiness"] = { ready: true, checks: { local_only: true, database_ready: true } };
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(await screen.findByRole("heading", { name: "What is happening now?" })).toBeInTheDocument();
});

test("uses a static second loading frame when reduced motion is requested", async () => {
  vi.stubGlobal("matchMedia", vi.fn(() => ({
    matches: true,
    media: "(prefers-reduced-motion: reduce)",
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })));
  render(<App />);
  await waitFor(() => expect(document.querySelector(".startup-animation img")?.getAttribute("src")).toContain("mellowyak-loading-02"));
});

test("offers and installs a signed desktop update without hardcoded UI copy", async () => {
  const downloadAndInstall = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(window, "__TAURI_INTERNALS__", { configurable: true, value: {} });
  updaterCheck.mockResolvedValue({ version: "0.2.0", downloadAndInstall });
  relaunch.mockResolvedValue(undefined);
  render(<App />);
  expect(await screen.findByText("MellowYak update available")).toBeInTheDocument();
  expect(screen.getByText("Version 0.2.0 is ready from the signed GitHub Release.")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Install and restart" }));
  await waitFor(() => expect(downloadAndInstall).toHaveBeenCalledTimes(1));
  await waitFor(() => expect(relaunch).toHaveBeenCalledTimes(1));
});

test("switches every product surface to Hebrew RTL from translation keys", async () => {
  render(<App />);
  await screen.findByRole("heading", { name: "What is happening now?" });
  fireEvent.change(screen.getByLabelText("Language"), { target: { value: "he" } });
  expect(await screen.findByRole("heading", { name: "מה קורה עכשיו?" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "אין פרויקטים מחוברים" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "הוספת הפרויקט הראשון" })).toBeInTheDocument();
  expect(document.documentElement).toHaveAttribute("lang", "he");
  expect(document.documentElement).toHaveAttribute("dir", "rtl");
  expect(document.querySelector("main")).toHaveAttribute("dir", "rtl");
});

test("shows explainable change impact, context receipt, and behavior candidate controls", async () => {
  responses["/projects"] = { projects: [project] };
  responses["/projects/project-1"] = project;
  responses["/projects/project-1/impact/summary"] = { files_indexed: 2, languages: 1, language_counts: { TypeScript: 2 }, direct_relationships: 1, tests_found: 1, sensitive_files: 0, unknown_references: 1, unsupported_files: 0, stale_relationships: 0 };
  responses["/projects/project-1/changes/current"] = change;
  responses["/projects/project-1/behavior-candidates"] = { candidates: [{ id: "candidate-1", title: "Keeps parser stable", source_type: "test_name", source_key: "parser.test.ts", status: "CANDIDATE", evidence: "none", verification: "not_configured", not_protected: true }] };
  responses["/projects/project-1/behaviors"] = { behaviors: [] };
  responses["/projects/project-1/changes/change-1/impact"] = impact;
  responses["/projects/project-1/changes/change-1/impact/paths"] = { paths: [{ id: "path-1", result_id: "result-1", result: "src/a.ts", impact_class: "changed", depth: 0, steps: [] }] };
  responses["/projects/project-1/changes/change-1/intent"] = { ...change, task_intent: "update parser" };
  responses["/projects/project-1/changes/change-1/analyze"] = impact;
  responses["/projects/project-1/changes/change-1/context-receipt"] = receipt;
  responses["/projects/project-1/behavior-candidates/candidate-1/prepare"] = { id: "candidate-1", status: "PROMOTED_STUB", verification: "not_configured", not_protected: true };
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.assign(navigator, { clipboard: { writeText } });

  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /demo/i }));
  fireEvent.click(await screen.findByRole("button", { name: "Repairs" }));
  expect(await screen.findByText("Changed Files")).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "Change Cockpit" })).toBeInTheDocument();
  expect(screen.getByText("Protection Plan")).toBeInTheDocument();
  expect(screen.getByText("Verification Runner")).toBeInTheDocument();
  expect(screen.getByText("Repair Context")).toBeInTheDocument();
  expect(screen.getByText("Gate Decision")).toBeInTheDocument();
  expect(screen.getByText("Unknown / Stale Boundaries")).toBeInTheDocument();
  expect(screen.getByText("unresolved import")).toBeInTheDocument();
  expect(screen.getByText("Impact Paths")).toBeInTheDocument();
  expect(screen.getByText("Behavior Candidates")).toBeInTheDocument();
  expect(screen.getByText(/Not protected · Verification not configured/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("What are you changing?"), { target: { value: "update parser" } });
  fireEvent.click(screen.getByRole("button", { name: "Analyze impact" }));
  await screen.findByText("IMPACT ANALYZED");
  fireEvent.click(screen.getByRole("button", { name: "Generate receipt" }));
  expect(await screen.findByText("mellowyak.context_receipt.v1")).toBeInTheDocument();
  expect(screen.getByText("Source bytes").nextSibling).toHaveTextContent("0");
  fireEvent.click(screen.getByRole("button", { name: "Copy JSON" }));
  await waitFor(() => expect(writeText).toHaveBeenCalledWith(expect.stringContaining('"source_uploaded": false')));
  fireEvent.click(screen.getByRole("button", { name: "Prepare" }));
  await waitFor(() => expect(screen.getByText(/PROMOTED STUB/)).toBeInTheDocument());
});

test("impact explorer reports incoming and outgoing provenance", async () => {
  responses["/projects"] = { projects: [project] };
  responses["/projects/project-1"] = project;
  responses["/projects/project-1/impact/summary"] = { files_indexed: 2, languages: 1, language_counts: {}, direct_relationships: 2, tests_found: 0, sensitive_files: 0, unknown_references: 0, unsupported_files: 0, stale_relationships: 0 };
  responses["/projects/project-1/impact/search"] = { results: [{ node: { type: "FILE", label: "src/a.ts", relative_path: "src/a.ts" }, relationships: [
    { direction: "incoming", type: "IMPORTS", target_type: "FILE", target: "src/b.ts", target_path: "src/b.ts", provenance: "EXACT_PARSER", parser_adapter: "typescript", source_scan_revision: "scan-1", stale: false },
    { direction: "outgoing", type: "CONTAINS", target_type: "SYMBOL", target: "parse", target_path: "src/a.ts", provenance: "EXACT_PARSER", parser_adapter: "typescript", source_scan_revision: "scan-1", stale: false },
  ], recent_changes: ["change-1"] }] };
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /demo/i }));
  fireEvent.click(await screen.findByRole("button", { name: "Impact" }));
  fireEvent.change(screen.getByLabelText("Find a file, symbol, test, or module"), { target: { value: "a.ts" } });
  fireEvent.click(screen.getByRole("button", { name: "Search" }));
  expect(await screen.findByText("incoming")).toBeInTheDocument();
  expect(screen.getByText("outgoing")).toBeInTheDocument();
  expect(screen.getAllByText(/EXACT_PARSER/)).toHaveLength(2);
});

test("starts the Runtime Wizard with the native folder picker and local project identity", async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Add your first project" }));
  expect(screen.getByText("Project Runtime Wizard")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Choose local source folder" }));
  await waitFor(() => expect(dialogOpen).toHaveBeenCalledWith(expect.objectContaining({ directory: true, multiple: false })));
  expect(await screen.findByText("Canonical root")).toBeInTheDocument();
  expect(screen.getByDisplayValue("demo")).toBeInTheDocument();
  expect(screen.getByText("Git detected")).toBeInTheDocument();
  expect(screen.getByText("Your source remains local.")).toBeInTheDocument();
});

test("shows the protected behavior, runtime, capture review, and evidence workflow", async () => {
  const behavior = {
    id: "behavior-1", project_id: "project-1", lifecycle_state: "DRAFT",
    current_version_id: "version-1",
    current_version: { id: "version-1", version_number: 1, title: "Task remains complete", description: "Create and complete a task.", expected_outcome: "The task stays complete.", source_revision: {}, created_at: "2026-08-24T00:00:00Z" },
    versions: [{ id: "version-1", version_number: 1, title: "Task remains complete", description: "Create and complete a task.", expected_outcome: "The task stays complete.", source_revision: {}, created_at: "2026-08-24T00:00:00Z" }],
    links: [], baselines: [], created_at: "2026-08-24T00:00:00Z", updated_at: "2026-08-24T00:00:00Z", archived_at: null,
  };
  const capture = {
    id: "capture-1", project_id: "project-1", behavior_id: "behavior-1", behavior_version_id: "version-1", runtime_configuration_id: "runtime-1", status: "REVIEW_REQUIRED", entry_url: "http://127.0.0.1:8262/", source_revision: {}, source_stale: false,
    steps: [{ id: "step-1", ordinal: 1, event_type: "click", page_url: "http://127.0.0.1:8262/", selector: "[data-testid=task-item]", metadata: {}, occurred_at: "2026-08-24T00:00:00Z" }],
    observations: [], started_at: "2026-08-24T00:00:00Z", stopped_at: "2026-08-24T00:01:00Z", error_code: null,
  };
  responses["/projects"] = { projects: [project] };
  responses["/projects/project-1"] = project;
  responses["/projects/project-1/impact/summary"] = { files_indexed: 1, languages: 1, language_counts: {}, direct_relationships: 0, tests_found: 0, sensitive_files: 0, unknown_references: 0, unsupported_files: 0, stale_relationships: 0 };
  responses["/projects/project-1/behaviors"] = { behaviors: [behavior] };
  responses["/projects/project-1/runtimes"] = { runtimes: [{ id: "runtime-1", project_id: "project-1", display_name: "PulsePlan", base_url: "http://127.0.0.1:8262/", allowed_origin: "http://127.0.0.1:8262", created_at: "2026-08-24T00:00:00Z", updated_at: "2026-08-24T00:00:00Z" }] };
  responses["/projects/project-1/captures"] = { captures: [capture] };
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /demo/i }));
  fireEvent.click(await screen.findByRole("button", { name: "Behaviors" }));
  expect(await screen.findByText("Protected behaviors")).toBeInTheDocument();
  expect(screen.getAllByText("Task remains complete").length).toBeGreaterThan(0);
  expect(screen.getByText("Review required")).toBeInTheDocument();
  expect(screen.getByText("MellowYak does not label this capture as pass, fail, or regression.")).toBeInTheDocument();
  expect(screen.getByText("Only http://127.0.0.1 or http://localhost with an explicit port is allowed.")).toBeInTheDocument();
});

test("renders the protected behavior workflow in full Hebrew RTL", async () => {
  responses["/projects"] = { projects: [project] };
  responses["/projects/project-1"] = project;
  responses["/projects/project-1/impact/summary"] = { files_indexed: 1, languages: 1, language_counts: {}, direct_relationships: 0, tests_found: 0, sensitive_files: 0, unknown_references: 0, unsupported_files: 0, stale_relationships: 0 };
  responses["/projects/project-1/behaviors"] = { behaviors: [] };
  responses["/projects/project-1/runtimes"] = { runtimes: [] };
  responses["/projects/project-1/captures"] = { captures: [] };
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /demo/i }));
  fireEvent.change(screen.getByLabelText("Language"), { target: { value: "he" } });
  fireEvent.click(await screen.findByRole("button", { name: "התנהגויות" }));
  expect(await screen.findByText("התנהגויות מוגנות")).toBeInTheDocument();
  expect(screen.getByText("הגנו על ההתנהגות הראשונה שאינכם רוצים ששינוי AI ישבור.")).toBeInTheDocument();
  expect(document.documentElement).toHaveAttribute("dir", "rtl");
  expect(document.querySelector("main")).toHaveAttribute("dir", "rtl");
});

test("renders a deterministic validated candidate from translation keys", async () => {
  window.history.replaceState({}, "", "/?phase8State=candidate-validated");
  render(<App />);
  expect(screen.getByText("Candidate repair validated")).toBeInTheDocument();
  expect(screen.getByText("Required workspace checks")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Prepare apply" })).toBeEnabled();
});

test("requires deliberate confirmation on the translated apply surface", async () => {
  window.history.replaceState({}, "", "/?phase8State=apply-confirmation");
  render(<App />);
  expect(screen.getByText("MellowYak will apply only this validated candidate.")).toBeInTheDocument();
  expect(screen.getByText("MellowYak will not restore unrelated historical files.")).toBeInTheDocument();
  expect(screen.getByRole("checkbox")).toBeChecked();
});

test("shows recovery required without claiming success", async () => {
  window.history.replaceState({}, "", "/?phase8State=recovery-required");
  render(<App />);
  expect(screen.getByText("Manual recovery is required")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Continue" })).toBeDisabled();
  expect(screen.queryByText("Applied and verified")).not.toBeInTheDocument();
});

test("renders Phase 8 Hebrew confirmation in full RTL", async () => {
  window.history.replaceState({}, "", "/?phase8State=hebrew-apply-confirmation");
  render(<App />);
  expect(await screen.findByText("החלת תיקון מאומת")).toBeInTheDocument();
  expect(document.documentElement).toHaveAttribute("dir", "rtl");
  expect(document.querySelector("main")).toHaveAttribute("dir", "rtl");
});
