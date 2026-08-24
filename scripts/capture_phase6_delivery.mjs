#!/usr/bin/env node

import { spawn } from "node:child_process";
import { copyFile, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { chromium } from "../apps/desktop/node_modules/playwright-core/index.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const desktop = path.join(root, "apps", "desktop");
const output = path.join(root, "docs", "phase-6-desktop-productization-2026-08-24");
const chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const baseUrl = "http://127.0.0.1:1420";

const git = { available: true, branch: "main", head_sha: "8fc79e1c8ad7446849941219bf17f01a8fa3c141", is_detached: false, is_dirty: true, staged: [], unstaged: ["src/dashboard.tsx"], untracked: ["tests/dashboard.spec.ts"], ignored_count: 18, worktree_fingerprint: "phase6-public-fixture", error: null };
const scan = { id: "scan-public", status: "completed", scan_version: "1", started_at: "2026-08-24T12:00:00Z", completed_at: "2026-08-24T12:00:03Z", total_candidates: 284, processed_files: 284, included_files: 268, excluded_files: 16, binary_files: 3, sensitive_files: 2, failed_files: 0, unknown_items: 3, unsupported_files: 4, test_files: 41, relationship_count: 792, duration_seconds: 3, error_summary: null };
const project = { id: "project-public", display_name: "PulsePlan Demo", display_path: "/workspace/pulseplan-demo", repository_path: "/workspace/pulseplan-demo", monitoring_mode: "passive", monitoring_status: "active", last_scan_status: "completed", last_scan_at: "2026-08-24T12:00:03Z", created_at: "2026-08-24T12:00:00Z", updated_at: "2026-08-24T12:00:03Z", languages: ["TypeScript", "Python"], frameworks: ["React", "FastAPI"], tests: ["Vitest", "Pytest"], runtime_hints: ["Node.js", "Python"], git, scan, source_remains_local: true, disconnected: false, source_available: true, notifications_muted: false };
const projectPaused = { ...project, id: "project-paused", display_name: "Ledger Sample", repository_path: "/workspace/ledger-sample", display_path: "/workspace/ledger-sample", monitoring_mode: "paused", monitoring_status: "paused", notifications_muted: true };
const alerts = [
  { id: "alert-regression", project_id: project.id, change_id: "change-public", behavior_id: "behavior-checkout", regression_id: "regression-public", gate_id: null, severity: "CRITICAL", category: "REGRESSION", title_key: "alerts.regressionTitle", summary_key: "alerts.regressionSummary", parameters: { project: project.display_name }, route: { screen: "change", project_id: project.id }, read: false, resolved: false, created_at: "2026-08-24T12:04:00Z", updated_at: "2026-08-24T12:04:00Z" },
  { id: "alert-gate", project_id: project.id, change_id: "change-public", behavior_id: null, regression_id: null, gate_id: "gate-public", severity: "HIGH", category: "GATE", title_key: "alerts.blockedTitle", summary_key: "alerts.blockedSummary", parameters: { project: project.display_name }, route: { screen: "change", project_id: project.id }, read: true, resolved: false, created_at: "2026-08-24T12:05:00Z", updated_at: "2026-08-24T12:05:00Z" },
  { id: "alert-complete", project_id: projectPaused.id, change_id: "change-resolved", behavior_id: null, regression_id: null, gate_id: "gate-resolved", severity: "INFO", category: "GATE", title_key: "alerts.verifiedTitle", summary_key: "alerts.verifiedSummary", parameters: { project: projectPaused.display_name }, route: { screen: "change", project_id: projectPaused.id }, read: true, resolved: true, created_at: "2026-08-24T11:00:00Z", updated_at: "2026-08-24T11:03:00Z" },
];
const setup = {
  "/health": { status: "ready", mode: "local", engine_version: "0.1.0", app_version: "0.1.0", database_status: "ready", database_schema_version: "0006_desktop_productization", data_root: "/local/MellowYak", cloud_connected: false, outbound_network_enabled: false, uptime_seconds: 42 },
  "/readiness": { ready: true, checks: { local_only: true, database_ready: true } },
  "/installation": { installation_id: "phase6-public-fixture", created_at: "2026-08-24T12:00:00Z", last_started_at: "2026-08-24T12:00:00Z", app_version: "0.1.0", engine_version: "0.1.0", database_schema_version: "0006_desktop_productization" },
  "/settings/privacy": { mode: "local", cloud_connected: false, outbound_network_enabled: false, source_upload_enabled: false, telemetry_upload_enabled: false, account_required: false },
  "/storage/paths": { data_root: "/local/MellowYak", database: "/local/MellowYak/database", evidence: "/local/MellowYak/evidence", projects: "/local/MellowYak/projects", cache: "/local/MellowYak/cache", logs: "/local/MellowYak/logs", runtime: "/local/MellowYak/runtime", backups: "/local/MellowYak/backups" },
};
const notificationSettings = { native_enabled: true, regression_enabled: true, blocked_gate_enabled: true, needs_review_enabled: true, project_errors_enabled: true, verified_complete_enabled: false, regression_resolved_enabled: false, show_behavior_name: true, show_project_name: true, hide_details: false, critical_override: true };

function responseFor(url, method) {
  const parsed = new URL(url); const pathname = parsed.pathname;
  if (pathname in setup) return setup[pathname];
  if (pathname === "/projects" && method === "GET") return { projects: [project, projectPaused] };
  if (pathname === "/alerts") { const state = parsed.searchParams.get("state"); return { alerts: state === "resolved" ? alerts.filter((item) => item.resolved) : state === "unread" ? alerts.filter((item) => !item.read && !item.resolved) : state === "attention" ? alerts.filter((item) => !item.resolved && item.severity !== "INFO") : alerts }; }
  if (pathname === "/alerts/unread-count") return { count: 1 };
  if (pathname === "/settings/notifications") return notificationSettings;
  if (pathname === "/settings/quiet-mode") return { active: false, started_at: null, ends_at: null, until_turned_off: false, allow_critical: false, remaining_seconds: null };
  if (pathname === "/settings/quiet-mode/start") return { active: true, started_at: "2026-08-24T12:10:00Z", ends_at: "2026-08-24T13:10:00Z", until_turned_off: false, allow_critical: false, remaining_seconds: 3600 };
  if (pathname === "/app/background-status") return { keep_running_on_close: true, start_at_login: false, start_at_login_supported: true, background_supported: true };
  if (pathname === `/projects/${project.id}`) return project;
  if (pathname === `/projects/${projectPaused.id}`) return projectPaused;
  if (pathname.endsWith("/impact/summary")) return { files_indexed: 268, languages: 2, language_counts: { TypeScript: 188, Python: 80 }, direct_relationships: 792, tests_found: 41, sensitive_files: 2, unknown_references: 3, unsupported_files: 4, stale_relationships: 0 };
  if (pathname.endsWith("/capabilities")) return { mode: "local_source_with_runtime", source_available: true, runtime_available: true, available: ["git_observation", "source_scan", "impact", "protected_behaviors", "local_evidence", "human_attestation", "browser_capture", "browser_replay", "assertions", "regression_detection", "completion_gate"], unavailable: ["automatic_browser_replay"], future_only: ["runtime_only"], source_remains_local: true };
  if (pathname.endsWith("/deletion-preview")) return { project_id: project.id, project_name: project.display_name, source_path: "pulseplan-demo", mellowyak_data_bytes: 245760, behavior_count: 4, evidence_count: 7, regression_count: 1, source_will_be_modified: false };
  return {};
}

const screens = [
  { file: "01-command-center-en.png", locale: "en-US", page: "home", title: "Command Center — English", description: "Global project metrics, actionable alerts, project health, and recent verified outcomes.", actions: "Open a project, all projects, or the alerts inbox." },
  { file: "02-projects-en.png", locale: "en-US", page: "projects", title: "Projects — English", description: "Searchable and filterable project lifecycle table.", actions: "Search, filter, add, open, or reveal project actions." },
  { file: "03-project-actions-en.png", locale: "en-US", page: "project-actions", title: "Project action menu — English", description: "Bounded project operations with destructive actions visually separated.", actions: "Open, reveal source, scan, pause, mute, disconnect, or delete local data." },
  { file: "04-disconnect-en.png", locale: "en-US", page: "disconnect", title: "Disconnect confirmation — English", description: "Explains that monitoring stops while MellowYak records and source remain safe.", actions: "Cancel or disconnect." },
  { file: "05-delete-local-data-en.png", locale: "en-US", page: "delete", title: "Delete local data confirmation — English", description: "Shows the local records affected and requires the exact project name.", actions: "Cancel or permanently delete only MellowYak project data." },
  { file: "06-alerts-en.png", locale: "en-US", page: "alerts", title: "Alerts Center — English", description: "Persistent regression, gate, and resolved outcome records.", actions: "Filter, open context, mark read or unread, resolve, and clear resolved." },
  { file: "07-settings-en.png", locale: "en-US", page: "settings", title: "Settings — English", description: "Native notification categories, privacy detail controls, quiet mode, background close, and login startup.", actions: "Toggle alert categories, quiet mode, background lifecycle, and start at login." },
  { file: "08-quiet-mode-en.png", locale: "en-US", page: "quiet", title: "Quiet Mode active — English", description: "Persistent time-bounded suppression state with an explicit end action.", actions: "End quiet mode." },
  { file: "09-capabilities-en.png", locale: "en-US", page: "capabilities", title: "Project capabilities — English", description: "Truthful available and unavailable features for a local source plus runtime.", actions: "Review source scan, Git, impact, evidence, replay, regression, and gate availability." },
  { file: "10-command-center-he.png", locale: "he-IL", page: "home", title: "Command Center — Hebrew RTL", description: "The complete command center mirrored and translated right-to-left.", actions: "Open projects, alerts, and project context." },
  { file: "11-projects-he.png", locale: "he-IL", page: "projects", title: "Projects — Hebrew RTL", description: "Project search, filters, states, and actions in full RTL.", actions: "Search, filter, add, open, and manage projects." },
  { file: "12-settings-he.png", locale: "he-IL", page: "settings", title: "Settings — Hebrew RTL", description: "Notification, quiet mode, startup, and privacy settings in full RTL.", actions: "Control all desktop preferences." },
];

async function waitForServer() { for (let i = 0; i < 80; i += 1) { try { if ((await fetch(baseUrl)).ok) return; } catch {} await new Promise((resolve) => setTimeout(resolve, 250)); } throw new Error("Vite server unavailable"); }
function escapeHtml(value) { return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;"); }

await mkdir(output, { recursive: true });
await copyFile(path.join(root, "assets", "brand", "mellowyak-app-icon.png"), path.join(output, "00-app-icon.png"));
const server = spawn("npm", ["run", "dev", "--", "--host", "127.0.0.1"], { cwd: desktop, stdio: ["ignore", "pipe", "pipe"] });
try {
  await waitForServer();
  const browser = await chromium.launch({ executablePath: chrome, headless: true });
  try {
    for (const screen of screens) {
      const context = await browser.newContext({ locale: screen.locale, viewport: { width: 1440, height: 1000 }, colorScheme: "dark" });
      await context.addInitScript(() => { let id = 0; const callbacks = new Map(); window.__TAURI_INTERNALS__ = { callbacks, transformCallback: (callback, once = false) => { id += 1; callbacks.set(id, { callback, once }); return id; }, unregisterCallback: (value) => callbacks.delete(value), invoke: async (command) => { if (command === "engine_bootstrap") return { host: "127.0.0.1", port: 43126, token: "public-review" }; if (command === "get_start_at_login") return false; if (command === "take_pending_route") return null; if (command.includes("listen")) return 1; return null; } }; });
      const page = await context.newPage();
      await page.route("http://127.0.0.1:43126/**", async (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(responseFor(route.request().url(), route.request().method())) }));
      await page.goto(baseUrl, { waitUntil: "networkidle" });
      await page.getByText(screen.locale.startsWith("he") ? "הפרויקטים שלכם, מובנים מקומית." : "Your projects, understood locally.").waitFor();
      const names = screen.locale.startsWith("he") ? { projects: "פרויקטים", alerts: "התראות", settings: "הגדרות", actions: "פעולות פרויקט", disconnect: "ניתוק פרויקט", remove: "מחיקת נתוני MellowYak מקומיים", quiet: "שקט לשעה", project: project.display_name } : { projects: "Projects", alerts: "Alerts", settings: "Settings", actions: "Project actions", disconnect: "Disconnect project", remove: "Delete MellowYak local data", quiet: "Quiet for one hour", project: project.display_name };
      if (["projects", "project-actions", "disconnect", "delete"].includes(screen.page)) await page.getByRole("button", { name: names.projects, exact: true }).click();
      if (["project-actions", "disconnect", "delete"].includes(screen.page)) await page.getByRole("button", { name: names.actions }).first().click();
      if (screen.page === "disconnect") await page.getByRole("button", { name: names.disconnect }).click();
      if (screen.page === "delete") await page.getByRole("button", { name: names.remove }).click();
      if (screen.page === "alerts") await page.getByRole("button", { name: names.alerts, exact: true }).click();
      if (["settings", "quiet"].includes(screen.page)) await page.getByRole("button", { name: names.settings, exact: true }).click();
      if (screen.page === "quiet") await page.getByRole("button", { name: names.quiet }).click();
      if (screen.page === "capabilities") await page.getByRole("button", { name: names.project }).last().click();
      await page.waitForTimeout(250);
      await page.screenshot({ path: path.join(output, screen.file), fullPage: true });
      await context.close();
      process.stdout.write(`${screen.file}\n`);
    }
    const markdown = ["# MellowYak Phase 6 screen guide", "", "All screenshots use synthetic public fixture data. No private repository path, credential, source content, or user data is included.", ""];
    screens.forEach((screen, index) => markdown.push(`## ${index + 1}. ${screen.title}`, "", `![${screen.title}](${screen.file})`, "", `- What is shown: ${screen.description}`, `- Available actions: ${screen.actions}`, ""));
    await writeFile(path.join(output, "PHASE_6_SCREEN_GUIDE.md"), `${markdown.join("\n")}\n`);
    const sections = screens.map((screen, index) => `<section><h1>${index + 1}. ${escapeHtml(screen.title)}</h1><img src="${screen.file}"><p><strong>What is shown:</strong> ${escapeHtml(screen.description)}</p><p><strong>Available actions:</strong> ${escapeHtml(screen.actions)}</p></section>`).join("\n");
    const html = `<!doctype html><html lang="en"><meta charset="utf-8"><style>@page{size:A4 landscape;margin:12mm}body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;color:#102334}section{page-break-after:always}h1{font-size:21px}img{display:block;max-width:100%;max-height:145mm;margin:auto;border:1px solid #cad6dc;border-radius:8px}p{font-size:11px}</style><body><section><h1>MellowYak Phase 6 — Desktop Productization</h1><img src="00-app-icon.png"><p>English base + Hebrew RTL · synthetic public fixture data</p></section>${sections}</body></html>`;
    await writeFile(path.join(output, "PHASE_6_SCREEN_GUIDE.html"), html);
    const pdf = await browser.newPage();
    await pdf.goto(`file://${path.join(output, "PHASE_6_SCREEN_GUIDE.html")}`, { waitUntil: "networkidle" });
    await pdf.pdf({ path: path.join(output, "MellowYak-Phase-6-Screen-Guide.pdf"), format: "A4", landscape: true, printBackground: true });
    await pdf.close();
  } finally { await browser.close(); }
} finally { server.kill("SIGTERM"); }
