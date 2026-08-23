import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { App } from "./App";
import { resetBootstrapForTests } from "./api";

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn().mockResolvedValue({ host: "127.0.0.1", port: 43123, token: "memory-only" }),
}));

const responses: Record<string, unknown> = {
  "/health": { status: "ready", mode: "local", engine_version: "0.1.0", app_version: "0.1.0", database_status: "ready", database_schema_version: "0001_local_core", data_root: "/local/MellowYak", cloud_connected: false, outbound_network_enabled: false, uptime_seconds: 1 },
  "/readiness": { ready: true, checks: { local_only: true, database_ready: true } },
  "/installation": { installation_id: "install-1", created_at: "2026-08-23T00:00:00Z", last_started_at: "2026-08-23T00:00:00Z", app_version: "0.1.0", engine_version: "0.1.0", database_schema_version: "0001_local_core" },
  "/settings/privacy": { mode: "local", cloud_connected: false, outbound_network_enabled: false, source_upload_enabled: false, telemetry_upload_enabled: false, account_required: false },
  "/storage/paths": { data_root: "/local/MellowYak", database: "/local/MellowYak/database", evidence: "/local/MellowYak/evidence", projects: "/local/MellowYak/projects", cache: "/local/MellowYak/cache", logs: "/local/MellowYak/logs", runtime: "/local/MellowYak/runtime", backups: "/local/MellowYak/backups" },
  "/system/open-data-folder": { opened: true, method: "test" },
};

beforeEach(() => {
  resetBootstrapForTests();
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const path = new URL(String(input)).pathname;
    return new Response(JSON.stringify(responses[path]), { status: 200, headers: { "Content-Type": "application/json" } });
  }));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test("renders real engine values and local privacy status", async () => {
  render(<App />);
  expect(screen.getByText("Verifying local engine and storage…")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText("Running")).toBeInTheDocument());
  expect(screen.getByText("/local/MellowYak")).toBeInTheDocument();
  expect(screen.getByText("SQLite — Local")).toBeInTheDocument();
  expect(screen.getByText("Not connected")).toBeInTheDocument();
  expect(screen.getByText("Your code stays local.")).toBeInTheDocument();
  expect(screen.getByText("Your project data stays local.")).toBeInTheDocument();
  expect(screen.getByText("Your evidence stays local.")).toBeInTheDocument();
  expect(screen.getByText("Data leaves only through connectors you explicitly enable.")).toBeInTheDocument();
  expect(screen.getByText("No Docker.")).toBeInTheDocument();
  expect(screen.getByText("No external database.")).toBeInTheDocument();
  expect(screen.getByText("No cloud required.")).toBeInTheDocument();
  expect(screen.getByText("0001_local_core")).toBeInTheDocument();
});

test("add project is an honest Phase 2 placeholder", async () => {
  render(<App />);
  const button = await screen.findByRole("button", { name: "Add your first project" });
  fireEvent.click(button);
  expect(screen.getByText("Project selection, Git observation, and source scanning are intentionally deferred to Phase 2.")).toBeInTheDocument();
});
