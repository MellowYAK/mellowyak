#!/usr/bin/env node

import { spawn } from "node:child_process";
import { access, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { chromium } from "../apps/desktop/node_modules/playwright-core/index.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const desktop = path.join(root, "apps", "desktop");
const delivery = path.join(root, "docs", "phase-9-delivery");
const screenshots = path.join(delivery, "screenshots");
const port = Number(process.env.MELLOWYAK_CAPTURE_PORT ?? 1429);
const baseUrl = `http://127.0.0.1:${port}`;
const generatedAt = "2026-08-25T12:00:00+03:00";

const browserCandidates = [
  process.env.MELLOWYAK_CHROMIUM_PATH,
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
].filter(Boolean);

const rows = [
  ["first-run-welcome", "First-run welcome", "Introduce the local-first Technical Preview.", "A fresh isolated installation has not completed onboarding.", "Continue to project choice.", "No account, model, Docker, or cloud is required.", "No project has been selected.", "Review the choices.", false],
  ["first-run-choose-project-or-demo", "Choose project or Demo Lab", "Offer a real local folder or a synthetic disposable demo.", "No selection is persisted yet.", "Select a real project or Demo Lab.", "Both choices remain local.", "A real project is intentionally not used in this capture.", "Choose Demo Lab for safe evaluation.", false],
  ["first-run-background-and-privacy", "Background and privacy", "Explain close-to-tray and optional local notifications.", "Background behavior awaits confirmation.", "Continue after reviewing privacy behavior.", "Routes contain identifiers, not source or paths.", "OS notification permission is not granted by this screenshot.", "Continue to summary.", false],
  ["first-run-complete", "First-run complete", "Confirm saved first-run choices.", "Synthetic Demo Lab is selected.", "Finish setup.", "The choice persists and can be replayed from Settings.", "No real project is attached.", "Open the disposable Demo Lab.", false],
  ["disconnected-projects", "Disconnected projects", "Review retained MellowYak history for unavailable source folders.", "A synthetic project is disconnected.", "Reconnect, locate, review history, or delete MellowYak data.", "Source is not moved or copied.", "The correct replacement folder is not yet selected.", "Locate the original project identity.", false],
  ["reconnect-project", "Reconnect project", "Reconnect after exact identity validation.", "The prior project remains retained locally.", "Choose a candidate source folder.", "History remains project-bound.", "Identity has not yet been accepted.", "Validate the folder.", false],
  ["relocate-project", "Relocate project", "Attach retained history to the same project at a new path.", "A safe relocation is being reviewed.", "Locate the matching folder.", "MellowYak never moves or deletes source.", "The final identity decision is not shown.", "Complete identity comparison.", false],
  ["relocate-mismatch", "Relocation mismatch", "Stop cross-project evidence attachment.", "Selected folder does not match retained project identity.", "Choose another folder or create a new project.", "Old evidence remains untouched.", "The user may still explicitly add the folder as new.", "Return to folder selection.", false],
  ["dynamic-tray-monitoring", "Tray monitoring", "Show privacy-safe global monitoring status.", "Two active projects, one paused, no alerts.", "Open MellowYak, alerts, or project actions.", "No full paths or source content are shown.", "Native menu rendering differs by OS.", "Continue monitoring.", false],
  ["dynamic-tray-attention", "Tray attention", "Surface critical local attention without private detail.", "Three unread alerts include one critical alert.", "Open Alerts for exact local context.", "Only counts and severity are exposed.", "The root cause is not claimed.", "Review the local alert.", false],
  ["dynamic-tray-project-menu", "Tray project menu", "Expose bounded per-project controls.", "Synthetic project submenu is open.", "Open, pause/resume, or mute/unmute.", "The menu uses project identity only.", "Native submenu appearance is platform-specific.", "Choose a project action.", false],
  ["notification-opened-context", "Notification context", "Show safe routing to exact local context.", "A validated project-bound route opened in the existing instance.", "Review the destination or return to Alerts.", "No token, source, or full path is in the route.", "A real macOS click still requires OS permission.", "Review the local state.", false],
  ["diagnostics", "Diagnostics Center", "Inspect safe desktop, engine, storage, and platform health.", "Local diagnostics are available.", "Run Self-Test, storage integrity, support export, or copy safe data.", "Bearer token and data-root path are redacted.", "External platform signing is not inferred.", "Run a chosen diagnostic.", false],
  ["support-bundle", "Redacted support bundle", "Export bounded local diagnostics.", "A redacted bundle is ready.", "Export or inspect the manifest.", "Source, evidence bytes, secrets, and absolute paths are excluded.", "The bundle does not diagnose every OS issue.", "Share only after reviewing the manifest.", false],
  ["product-self-test", "Product Self-Test", "Run the synthetic core acceptance loop.", "Disposable local validation is available.", "Run and export the result.", "Executed steps are reported truthfully.", "It does not certify untested platforms.", "Run the packaged test.", false],
  ["update-check", "Update check", "Show the signed updater status surface.", "A local check can be requested.", "Check for an update.", "Production public-key verification remains configured.", "No public higher release is available in this run.", "Use the local signed fixture.", false],
  ["update-signature-rejected", "Update signature rejected", "Explain a cryptographic rejection safely.", "Tampered or wrongly signed fixture is blocked.", "Return to current version or retry later.", "Current application and data are preserved.", "Production update remains untested without a real release.", "Keep the installed version.", false],
  ["package-acceptance", "Package acceptance", "Summarize current packaged validation.", "Package checks have deterministic local evidence.", "Inspect the evidence report.", "Phase 8 repair safety is rerun against the package.", "Unsupported platforms remain unverified.", "Review exact statuses.", false],
  ["battery-saver", "Battery saver", "Reduce optional activity without weakening core snapshot correctness.", "Battery saver is selected.", "Return to Normal or Reduced activity.", "File observation, snapshots, and critical alerts remain active.", "Deep runtime work may be deferred.", "Review listed limitations.", false],
  ["technical-preview-readiness", "Technical Preview readiness", "Show release-readiness boundaries.", "Current-platform evidence is assembled.", "Review checklist and known limitations.", "No public release or push occurred.", "Signing and other platforms remain externally dependent.", "Follow the real-project guide later.", false],
  ["hebrew-first-run", "Hebrew RTL first run", "Verify first-run copy and layout in Hebrew RTL.", "Synthetic onboarding is shown in Hebrew.", "Continue through the same local flow.", "Translation keys drive the visible text.", "No native OS permission is implied.", "Continue in RTL.", false],
  ["hebrew-disconnected-projects", "Hebrew RTL disconnected projects", "Verify retained-project controls in Hebrew RTL.", "A synthetic disconnected project is shown.", "Reconnect or locate the folder.", "Technical identifiers remain LTR.", "Identity is not silently assumed.", "Validate the selected folder.", false],
  ["hebrew-diagnostics", "Hebrew RTL diagnostics", "Verify safe diagnostics in Hebrew RTL.", "Synthetic diagnostic readiness is shown.", "Run local diagnostic actions.", "Visible copy comes from Hebrew translation keys.", "Signing cannot be inferred from UI.", "Review the evidence.", false],
  ["hebrew-notification-context", "Hebrew RTL notification context", "Verify safe activation context in Hebrew RTL.", "A synthetic validated route is shown.", "Open the local destination.", "Identifiers remain bounded and LTR.", "A real OS click is not visually automated.", "Review the destination.", false],
];

function escapeHtml(value) {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

function markdown() {
  const lines = ["# MellowYak Phase 9 Screen Guide", "", "All screens use deterministic synthetic data. No real project, private source, user path, credential, prompt, provider data, or evidence bytes are included.", ""];
  rows.forEach(([slug, title, purpose, state, actions, known, unknown, next, modified], index) => {
    lines.push(`## ${String(index).padStart(2, "0")}. ${title}`, "", `![${title}](screenshots/${String(index).padStart(2, "0")}-${slug}.png)`, "", `- Purpose: ${purpose}`, `- Displayed state: ${state}`, "- Data source: deterministic synthetic Phase 9 capture fixture rendered locally.", `- Available actions: ${actions}`, `- Known facts: ${known}`, `- Unknowns: ${unknown}`, `- Expected next step: ${next}`, "- Privacy: no source, evidence bytes, secrets, provider data, or absolute user paths.", `- Source modified: ${modified ? "Yes — synthetic fixture only." : "No."}`, "");
  });
  return `${lines.join("\n").trimEnd()}\n`;
}

function html() {
  const sections = rows.map(([slug, title, purpose, state, actions, known, unknown, next, modified], index) => `<section><h1>${String(index).padStart(2, "0")}. ${escapeHtml(title)}</h1><img src="screenshots/${String(index).padStart(2, "0")}-${escapeHtml(slug)}.png" alt="${escapeHtml(title)}"><dl><dt>Purpose</dt><dd>${escapeHtml(purpose)}</dd><dt>State</dt><dd>${escapeHtml(state)}</dd><dt>Data source</dt><dd>Deterministic synthetic Phase 9 capture fixture.</dd><dt>Actions</dt><dd>${escapeHtml(actions)}</dd><dt>Known</dt><dd>${escapeHtml(known)}</dd><dt>Unknowns</dt><dd>${escapeHtml(unknown)}</dd><dt>Next</dt><dd>${escapeHtml(next)}</dd><dt>Privacy</dt><dd>No private source, evidence bytes, secrets, provider data, or absolute user paths.</dd><dt>Source modified</dt><dd>${modified ? "Yes — synthetic fixture only." : "No."}</dd></dl></section>`).join("\n");
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>MellowYak Phase 9 Screen Guide</title><style>@page{size:A4 landscape;margin:9mm}*{box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;color:#102334;margin:0}section{page-break-after:always}h1{font-size:20px;margin:0 0 6px}img{display:block;max-width:100%;max-height:126mm;margin:0 auto 6px;border:1px solid #cad6dc;border-radius:8px}dl{display:grid;grid-template-columns:130px 1fr;gap:3px 10px;margin:0;font-size:9px;line-height:1.2}dt{font-weight:800}dd{margin:0}.cover{display:grid;place-items:center;text-align:center;min-height:170mm}.cover h1{font-size:34px}.cover p{max-width:760px;font-size:15px}</style></head><body><section class="cover"><div><h1>MellowYak Phase 9</h1><h2>Technical Preview Readiness</h2><p>Deterministic synthetic delivery catalog · English base + Hebrew RTL · 2026-08-25</p><p>No real project or private user data is included.</p></div></section>${sections}</body></html>`;
}

async function findBrowser() {
  for (const candidate of browserCandidates) {
    try { await access(candidate); return candidate; } catch { /* continue */ }
  }
  throw new Error("No supported local Chromium browser found");
}

async function waitForServer() {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    try { if ((await fetch(baseUrl)).ok) return; } catch { /* starting */ }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("Phase 9 capture server did not start");
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
    for (let index = 0; index < rows.length; index += 1) {
      const [slug] = rows[index];
      const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1, colorScheme: "dark", reducedMotion: "reduce" });
      await context.addInitScript(() => {
        let callbackId = 0;
        const callbacks = new Map();
        window.__TAURI_INTERNALS__ = {
          callbacks,
          transformCallback: (callback, once = false) => { callbackId += 1; callbacks.set(callbackId, { callback, once }); return callbackId; },
          unregisterCallback: (id) => callbacks.delete(id),
          invoke: async (command) => {
            if (command === "engine_bootstrap") return { host: "127.0.0.1", port: 43129, token: "phase9-synthetic-capture" };
            if (command === "plugin:updater|check") return null;
            if (command.includes("listen")) return 1;
            if (command === "take_pending_route") return null;
            if (command === "get_start_at_login") return false;
            return null;
          },
        };
      });
      const page = await context.newPage();
      await page.route("http://127.0.0.1:43129/**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "{}" }));
      await page.goto(`${baseUrl}/?phase9State=${slug}`, { waitUntil: "networkidle" });
      await page.locator(`[data-phase9-state="${slug}"]`).waitFor();
      if (String(slug).startsWith("hebrew-")) await page.locator('main[dir="rtl"]').waitFor();
      const filename = `${String(index).padStart(2, "0")}-${slug}.png`;
      await page.screenshot({ path: path.join(screenshots, filename), fullPage: true });
      await context.close();
      process.stdout.write(`${filename}\n`);
    }
    const manifest = {
      schema: "mellowyak.phase9.screenshot-delivery.v1",
      generated_at: generatedAt,
      fixture: "deterministic_synthetic_public",
      screenshots: rows.map(([slug, title, purpose, state, actions, known, unknown, next, modified], index) => ({
        file: `screenshots/${String(index).padStart(2, "0")}-${slug}.png`, locale: String(slug).startsWith("hebrew-") ? "he-IL" : "en-US", title, purpose, state, data_source: "deterministic synthetic Phase 9 capture fixture rendered locally", actions, known_facts: known, unknowns: unknown, next_step: next, privacy_status: "No source, evidence bytes, secrets, provider data, or absolute user paths.", source_modified: modified,
      })),
    };
    await writeFile(path.join(delivery, "PHASE_9_SCREEN_GUIDE.md"), markdown());
    await writeFile(path.join(delivery, "PHASE_9_SCREEN_GUIDE.html"), html());
    await writeFile(path.join(delivery, "PHASE_9_SCREENSHOT_MANIFEST.json"), `${JSON.stringify(manifest, null, 2)}\n`);
    const pdfPage = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    await pdfPage.goto(`file://${path.join(delivery, "PHASE_9_SCREEN_GUIDE.html")}`, { waitUntil: "networkidle" });
    await pdfPage.pdf({ path: path.join(delivery, "MellowYak-Phase-9-Screen-Guide.pdf"), format: "A4", landscape: true, printBackground: true, margin: { top: "9mm", right: "9mm", bottom: "9mm", left: "9mm" } });
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
