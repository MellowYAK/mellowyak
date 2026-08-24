import { cleanup, configure, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { App } from "./App";
import { resetBootstrapForTests } from "./api";

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
  "/health": { status: "ready", mode: "local", engine_version: "0.1.0", app_version: "0.1.0", database_status: "ready", database_schema_version: "0004_behavior_evidence_browser", data_root: "/local/MellowYak", cloud_connected: false, outbound_network_enabled: false, uptime_seconds: 1 },
  "/readiness": { ready: true, checks: { local_only: true, database_ready: true } },
  "/installation": { installation_id: "install-1", created_at: "2026-08-23T00:00:00Z", last_started_at: "2026-08-23T00:00:00Z", app_version: "0.1.0", engine_version: "0.1.0", database_schema_version: "0004_behavior_evidence_browser" },
  "/settings/privacy": { mode: "local", cloud_connected: false, outbound_network_enabled: false, source_upload_enabled: false, telemetry_upload_enabled: false, account_required: false },
  "/storage/paths": { data_root: "/local/MellowYak", database: "/local/MellowYak/database", evidence: "/local/MellowYak/evidence", projects: "/local/MellowYak/projects", cache: "/local/MellowYak/cache", logs: "/local/MellowYak/logs", runtime: "/local/MellowYak/runtime", backups: "/local/MellowYak/backups" },
  "/projects": { projects: [] },
  "/projects/detect": {
    selected_path: "/work/demo", repository_path: "/work/demo", suggested_name: "demo",
    git: { available: true, branch: "main", head_sha: "1234567890abcdef", is_detached: false, is_dirty: true, staged: ["src/a.ts"], unstaged: [], untracked: ["notes.txt"], ignored_count: 2, worktree_fingerprint: "fp", error: null },
    languages: ["TypeScript"], language_counts: { TypeScript: 4 }, frameworks: ["React"], tests: ["Vitest"], runtime_hints: ["Node.js application hint"], candidate_files: 8, ignored_paths: 2, relationship_coverage: "bounded deterministic adapters", unsupported_coverage: "reported during initial scan", source_remains_local: true
  }
};

const git = { available: true, branch: "main", head_sha: "1234567890abcdef", is_detached: false, is_dirty: true, staged: ["src/a.ts"], unstaged: [], untracked: [], ignored_count: 2, worktree_fingerprint: "fp", error: null };
const scan = { id: "scan-1", status: "completed", scan_version: "1", started_at: "2026-08-24T00:00:00Z", completed_at: "2026-08-24T00:00:01Z", total_candidates: 2, processed_files: 2, included_files: 2, excluded_files: 0, binary_files: 0, sensitive_files: 0, failed_files: 0, unknown_items: 0, unsupported_files: 0, test_files: 1, relationship_count: 1, duration_seconds: 1, error_summary: null };
const project = { id: "project-1", display_name: "demo", display_path: "/work/demo", repository_path: "/work/demo", monitoring_mode: "passive", monitoring_status: "active", last_scan_status: "completed", last_scan_at: "2026-08-24T00:00:01Z", created_at: "2026-08-24T00:00:00Z", updated_at: null, languages: ["TypeScript"], frameworks: ["React"], tests: ["Vitest"], runtime_hints: [], git, scan, source_remains_local: true };
const change = { id: "change-1", project_id: "project-1", change_kind: "uncommitted_worktree", revision: 1, base_head_sha: git.head_sha, head_sha: git.head_sha, worktree_fingerprint: "fp", changed_paths: ["src/a.ts"], task_intent: null, status: "change_detected", created_at: "2026-08-24T00:00:00Z", updated_at: "2026-08-24T00:00:00Z" };
const analysis = { id: "analysis-1", project_id: "project-1", change_id: "change-1", analysis_revision: 1, base_head_sha: git.head_sha, head_sha: git.head_sha, worktree_fingerprint: "fp", scan_revision: "scan-1", algorithm_version: "reverse-impact-v1", status: "completed", changed_file_count: 1, impacted_node_count: 2, unknown_count: 1, stale_count: 0, heuristic_count: 0, truncated: false, truncation_reasons: [], duration_ms: 2, stale: false, stale_reasons: [], created_at: "2026-08-24T00:00:00Z" };
const impact = { analysis, results: [
  { id: "result-1", node_id: "node-1", node_type: "FILE", display_name: "src/a.ts", relative_path: "src/a.ts", impact_class: "changed", minimum_depth: 0, strongest_provenance: "EXACT_PARSER", stale: false, unknown: false, explanation: "Changed file.", path_count: 1, ranking_score: 100, ranking_reasons: ["changed"], unknown_reason: null },
  { id: "result-2", node_id: null, node_type: "UNKNOWN", display_name: "missing-module", relative_path: null, impact_class: "unknown_boundary", minimum_depth: 1, strongest_provenance: "UNKNOWN", stale: false, unknown: true, explanation: "Resolution stopped at an unknown boundary.", path_count: 1, ranking_score: 1, ranking_reasons: ["unknown"], unknown_reason: "unresolved import" },
] };
const receipt = { schema: "mellowyak.context_receipt.v1", id: "receipt-1", project: { id: "project-1", name: "demo" }, change_id: "change-1", analysis_id: "analysis-1", request: "update parser", source_revision: {}, selected_files: [{ relative_path: "src/a.ts", type: "FILE", reason_selected: "Changed file.", relationship_provenance: "EXACT_PARSER", relevance_class: "changed", stale: false, size: 10, content_eligible: true, selection_reasons: ["changed"] }], selected_symbols: [], related_tests: [], relationship_paths: [], constraints: { source_content_included: false }, unknowns: [{ path: "missing-module", reason: "unresolved import" }], excluded_context: [], selection_reasons: ["changed"], size_metrics: { selected_files: 1, selected_source_bytes: 0 }, truncated: false, stale: false, source_uploaded: false, created_at: "2026-08-24T00:00:00Z" };

beforeEach(() => {
  document.documentElement.lang = "en";
  document.documentElement.dir = "ltr";
  Reflect.deleteProperty(window, "__TAURI_INTERNALS__");
  resetBootstrapForTests(); dialogOpen.mockReset(); dialogOpen.mockResolvedValue("/work/demo"); updaterCheck.mockReset(); relaunch.mockReset();
  tauriInvoke.mockReset();
  tauriInvoke.mockResolvedValue({ host: "127.0.0.1", port: 43123, token: "memory-only" });
  responses["/projects"] = { projects: [] };
  responses["/readiness"] = { ready: true, checks: { local_only: true, database_ready: true } };
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const path = new URL(String(input)).pathname;
    return new Response(JSON.stringify(responses[path]), { status: 200, headers: { "Content-Type": "application/json" } });
  }));
});

test("waits for an asynchronously starting packaged engine without crashing", async () => {
  tauriInvoke.mockRejectedValueOnce("ENGINE_STARTING");
  render(<App />);
  expect(screen.getByText("Preparing your local engine")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText("Running")).toBeInTheDocument());
  expect(tauriInvoke).toHaveBeenCalledTimes(2);
});

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

test("renders real engine values and local privacy status", async () => {
  render(<App />);
  expect(screen.getByText("Preparing your local engine")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText("Running")).toBeInTheDocument());
  expect(screen.getByText("/local/MellowYak")).toBeInTheDocument();
  expect(screen.getByText("SQLite — Local")).toBeInTheDocument();
  expect(screen.getByText("Not connected")).toBeInTheDocument();
  expect(screen.getByText("Your code stays local.")).toBeInTheDocument();
  expect(screen.getByText("No Docker.")).toBeInTheDocument();
  expect(screen.getByText("0004_behavior_evidence_browser")).toBeInTheDocument();
});

test("does not report ready or render projects before real project discovery completes", async () => {
  let releaseProjects: (() => void) | undefined;
  const projectGate = new Promise<void>((resolve) => { releaseProjects = resolve; });
  responses["/projects"] = { projects: [project] };
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const path = new URL(String(input)).pathname;
    if (path === "/projects") await projectGate;
    return new Response(JSON.stringify(responses[path]), { status: 200, headers: { "Content-Type": "application/json" } });
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
  expect(await screen.findByText("Running")).toBeInTheDocument();
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
  await screen.findByText("Your local engine is ready.");
  expect(await screen.findByRole("img", { name: "MellowYak waving hello" })).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Language"), { target: { value: "he" } });
  expect(await screen.findByText("המנוע המקומי מוכן.")).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "MellowYak מנופף לשלום" })).toBeInTheDocument();
  expect(screen.getByText("הנתונים שלכם נשארים במחשב הזה.")).toBeInTheDocument();
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
  fireEvent.click(await screen.findByRole("button", { name: "Changes" }));
  expect(await screen.findByText("Changed Files")).toBeInTheDocument();
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

test("uses the native folder picker and reports real project detection", async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Add your first project" }));
  fireEvent.click(screen.getByRole("button", { name: "Choose project folder" }));
  await waitFor(() => expect(dialogOpen).toHaveBeenCalledWith(expect.objectContaining({ directory: true, multiple: false })));
  expect(await screen.findByText("Detected project")).toBeInTheDocument();
  expect(screen.getByDisplayValue("demo")).toBeInTheDocument();
  expect(screen.getByText("1234567890ab")).toBeInTheDocument();
  expect(screen.getByText("1 staged · 0 unstaged · 1 untracked")).toBeInTheDocument();
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
