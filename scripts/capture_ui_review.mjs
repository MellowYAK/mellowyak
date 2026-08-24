#!/usr/bin/env node

import { spawn } from "node:child_process";
import { copyFile, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { chromium } from "../apps/desktop/node_modules/playwright-core/index.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const desktop = path.join(root, "apps", "desktop");
const output = path.join(root, "docs", "ui-review", "phase-3-2026-08-24");
const chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const baseUrl = "http://127.0.0.1:1420";

const git = {
  available: true,
  branch: "main",
  head_sha: "1234567890abcdef1234567890abcdef12345678",
  is_detached: false,
  is_dirty: true,
  staged: ["src/impact.ts"],
  unstaged: ["src/panel.tsx"],
  untracked: ["tests/panel.spec.ts"],
  ignored_count: 12,
  worktree_fingerprint: "fixture-fingerprint",
  error: null,
};

const completedScan = {
  id: "scan-1",
  status: "completed",
  scan_version: "1",
  started_at: "2026-08-24T00:00:00Z",
  completed_at: "2026-08-24T00:00:02Z",
  total_candidates: 184,
  processed_files: 184,
  included_files: 172,
  excluded_files: 12,
  binary_files: 2,
  sensitive_files: 1,
  failed_files: 0,
  unknown_items: 2,
  unsupported_files: 3,
  test_files: 24,
  relationship_count: 426,
  duration_seconds: 2,
  error_summary: null,
};

const runningScan = {
  ...completedScan,
  id: "scan-running",
  status: "running",
  completed_at: null,
  processed_files: 73,
  included_files: 68,
  relationship_count: 141,
  duration_seconds: null,
};

function project(scan = completedScan) {
  return {
    id: "project-1",
    display_name: "MellowYak Demo",
    display_path: "/workspace/mellowyak-demo",
    repository_path: "/workspace/mellowyak-demo",
    monitoring_mode: "passive",
    monitoring_status: "active",
    last_scan_status: scan.status,
    last_scan_at: "2026-08-24T00:00:02Z",
    created_at: "2026-08-24T00:00:00Z",
    updated_at: null,
    languages: ["TypeScript", "Python", "Rust"],
    frameworks: ["React", "Tauri", "FastAPI"],
    tests: ["Vitest", "Pytest"],
    runtime_hints: ["Node.js", "Python"],
    git,
    scan,
    source_remains_local: true,
  };
}

const change = {
  id: "change-1",
  project_id: "project-1",
  change_kind: "uncommitted_worktree",
  revision: 1,
  base_head_sha: git.head_sha,
  head_sha: git.head_sha,
  worktree_fingerprint: git.worktree_fingerprint,
  changed_paths: ["src/impact.ts", "src/panel.tsx", "tests/panel.spec.ts"],
  task_intent: "Explain the local impact of the current change",
  status: "change_detected",
  created_at: "2026-08-24T00:00:00Z",
  updated_at: "2026-08-24T00:00:00Z",
};

const analysis = {
  id: "analysis-1",
  project_id: "project-1",
  change_id: "change-1",
  analysis_revision: 1,
  base_head_sha: git.head_sha,
  head_sha: git.head_sha,
  worktree_fingerprint: git.worktree_fingerprint,
  scan_revision: "scan-1",
  algorithm_version: "reverse-impact-v1",
  status: "completed",
  changed_file_count: 3,
  impacted_node_count: 6,
  unknown_count: 1,
  stale_count: 1,
  heuristic_count: 2,
  truncated: false,
  truncation_reasons: [],
  duration_ms: 18,
  stale: false,
  stale_reasons: [],
  created_at: "2026-08-24T00:00:00Z",
};

const impact = {
  analysis,
  results: [
    { id: "r1", node_id: "n1", node_type: "FILE", display_name: "src/impact.ts", relative_path: "src/impact.ts", impact_class: "changed", minimum_depth: 0, strongest_provenance: "EXACT_CHANGE", stale: false, unknown: false, explanation: "Exact changed file.", path_count: 1, ranking_score: 100, ranking_reasons: ["changed"], unknown_reason: null },
    { id: "r2", node_id: "n2", node_type: "FILE", display_name: "src/panel.tsx", relative_path: "src/panel.tsx", impact_class: "direct_static", minimum_depth: 1, strongest_provenance: "EXACT_PARSER", stale: false, unknown: false, explanation: "Imports the changed impact module.", path_count: 1, ranking_score: 82, ranking_reasons: ["direct"], unknown_reason: null },
    { id: "r3", node_id: "n3", node_type: "TEST", display_name: "tests/panel.spec.ts", relative_path: "tests/panel.spec.ts", impact_class: "transitive_static", minimum_depth: 2, strongest_provenance: "EXACT_PARSER", stale: false, unknown: false, explanation: "Exercises the related panel.", path_count: 1, ranking_score: 70, ranking_reasons: ["test"], unknown_reason: null },
    { id: "r4", node_id: null, node_type: "UNKNOWN", display_name: "runtime-generated-module", relative_path: null, impact_class: "unknown_boundary", minimum_depth: 2, strongest_provenance: "UNKNOWN", stale: false, unknown: true, explanation: "Resolution stops at an unknown dynamic boundary.", path_count: 1, ranking_score: 30, ranking_reasons: ["unknown"], unknown_reason: "Dynamic module name cannot be resolved statically." },
    { id: "r5", node_id: "n5", node_type: "FILE", display_name: "src/legacy.ts", relative_path: "src/legacy.ts", impact_class: "stale_boundary", minimum_depth: 1, strongest_provenance: "EXACT_PARSER", stale: true, unknown: false, explanation: "Relationship belongs to an older scan revision.", path_count: 1, ranking_score: 20, ranking_reasons: ["stale"], unknown_reason: null },
  ],
};

const receipt = {
  schema: "mellowyak.context_receipt.v1",
  id: "receipt-1",
  project: { id: "project-1", name: "MellowYak Demo" },
  change_id: "change-1",
  analysis_id: "analysis-1",
  request: change.task_intent,
  source_revision: { head: git.head_sha, scan: "scan-1" },
  selected_files: [{ relative_path: "src/impact.ts", type: "FILE", reason_selected: "Exact changed file.", relationship_provenance: "EXACT_CHANGE", relevance_class: "changed", stale: false, size: 8200, content_eligible: true, selection_reasons: ["changed"] }],
  selected_symbols: [],
  related_tests: ["tests/panel.spec.ts"],
  relationship_paths: [{ from: "tests/panel.spec.ts", to: "src/impact.ts", depth: 2 }],
  constraints: { max_files: 20, max_source_bytes: 0, source_content_included: false },
  unknowns: [{ path: "runtime-generated-module", reason: "Dynamic module name cannot be resolved statically." }],
  excluded_context: [{ path: ".env", reason: "sensitive_path" }],
  selection_reasons: ["changed", "related_test"],
  size_metrics: { selected_files: 3, selected_source_bytes: 0 },
  truncated: false,
  stale: false,
  source_uploaded: false,
  created_at: "2026-08-24T00:00:00Z",
};

const setup = {
  "/health": { status: "ready", mode: "local", engine_version: "0.1.0", app_version: "0.1.0", database_status: "ready", database_schema_version: "0003_reverse_impact_context", data_root: "/local/MellowYak", cloud_connected: false, outbound_network_enabled: false, uptime_seconds: 42 },
  "/readiness": { ready: true, checks: { local_only: true, database_ready: true } },
  "/installation": { installation_id: "review-fixture", created_at: "2026-08-24T00:00:00Z", last_started_at: "2026-08-24T00:00:00Z", app_version: "0.1.0", engine_version: "0.1.0", database_schema_version: "0003_reverse_impact_context" },
  "/settings/privacy": { mode: "local", cloud_connected: false, outbound_network_enabled: false, source_upload_enabled: false, telemetry_upload_enabled: false, account_required: false },
  "/storage/paths": { data_root: "/local/MellowYak", database: "/local/MellowYak/database", evidence: "/local/MellowYak/evidence", projects: "/local/MellowYak/projects", cache: "/local/MellowYak/cache", logs: "/local/MellowYak/logs", runtime: "/local/MellowYak/runtime", backups: "/local/MellowYak/backups" },
};

const screens = [
  { name: "01-home-empty-en", locale: "en-US", mode: "empty", title: "Home — empty state (English)", description: "Local engine readiness, privacy promises, versions, and the first-project action.", actions: "Add project, open data folder, inspect diagnostics.", design: "Hero hierarchy, mascot scale, density of privacy/status cards." },
  { name: "02-home-projects-en", locale: "en-US", mode: "ready", title: "Home — connected project (English)", description: "Connected project list with truthful readiness status and passive-monitoring mascot.", actions: "Open a project or add another project.", design: "Project-card prominence, readiness badge, spacing for multiple projects." },
  { name: "03-add-project-en", locale: "en-US", mode: "empty", nav: "add", title: "Add Project — choose folder (English)", description: "Sparse native-folder-picker entry state with source-local reassurance.", actions: "Choose a project folder or return home.", design: "Illustration size, button prominence, explanation width." },
  { name: "04-add-detected-en", locale: "en-US", mode: "empty", nav: "detect", title: "Add Project — detected repository (English)", description: "Detected project metadata, Git state, runtime hints, tests, and monitoring selection.", actions: "Rename, choose another folder, select monitoring mode, connect.", design: "Two-column balance, metadata scanability, privacy note placement." },
  { name: "05-project-ready-en", locale: "en-US", mode: "ready", nav: "project", title: "Project Overview — ready with limits (English)", description: "Source-scan metrics, Git monitoring controls, and bounded impact foundation.", actions: "Run scan, open folder, pause monitoring, switch to Change or Impact.", design: "Metric hierarchy, warning/readiness tone, technical density." },
  { name: "06-project-scanning-en", locale: "en-US", mode: "running", nav: "project", title: "Project Overview — scanning (English)", description: "In-progress scan with mascot, progress, partial counts, and cancellation action.", actions: "Cancel scan, open folder, pause monitoring.", design: "Progress visibility, animation opportunity, mascot restraint." },
  { name: "07-change-detected-en", locale: "en-US", mode: "ready", nav: "change-empty", title: "Change Cockpit — before analysis (English)", description: "Exact working-tree identity and changed files before bounded impact is run.", actions: "Edit optional intent and analyze impact.", design: "Command bar focus, empty-state guidance, changed-file list density." },
  { name: "08-change-analyzed-en", locale: "en-US", mode: "ready", nav: "change", title: "Change Cockpit — analyzed (English)", description: "Related entities, explainable paths, unknown/stale boundaries, and behavior candidates.", actions: "Rerun analysis, generate receipt, keep/dismiss/prepare candidates.", design: "Information hierarchy, card grouping, boundary severity." },
  { name: "09-context-receipt-en", locale: "en-US", mode: "ready", nav: "receipt", title: "Context Receipt — expanded (English)", description: "Metadata-only receipt summary and inspectable selected/excluded context.", actions: "Copy JSON, regenerate, expand or collapse details.", design: "JSON readability, zero-source proof, disclosure control." },
  { name: "10-impact-empty-en", locale: "en-US", mode: "ready", nav: "impact-empty", title: "Impact Explorer — empty query (English)", description: "Search entry and calm helper illustration before a graph query.", actions: "Enter a metadata query and search.", design: "Search prominence, helper-card size, empty-state clarity." },
  { name: "11-impact-results-en", locale: "en-US", mode: "ready", nav: "impact", title: "Impact Explorer — results (English)", description: "Incoming/outgoing relationships with parser provenance, scan revision, and recent changes.", actions: "Refine and rerun search; inspect relationship facts.", design: "Direction labels, provenance legibility, long-path wrapping." },
  { name: "12-update-available-en", locale: "en-US", mode: "empty", update: true, title: "Signed update available (English)", description: "Non-blocking signed GitHub Release notification in the global shell.", actions: "Install the signed update and restart.", design: "Banner urgency, trust language, primary-action strength." },
  { name: "13-engine-unavailable-en", locale: "en-US", mode: "error", title: "Local Engine unavailable (English)", description: "Honest local startup failure without pretending that project data is ready.", actions: "Retry the authoritative startup pipeline or inspect translated technical details.", design: "Recovery guidance, failed-step clarity, error severity." },
  { name: "14-home-empty-he", locale: "he-IL", mode: "empty", title: "דף הבית — מצב ריק (עברית RTL)", description: "אותו מצב מנוע ופרטיות בפריסה מלאה מימין לשמאל.", actions: "הוספת פרויקט, פתיחת תיקיית נתונים והצגת אבחון.", design: "יישור RTL, סדר הכרטיסים, ריווח והיררכיית כותרות." },
  { name: "15-add-project-he", locale: "he-IL", mode: "empty", nav: "add", title: "הוספת פרויקט — בחירת תיקייה (עברית RTL)", description: "מסך בחירה מקומי עם mascot וטקסט מתורגם בלבד.", actions: "בחירת תיקייה או חזרה.", design: "מיקום האיור מול כיוון הקריאה וכפתור הפעולה." },
  { name: "16-add-detected-he", locale: "he-IL", mode: "empty", nav: "detect", title: "הוספת פרויקט — זיהוי מאגר (עברית RTL)", description: "כל מטא־הנתונים והאפשרויות בפריסה עברית.", actions: "שינוי שם, מצב ניטור, בחירה מחדש וחיבור.", design: "טבלאות ערך/תווית RTL ונתיבים טכניים LTR." },
  { name: "17-project-ready-he", locale: "he-IL", mode: "ready", nav: "project", title: "סקירת פרויקט (עברית RTL)", description: "מצב מוכנות, סריקה, Git ומפת השפעה בעברית.", actions: "סריקה, פתיחת תיקייה, ניטור וניווט.", design: "קריאות המספרים והמונחים הטכניים בתוך RTL." },
  { name: "18-change-analyzed-he", locale: "he-IL", mode: "ready", nav: "change", title: "Change Cockpit מנותח (עברית RTL)", description: "תוצאות השפעה, נתיבים וגבולות לא ידועים/לא עדכניים בעברית.", actions: "ניתוח, יצירת קבלה וניהול מועמדי התנהגות.", design: "סדר חזותי של כרטיסים והפרדת נתוני קוד LTR." },
  { name: "19-context-receipt-he", locale: "he-IL", mode: "ready", nav: "receipt", title: "Context Receipt מורחב (עברית RTL)", description: "סיכום מקומי בעברית ו‑JSON טכני בכיוון LTR.", actions: "העתקה, יצירה מחדש והרחבת פירוט.", design: "איזון דו־כיווני ומניעת ערבוב סימני פיסוק." },
  { name: "20-impact-results-he", locale: "he-IL", mode: "ready", nav: "impact", title: "Impact Explorer עם תוצאות (עברית RTL)", description: "קשרים נכנסים ויוצאים, provenance וגרסת סריקה.", actions: "חיפוש ובדיקת עובדות הקשר.", design: "תגיות כיוון, יישור טקסט ונתיבים ארוכים." },
  { name: "21-update-available-he", locale: "he-IL", mode: "empty", update: true, title: "עדכון חתום זמין (עברית RTL)", description: "התראת עדכון גלובלית עם גרסה ופעולת התקנה מתורגמת.", actions: "התקנת העדכון והפעלה מחדש.", design: "מיקום הבאנר, אמון ודרגת הדחיפות." },
  { name: "22-startup-loading-en", locale: "en-US", mode: "startup", title: "Real startup pipeline (English)", description: "Animated MellowYak, the currently active real project-discovery step, meaningful progress, and completed/pending stages.", actions: "Wait for local startup; language remains selectable while work continues.", design: "Compact hierarchy, animation scale, progress readability, calm local tone." },
  { name: "23-startup-loading-he", locale: "he-IL", mode: "startup", title: "תהליך אתחול אמיתי (עברית RTL)", description: "אנימציית MellowYak ושלב איתור הפרויקטים האמיתי בפריסת RTL מלאה.", actions: "המתנה להשלמת האתחול המקומי או שינוי שפה.", design: "כיוון RTL, סדר השלבים, קריאות והיררכיה קומפקטית." },
  { name: "24-startup-narrow-en", locale: "en-US", mode: "startup", narrow: true, title: "Real startup pipeline — narrow window", description: "The same authoritative startup state at the supported narrow viewport, with every important label and step retained.", actions: "Wait for local startup or change language.", design: "No overlap, clipping, hidden operation, or required vertical scroll." },
];

function responseFor(url, method, mode) {
  const pathname = new URL(url).pathname;
  if (mode === "error" && pathname === "/health") return { status: 503, body: { detail: "LOCAL_ENGINE_UNAVAILABLE" } };
  if (pathname in setup) return { status: 200, body: setup[pathname] };
  if (pathname === "/projects" && method === "GET") return { status: 200, body: { projects: mode === "empty" || mode === "error" ? [] : [project(mode === "running" ? runningScan : completedScan)] } };
  if (pathname === "/projects/detect") return { status: 200, body: { selected_path: "/workspace/mellowyak-demo", repository_path: "/workspace/mellowyak-demo", suggested_name: "MellowYak Demo", git, languages: ["TypeScript", "Python", "Rust"], language_counts: { TypeScript: 92, Python: 54, Rust: 18 }, frameworks: ["React", "Tauri", "FastAPI"], tests: ["Vitest", "Pytest"], runtime_hints: ["Node.js", "Python"], candidate_files: 184, ignored_paths: 12, relationship_coverage: "bounded deterministic adapters", unsupported_coverage: "reported during initial scan", source_remains_local: true } };
  if (pathname === "/projects/project-1") return { status: 200, body: project(mode === "running" ? runningScan : completedScan) };
  if (pathname === "/projects/project-1/impact/summary") return { status: 200, body: { files_indexed: 172, languages: 3, language_counts: { TypeScript: 92, Python: 54, Rust: 18 }, direct_relationships: 426, tests_found: 24, sensitive_files: 1, unknown_references: 2, unsupported_files: 3, stale_relationships: 1 } };
  if (pathname === "/projects/project-1/changes/current") return { status: 200, body: change };
  if (pathname === "/projects/project-1/behavior-candidates") return { status: 200, body: { candidates: [{ id: "candidate-1", title: "Keeps impact ranking deterministic", source_type: "test_name", source_key: "tests/panel.spec.ts", status: "CANDIDATE", evidence: "none", verification: "not_configured", not_protected: true }] } };
  if (pathname.endsWith("/impact/paths")) return { status: 200, body: { paths: [{ id: "path-1", result_id: "r3", result: "tests/panel.spec.ts", impact_class: "transitive_static", depth: 2, steps: [{ from: "tests/panel.spec.ts", edge: "IMPORTS", to: "src/panel.tsx" }, { from: "src/panel.tsx", edge: "IMPORTS", to: "src/impact.ts" }] }] } };
  if (pathname.endsWith("/changes/change-1/impact")) {
    if (mode === "ready" && globalThis.reviewNav === "change-empty") return { status: 404, body: { detail: "IMPACT_NOT_ANALYZED" } };
    return { status: 200, body: impact };
  }
  if (pathname.endsWith("/context-receipt")) return { status: 200, body: receipt };
  if (pathname === "/projects/project-1/impact/search") return { status: 200, body: { results: [{ node: { type: "FILE", label: "src/impact.ts", relative_path: "src/impact.ts" }, relationships: [{ direction: "incoming", type: "IMPORTS", target_type: "FILE", target: "src/panel.tsx", target_path: "src/panel.tsx", provenance: "EXACT_PARSER", parser_adapter: "typescript", source_scan_revision: "scan-1", stale: false }, { direction: "outgoing", type: "CONTAINS", target_type: "SYMBOL", target: "analyzeImpact", target_path: "src/impact.ts", provenance: "EXACT_PARSER", parser_adapter: "typescript", source_scan_revision: "scan-1", stale: false }], recent_changes: ["change-1"] }] } };
  return { status: 200, body: {} };
}

async function waitForServer() {
  for (let attempt = 0; attempt < 80; attempt += 1) {
    try {
      const response = await fetch(baseUrl);
      if (response.ok) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("Vite review server did not start");
}

async function navigate(page, screen) {
  const he = screen.locale.startsWith("he");
  if (!screen.nav) return;
  if (screen.nav === "add" || screen.nav === "detect") {
    await page.getByRole("button", { name: he ? "הוספת הפרויקט הראשון" : "Add your first project" }).click();
    if (screen.nav === "detect") {
      await page.getByRole("button", { name: he ? "בחירת תיקיית פרויקט" : "Choose project folder" }).click();
      await page.getByText(he ? "הפרויקט שזוהה" : "Detected project").waitFor();
    }
    return;
  }
  await page.getByRole("button", { name: /MellowYak Demo/ }).click();
  if (screen.nav === "project") return;
  if (screen.nav.startsWith("change") || screen.nav === "receipt") {
    await page.getByRole("button", { name: he ? "שינויים" : "Changes" }).click();
    await page.getByText(he ? "קבצים שהשתנו" : "Changed Files").waitFor();
    if (screen.nav === "receipt") {
      await page.getByRole("button", { name: he ? "יצירת קבלה" : "Generate receipt" }).click();
      await page.getByText("mellowyak.context_receipt.v1").waitFor();
      await page.getByText(he ? "הצגת הסיבות וההקשר שלא נכלל" : "View why and excluded context").click();
    }
    return;
  }
  await page.getByRole("button", { name: he ? "השפעה" : "Impact" }).click();
  if (screen.nav === "impact") {
    await page.getByLabel(he ? "חיפוש קובץ, סמל, בדיקה או מודול" : "Find a file, symbol, test, or module").fill("impact.ts");
    await page.getByRole("button", { name: he ? "חיפוש" : "Search" }).click();
    await page.getByText("src/impact.ts").first().waitFor();
  }
}

function escapeHtml(value) {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

await mkdir(output, { recursive: true });
await copyFile(path.join(root, "assets", "brand", "mellowyak-app-icon.png"), path.join(output, "00-app-icon-master.png"));
await copyFile(path.join(root, "assets", "mascot", "sheet", "mellowyak-sheet.png"), path.join(output, "00-mascot-sheet.png"));
await copyFile(path.join(root, "assets", "mascot", "loading", "sheet", "mellowyak-loading-sheet.png"), path.join(output, "00-loading-sprite-sheet.png"));

const server = spawn("npm", ["run", "dev", "--", "--host", "127.0.0.1"], { cwd: desktop, stdio: ["ignore", "pipe", "pipe"] });
try {
  await waitForServer();
  const browser = await chromium.launch({ executablePath: chrome, headless: true });
  try {
    for (const screen of screens) {
      globalThis.reviewNav = screen.nav;
      const context = await browser.newContext({ locale: screen.locale, viewport: screen.narrow ? { width: 540, height: 900 } : { width: 1440, height: 1000 }, deviceScaleFactor: 1, colorScheme: "dark", reducedMotion: screen.narrow ? "reduce" : "no-preference" });
      await context.addInitScript(({ update }) => {
        let callbackId = 0;
        const callbacks = new Map();
        window.__TAURI_INTERNALS__ = {
          callbacks,
          transformCallback: (callback, once = false) => {
            callbackId += 1;
            callbacks.set(callbackId, { callback, once });
            return callbackId;
          },
          unregisterCallback: (id) => callbacks.delete(id),
          invoke: async (command) => {
            if (command === "engine_bootstrap") return { host: "127.0.0.1", port: 43123, token: "review-only" };
            if (command === "plugin:dialog|open") return "/workspace/mellowyak-demo";
            if (command === "plugin:updater|check") return update ? { rid: 1, currentVersion: "0.1.0", version: "0.2.0", rawJson: {} } : null;
            return null;
          },
        };
      }, { update: Boolean(screen.update) });
      const page = await context.newPage();
      await page.route("http://127.0.0.1:43123/**", async (route) => {
        if (screen.mode === "startup" && new URL(route.request().url()).pathname === "/projects") await new Promise((resolve) => setTimeout(resolve, 4_000));
        const result = responseFor(route.request().url(), route.request().method(), screen.mode);
        await route.fulfill({ status: result.status, contentType: "application/json", body: JSON.stringify(result.body) });
      });
      await page.goto(baseUrl, { waitUntil: screen.mode === "startup" ? "domcontentloaded" : "networkidle" });
      await page.getByText("MellowYak").first().waitFor();
      if (screen.mode === "startup") await page.getByText(screen.locale.startsWith("he") ? "איתור פרויקטים מקומיים…" : "Discovering local projects…").first().waitFor();
      await navigate(page, screen);
      await page.screenshot({ path: path.join(output, `${screen.name}.png`), fullPage: true });
      await context.close();
      process.stdout.write(`${screen.name}.png\n`);
    }

    const markdown = ["# MellowYak Phase 3 UI review", "", "All screenshots use synthetic public fixture data. No private repository path, credential, source content, or user data is included.", ""];
    for (const [index, screen] of screens.entries()) {
      markdown.push(`## ${index + 1}. ${screen.title}`, "", `![${screen.title}](${screen.name}.png)`, "", `- What is shown: ${screen.description}`, `- Available actions: ${screen.actions}`, `- Design review focus: ${screen.design}`, "");
    }
    await writeFile(path.join(output, "UI_REVIEW.md"), `${markdown.join("\n")}\n`);

    const sections = screens.map((screen, index) => `<section><h1>${index + 1}. ${escapeHtml(screen.title)}</h1><img src="${screen.name}.png"><dl><dt>מה רואים / What is shown</dt><dd>${escapeHtml(screen.description)}</dd><dt>אפשרויות / Actions</dt><dd>${escapeHtml(screen.actions)}</dd><dt>מוקד לבחינת עיצוב / Design review</dt><dd>${escapeHtml(screen.design)}</dd></dl></section>`).join("\n");
    const html = `<!doctype html><html lang="he" dir="rtl"><meta charset="utf-8"><style>@page{size:A4 landscape;margin:12mm}body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;color:#102334}section{page-break-after:always}h1{font-size:22px;margin:0 0 8px}img{display:block;max-width:100%;max-height:145mm;margin:0 auto 8px;border:1px solid #cad6dc;border-radius:8px}dl{display:grid;grid-template-columns:180px 1fr;gap:5px 12px;margin:0;font-size:11px}dt{font-weight:800}dd{margin:0}</style><body><section><h1>MellowYak — Phase 3 UI Review</h1><p>קטלוג מסכים מלא לצורך בדיקת עיצוב. כל הנתונים סינתטיים וכל טקסט המוצר נלקח ממפתחות התרגום של האפליקציה.</p><img src="00-app-icon-master.png"><p>English base + Hebrew RTL · 2026-08-24</p></section>${sections}</body></html>`;
    await writeFile(path.join(output, "UI_REVIEW.html"), html);
    const pdfPage = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    await pdfPage.goto(`file://${path.join(output, "UI_REVIEW.html")}`, { waitUntil: "networkidle" });
    await pdfPage.pdf({ path: path.join(output, "MellowYak-Phase-3-UI-Review.pdf"), format: "A4", landscape: true, printBackground: true, margin: { top: "12mm", right: "12mm", bottom: "12mm", left: "12mm" } });
    await pdfPage.close();
  } finally {
    await browser.close();
  }
} finally {
  server.kill("SIGTERM");
}
