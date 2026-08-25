#!/usr/bin/env node

import { spawn } from "node:child_process";
import { access, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { chromium } from "../apps/desktop/node_modules/playwright-core/index.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const desktop = path.join(root, "apps", "desktop");
const delivery = path.join(root, "docs", "phase-10-delivery");
const screenshots = path.join(delivery, "screenshots");
const port = Number(process.env.MELLOWYAK_CAPTURE_PORT ?? 1430);
const baseUrl = `http://127.0.0.1:${port}`;
const generatedAt = "2026-08-25T15:00:00+03:00";

const states = [
  "first-run-welcome", "first-run-choice-unselected", "first-run-demo-selected",
  "first-run-background-settings", "first-run-complete-demo", "home-no-confirmed-issue",
  "home-needs-attention", "project-overview-healthy", "project-overview-ready-with-limits",
  "project-activity-timeline", "episode-detail", "check-passed-no-regression",
  "behaviors-known-good", "regression-friendly", "regression-technical",
  "repair-workspace-operational", "candidate-validation-progress", "candidate-validated",
  "apply-confirmation", "apply-transaction-progress", "applied-and-verified",
  "rolled-back-safely", "disconnected-projects", "reconnect-identity-preview",
  "project-mismatch-alert", "diagnostics-real-data", "self-test-running",
  "self-test-passed", "support-bundle-manifest", "update-status",
  "activity-mode-settings", "native-tray-preview", "hebrew-home",
  "hebrew-project-overview", "hebrew-regression", "hebrew-diagnostics",
];

const titles = {
  "first-run-welcome": "First-run welcome",
  "first-run-choice-unselected": "Choose how to begin — unselected",
  "first-run-demo-selected": "Demo Lab selected",
  "first-run-background-settings": "Background behavior",
  "first-run-complete-demo": "Demo Lab ready",
  "home-no-confirmed-issue": "Home — no confirmed issue",
  "home-needs-attention": "Home — attention required",
  "project-overview-healthy": "Project Overview — current evidence",
  "project-overview-ready-with-limits": "Project Overview — ready with limits",
  "project-activity-timeline": "Project activity timeline",
  "episode-detail": "Episode detail",
  "check-passed-no-regression": "Check passed — no regression",
  "behaviors-known-good": "Known-good behavior",
  "regression-friendly": "Regression detail — friendly",
  "regression-technical": "Regression detail — technical evidence",
  "repair-workspace-operational": "Repair Workspace",
  "candidate-validation-progress": "Candidate validation in progress",
  "candidate-validated": "Candidate validated",
  "apply-confirmation": "Apply confirmation",
  "apply-transaction-progress": "Apply transaction progress",
  "applied-and-verified": "Applied and verified",
  "rolled-back-safely": "Rolled back safely",
  "disconnected-projects": "Disconnected projects",
  "reconnect-identity-preview": "Reconnect identity preview",
  "project-mismatch-alert": "Project mismatch",
  "diagnostics-real-data": "Diagnostics Center",
  "self-test-running": "Product Self-Test running",
  "self-test-passed": "Product Self-Test passed",
  "support-bundle-manifest": "Support bundle manifest",
  "update-status": "Update status",
  "activity-mode-settings": "Activity mode settings",
  "native-tray-preview": "Native menu preview",
  "hebrew-home": "Hebrew RTL Home",
  "hebrew-project-overview": "Hebrew RTL Project Overview",
  "hebrew-regression": "Hebrew RTL Regression Detail",
  "hebrew-diagnostics": "Hebrew RTL Diagnostics",
};

function metadata(state, index) {
  const preview = state === "native-tray-preview";
  const isFirstRun = state.startsWith("first-run");
  const purpose = isFirstRun
    ? "Show the accessible, persisted path from welcome to the selected local destination."
    : state.startsWith("hebrew-")
      ? "Verify the same operational product surface in Hebrew RTL."
      : "Show the current product state, its evidence, limitations, and safe next action.";
  const actions = state.includes("regression") ? "Review evidence, run again, or create a Repair Workspace."
    : state.includes("diagnostics") ? "Run Self-Test, export support information, or copy redacted diagnostics."
      : state.includes("apply") ? "Review the explicit source-bound transaction and continue only by deliberate action."
        : "Use the visible operational controls to continue to exact local context.";
  return {
    index,
    slug: state,
    title: titles[state],
    purpose,
    state: "Deterministic synthetic Phase 10 state rendered through the production component.",
    data_source: "Explicit screenshot-test fixture; no real project or user data.",
    actions,
    known_facts: "Only values visible in the bounded synthetic evidence are claimed.",
    unknowns: "Root cause, complete blast radius, unexecuted checks, and untested platforms remain unclaimed.",
    next_step: "Follow the primary visible action or open technical details when needed.",
    source_modified: false,
    surface_kind: preview ? "test-only native preview" : "real operational UI with synthetic capture data",
    locale: state.startsWith("hebrew-") ? "he-IL" : "en-US",
  };
}

const rows = states.map(metadata);

function escapeHtml(value) {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

function markdown() {
  const lines = [
    "# MellowYak Phase 10 Screen Guide", "",
    "All 36 screens use deterministic synthetic capture data. No real project, private source, evidence bytes, prompt, credential, provider data, or absolute user path is included.", "",
  ];
  for (const row of rows) {
    const number = String(row.index).padStart(2, "0");
    lines.push(
      `## ${number}. ${row.title}`, "",
      `![${row.title}](screenshots/${number}-${row.slug}.png)`, "",
      `- Purpose: ${row.purpose}`,
      `- Displayed state: ${row.state}`,
      `- Data source: ${row.data_source}`,
      `- Available actions: ${row.actions}`,
      `- Known facts: ${row.known_facts}`,
      `- Unknowns: ${row.unknowns}`,
      `- Expected next step: ${row.next_step}`,
      `- Source modified: ${row.source_modified ? "Yes" : "No"}`,
      `- Surface classification: ${row.surface_kind}.`, "",
    );
  }
  return `${lines.join("\n").trimEnd()}\n`;
}

function html() {
  const sections = rows.map((row) => {
    const number = String(row.index).padStart(2, "0");
    return `<section><h1>${number}. ${escapeHtml(row.title)}</h1><img src="screenshots/${number}-${escapeHtml(row.slug)}.png" alt="${escapeHtml(row.title)}"><dl><dt>Purpose</dt><dd>${escapeHtml(row.purpose)}</dd><dt>State</dt><dd>${escapeHtml(row.state)}</dd><dt>Data source</dt><dd>${escapeHtml(row.data_source)}</dd><dt>Actions</dt><dd>${escapeHtml(row.actions)}</dd><dt>Known</dt><dd>${escapeHtml(row.known_facts)}</dd><dt>Unknowns</dt><dd>${escapeHtml(row.unknowns)}</dd><dt>Next</dt><dd>${escapeHtml(row.next_step)}</dd><dt>Source modified</dt><dd>No</dd><dt>Surface</dt><dd>${escapeHtml(row.surface_kind)}</dd></dl></section>`;
  }).join("\n");
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>MellowYak Phase 10 Screen Guide</title><style>@page{size:A4 landscape;margin:8mm}*{box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;color:#102334;margin:0}section{page-break-after:always}h1{font-size:19px;margin:0 0 5px}img{display:block;max-width:100%;max-height:128mm;margin:0 auto 5px;border:1px solid #cad6dc;border-radius:8px}dl{display:grid;grid-template-columns:125px 1fr;gap:2px 9px;margin:0;font-size:8.5px;line-height:1.18}dt{font-weight:800}dd{margin:0}.cover{display:grid;place-items:center;text-align:center;min-height:175mm}.cover h1{font-size:34px}.cover p{max-width:760px;font-size:15px}</style></head><body><section class="cover"><div><h1>MellowYak Phase 10</h1><h2>Product Truth and Daily Workflow</h2><p>36 deterministic synthetic operational screens · English and Hebrew RTL · 2026-08-25</p><p>No real project or private user data is included.</p></div></section>${sections}</body></html>`;
}

async function findBrowser() {
  const candidates = [process.env.MELLOWYAK_CHROMIUM_PATH, "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Chromium.app/Contents/MacOS/Chromium", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"].filter(Boolean);
  for (const candidate of candidates) {
    try { await access(candidate); return candidate; } catch { /* continue */ }
  }
  throw new Error("No supported local Chromium browser found");
}

async function waitForServer() {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    try { if ((await fetch(baseUrl)).ok) return; } catch { /* starting */ }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("Phase 10 capture server did not start");
}

await mkdir(screenshots, { recursive: true });
const browserPath = await findBrowser();
const server = spawn("npm", ["run", "dev", "--", "--host", "127.0.0.1", "--port", String(port), "--strictPort"], { cwd: desktop, stdio: ["ignore", "pipe", "pipe"] });
let serverOutput = "";
server.stdout.on("data", (chunk) => { serverOutput += chunk.toString(); });
server.stderr.on("data", (chunk) => { serverOutput += chunk.toString(); });

try {
  await waitForServer();
  const browser = await chromium.launch({ executablePath: browserPath, headless: true });
  try {
    for (const row of rows) {
      const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1, colorScheme: "dark", reducedMotion: "reduce" });
      await context.addInitScript(() => {
        let callbackId = 0;
        const callbacks = new Map();
        window.__TAURI_INTERNALS__ = {
          callbacks,
          transformCallback: (callback, once = false) => { callbackId += 1; callbacks.set(callbackId, { callback, once }); return callbackId; },
          unregisterCallback: (id) => callbacks.delete(id),
          invoke: async (command) => {
            if (command === "engine_bootstrap") return { host: "127.0.0.1", port: 43130, token: "phase10-synthetic-capture" };
            if (command === "get_start_at_login") return false;
            if (command.includes("listen")) return 1;
            return null;
          },
        };
      });
      const page = await context.newPage();
      await page.route("http://127.0.0.1:43130/**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "{}" }));
      await page.goto(`${baseUrl}/?phase10State=${row.slug}`, { waitUntil: "networkidle" });
      await page.locator(`[data-phase10-state="${row.slug}"]`).waitFor();
      if (row.locale === "he-IL") await page.locator('main[dir="rtl"]').waitFor();
      const filename = `${String(row.index).padStart(2, "0")}-${row.slug}.png`;
      await page.screenshot({ path: path.join(screenshots, filename), fullPage: true });
      await context.close();
      process.stdout.write(`${filename}\n`);
    }
    const manifest = {
      schema: "mellowyak.phase10.screenshot-delivery.v1",
      generated_at: generatedAt,
      fixture: "deterministic_synthetic_public",
      screenshots: rows.map((row) => ({ ...row, file: `screenshots/${String(row.index).padStart(2, "0")}-${row.slug}.png` })),
    };
    await writeFile(path.join(delivery, "PHASE_10_SCREEN_GUIDE.md"), markdown());
    await writeFile(path.join(delivery, "PHASE_10_SCREEN_GUIDE.html"), html());
    await writeFile(path.join(delivery, "PHASE_10_SCREENSHOT_MANIFEST.json"), `${JSON.stringify(manifest, null, 2)}\n`);
    const pdfPage = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await pdfPage.goto(`file://${path.join(delivery, "PHASE_10_SCREEN_GUIDE.html")}`, { waitUntil: "networkidle" });
    await pdfPage.pdf({ path: path.join(delivery, "MellowYak-Phase-10-Screen-Guide.pdf"), format: "A4", landscape: true, printBackground: true, margin: { top: "8mm", right: "8mm", bottom: "8mm", left: "8mm" } });
    await pdfPage.close();
  } finally {
    await browser.close();
  }
} catch (reason) {
  if (serverOutput) process.stderr.write(serverOutput);
  throw reason;
} finally {
  server.kill("SIGTERM");
}
