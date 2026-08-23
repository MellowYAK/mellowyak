import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { App } from "./App";
import { resetBootstrapForTests } from "./api";

const dialogOpen = vi.fn();

vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn().mockResolvedValue({ host: "127.0.0.1", port: 43123, token: "memory-only" }) }));
vi.mock("@tauri-apps/plugin-dialog", () => ({ open: (...args: unknown[]) => dialogOpen(...args) }));

const responses: Record<string, unknown> = {
  "/health": { status: "ready", mode: "local", engine_version: "0.1.0", app_version: "0.1.0", database_status: "ready", database_schema_version: "0002_project_git_impact", data_root: "/local/MellowYak", cloud_connected: false, outbound_network_enabled: false, uptime_seconds: 1 },
  "/readiness": { ready: true, checks: { local_only: true, database_ready: true } },
  "/installation": { installation_id: "install-1", created_at: "2026-08-23T00:00:00Z", last_started_at: "2026-08-23T00:00:00Z", app_version: "0.1.0", engine_version: "0.1.0", database_schema_version: "0002_project_git_impact" },
  "/settings/privacy": { mode: "local", cloud_connected: false, outbound_network_enabled: false, source_upload_enabled: false, telemetry_upload_enabled: false, account_required: false },
  "/storage/paths": { data_root: "/local/MellowYak", database: "/local/MellowYak/database", evidence: "/local/MellowYak/evidence", projects: "/local/MellowYak/projects", cache: "/local/MellowYak/cache", logs: "/local/MellowYak/logs", runtime: "/local/MellowYak/runtime", backups: "/local/MellowYak/backups" },
  "/projects": { projects: [] },
  "/projects/detect": {
    selected_path: "/work/demo", repository_path: "/work/demo", suggested_name: "demo",
    git: { available: true, branch: "main", head_sha: "1234567890abcdef", is_detached: false, is_dirty: true, staged: ["src/a.ts"], unstaged: [], untracked: ["notes.txt"], ignored_count: 2, worktree_fingerprint: "fp", error: null },
    languages: ["TypeScript"], language_counts: { TypeScript: 4 }, frameworks: ["React"], tests: ["Vitest"], runtime_hints: ["Node.js application hint"], candidate_files: 8, ignored_paths: 2, relationship_coverage: "bounded deterministic adapters", unsupported_coverage: "reported during initial scan", source_remains_local: true
  }
};

beforeEach(() => {
  resetBootstrapForTests(); dialogOpen.mockReset(); dialogOpen.mockResolvedValue("/work/demo");
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const path = new URL(String(input)).pathname;
    return new Response(JSON.stringify(responses[path]), { status: 200, headers: { "Content-Type": "application/json" } });
  }));
});

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

test("renders real engine values and local privacy status", async () => {
  render(<App />);
  expect(screen.getByText("Verifying local engine and storage…")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText("Running")).toBeInTheDocument());
  expect(screen.getByText("/local/MellowYak")).toBeInTheDocument();
  expect(screen.getByText("SQLite — Local")).toBeInTheDocument();
  expect(screen.getByText("Not connected")).toBeInTheDocument();
  expect(screen.getByText("Your code stays local.")).toBeInTheDocument();
  expect(screen.getByText("No Docker.")).toBeInTheDocument();
  expect(screen.getByText("0002_project_git_impact")).toBeInTheDocument();
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
