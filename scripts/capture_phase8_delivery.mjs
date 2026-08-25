#!/usr/bin/env node

import { spawn } from "node:child_process";
import { access, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { chromium } from "../apps/desktop/node_modules/playwright-core/index.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const desktop = path.join(root, "apps", "desktop");
const delivery = path.join(root, "docs", "phase-8-delivery");
const screenshots = path.join(delivery, "screenshots");
const port = Number(process.env.MELLOWYAK_CAPTURE_PORT ?? 1428);
const baseUrl = `http://127.0.0.1:${port}`;
const generatedAt = "2026-08-25T08:00:00+03:00";

const browserCandidates = [
  process.env.MELLOWYAK_CHROMIUM_PATH,
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
].filter(Boolean);

async function findBrowser() {
  for (const candidate of browserCandidates) {
    try { await access(candidate); return candidate; } catch { /* use the next installed browser */ }
  }
  throw new Error("No supported local Chromium browser was found. Set MELLOWYAK_CHROMIUM_PATH.");
}

const rows = [
  ["repair-workspace-ready", "Repair Workspace ready", "Review an isolated working copy before edits.", "Workspace is materialized from the exact failing source identity.", "Open, inspect, refresh, export, or abandon the working copy.", "Workspace and base manifest identities are known.", "No repair has been validated.", "Edit only the isolated working copy.", false],
  ["workspace-changes", "Workspace changes", "Review detected changes without touching live source.", "Three deterministic synthetic file changes are detected.", "Refresh, inspect files, restore a workspace file, or create a candidate.", "Paths, operations, sizes, and workspace identity are known.", "Behavioral correctness is not yet known.", "Create and review a bounded candidate repair.", false],
  ["candidate-patch-preview", "Candidate patch preview", "Summarize the bounded candidate manifest.", "One add and two modifications form candidate revision R3.", "View files/diffs, export, exclude, validate, or abandon.", "Exact candidate and expected live digests are bound.", "Live success is not implied.", "Review warnings and start workspace validation.", false],
  ["candidate-diff", "Candidate diff", "Inspect a bounded text diff.", "A synthetic checkout repair diff is visible.", "Review the diff or return to the candidate summary.", "The preview is candidate-bound and size-bounded.", "Binary content and omitted lines are not inferred.", "Validate the exact candidate revision.", false],
  ["validation-plan", "Candidate validation plan", "Show required checks before execution.", "Original failed probe is ordered first, followed by impacted and runtime checks.", "Start validation or inspect technical bindings.", "Required order, runtime identity, and policy are known.", "Unsupported external state may still require review.", "Run validation in the isolated workspace.", false],
  ["candidate-validating", "Candidate validating", "Show bounded workspace verification in progress.", "Required checks are running against the candidate-bound working copy.", "Inspect progress or cancel validation.", "Workspace processes and exact candidate identity are tracked.", "Final validation outcome is not known yet.", "Wait for all required checks to finish.", false],
  ["validation-failed", "Validation failed", "Block Apply when any required check fails.", "The original protected-behavior probe failed in the working copy.", "Inspect evidence, edit the workspace, refresh, or export.", "Failure is preserved and Apply is disabled.", "Root cause is not claimed.", "Make a smaller relevant edit and validate a new revision.", false],
  ["candidate-validated", "Candidate validated", "Present a candidate that passed every required workspace check.", "Candidate R3 is validated against exact workspace/runtime identities.", "Prepare Apply, export, or inspect technical evidence.", "All required workspace checks passed.", "The live project has not yet been verified.", "Prepare a fresh live-source preflight.", false],
  ["apply-blocked-stale-source", "Apply blocked — live project changed", "Prevent writes when live source no longer matches.", "Preflight found a stale live source identity.", "Recreate the workspace, export the candidate, or cancel.", "No live path was written.", "No automatic merge is attempted.", "Start again from the latest live source.", false],
  ["apply-confirmation", "Apply confirmation", "Require deliberate confirmation for one exact validated candidate.", "Candidate, source identity, safety point, checks, and rollback behavior are shown.", "Confirm once, inspect details, export, or cancel.", "Nonce is candidate/project/source-bound and short-lived.", "Cross-platform atomicity is not claimed.", "Confirm only after reviewing affected paths.", false],
  ["safety-snapshot-created", "Safety snapshot created", "Show the fresh pinned pre-apply safety point.", "Safety snapshot and durable transaction journal exist before writes.", "Inspect journal or continue the confirmed transaction.", "Exact affected-path digests are captured.", "Post-apply success is not yet known.", "Proceed with hash-preconditioned writes.", false],
  ["applying", "Applying changes", "Show bounded journaled writes in progress.", "Prepared temporary files and atomic replacements are being journaled.", "Inspect technical progress.", "The transaction is bound to the confirmed candidate.", "A final live verification has not run.", "Complete writes, then run fresh live verification.", true],
  ["post-apply-verification", "Post-apply verification", "Separate workspace PASS from fresh live verification.", "A new live source identity and fresh required checks are running.", "Inspect checks and transaction evidence.", "Workspace evidence is not reused as live evidence.", "Commit outcome remains pending.", "Commit only if the live Completion Gate passes.", true],
  ["applied-and-verified", "Applied and verified", "Show a committed repair after fresh live verification.", "Required live checks passed and the transaction committed.", "Inspect evidence or optionally create a new known-good milestone.", "Original failure, candidate validation, and live evidence remain distinct.", "No milestone was created automatically.", "Decide whether to save a new known-good milestone.", true],
  ["post-apply-failed", "Post-apply verification failed", "Explain why a written candidate cannot remain applied.", "A required live check failed after Apply.", "Inspect evidence while automatic rollback begins.", "The failure is transaction-bound and preserved.", "Repair success is not claimed.", "Wait for byte-verified rollback.", true],
  ["rolled-back-safely", "Rolled back safely", "Confirm byte-identical transaction rollback.", "Only paths changed by this Apply were restored from its safety snapshot.", "Inspect rollback evidence or keep/export the candidate.", "Affected bytes match the pre-apply safety point.", "The original regression remains unresolved.", "Revise the candidate in an isolated workspace.", false],
  ["recovery-required", "Recovery required", "Stop writes when recovery safety cannot be proven.", "An incomplete transaction needs manual recovery.", "Create/open a Recovery Bundle or inspect exact unresolved paths.", "Further writes are blocked and a critical local state is raised.", "Automatic recovery success is not claimed.", "Follow the Recovery Bundle instructions.", false],
  ["portable-repair-package", "Portable Repair Package", "Export bounded local context for a human or external tool.", "Selected files, evidence references, validation plan, and unknowns are ready.", "Review the manifest and export locally.", "Secrets, absolute paths, provider data, and full-project dumps are excluded.", "The package may not be independently runnable.", "Return edits to the isolated Repair Workspace.", false],
  ["demo-lab", "Demo Lab", "Create a disposable synthetic project for guided review.", "The local-only demo is ready to be created in a selected folder.", "Create, reset, inject scenarios, or run the self-test.", "The fixture is offline, dependency-light, and explicitly synthetic.", "No real project is selected or mutated.", "Create the disposable demo project.", false],
  ["demo-confirmed-regression", "Demo confirmed regression", "Demonstrate deterministic prior-pass/current-fail confirmation.", "The synthetic checkout behavior fails reproducibly.", "Create bad/valid candidates, inspect evidence, or reset.", "The regression is synthetic and source-bound.", "Root cause is not inferred by AI.", "Create an isolated demo Repair Workspace.", false],
  ["demo-valid-repair", "Demo valid repair", "Demonstrate a candidate that passed workspace validation.", "The synthetic good candidate is eligible for Apply preparation.", "Prepare Apply, simulate stale source, or reset.", "All required workspace checks passed.", "Live verification has not yet run.", "Confirm a disposable demo Apply.", false],
  ["product-self-test-running", "Product Self-Test running", "Exercise the product loop only in disposable storage.", "Deterministic self-test steps are running locally.", "Inspect step progress or wait for completion.", "Real projects and external network are excluded.", "Final status is not known until every executed step finishes.", "Wait for PASS, PARTIAL, or FAILED.", false],
  ["product-self-test-passed", "Product Self-Test passed", "Show completed disposable end-to-end evidence.", "All executed deterministic self-test steps passed.", "Export the report or open local diagnostics.", "Apply, rollback, journal, hash, cleanup, and no-network checks ran.", "This does not certify every operating system.", "Use the morning guide for manual product acceptance.", false],
  ["hebrew-candidate-validated", "Hebrew RTL — validated candidate", "Verify the validated-candidate surface in Hebrew RTL.", "The same deterministic candidate is displayed with mirrored layout.", "Prepare Apply, export, or inspect evidence.", "Translation-key-only UI and technical LTR identifiers coexist.", "Live success remains unverified.", "Continue to deliberate confirmation.", false],
  ["hebrew-apply-confirmation", "Hebrew RTL — Apply confirmation", "Verify deliberate confirmation in Hebrew RTL.", "Safety, rollback, and affected-path copy is translated and mirrored.", "Confirm once, inspect, export, or cancel.", "The confirmation remains candidate/source bound.", "Cross-platform guarantees remain limited.", "Confirm only after path review.", false],
  ["hebrew-rollback-safe", "Hebrew RTL — rolled back safely", "Verify the safe rollback result in Hebrew RTL.", "Affected demo bytes were restored to the safety point.", "Inspect evidence or revise the candidate.", "Only transaction paths were restored.", "The original regression remains unresolved.", "Return to the isolated workspace.", false],
];

function escapeHtml(value) {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

function guideMarkdown() {
  const lines = ["# MellowYak Phase 8 Screen Guide", "", "All screens use deterministic synthetic data. No private source, user path, credentials, prompt history, provider data, runtime evidence, or real project content is included.", ""];
  rows.forEach(([slug, title, purpose, state, actions, known, unknown, next, modified], index) => {
    lines.push(`## ${index + 1}. ${title}`, "", `![${title}](screenshots/${String(index).padStart(2, "0")}-${slug}.png)`, "", `- Purpose: ${purpose}`, `- Displayed state: ${state}`, "- Source of data: deterministic synthetic Phase 8 review fixture rendered locally by the desktop UI.", `- Available actions: ${actions}`, `- Known facts: ${known}`, `- Unknowns: ${unknown}`, `- Expected next step: ${next}`, `- Live source modified: ${modified ? "Yes — only within the synthetic transaction shown." : "No."}`, "");
  });
  return `${lines.join("\n").trimEnd()}\n`;
}

function guideHtml() {
  const sections = rows.map(([slug, title, purpose, state, actions, known, unknown, next, modified], index) => `<section><h1>${index + 1}. ${escapeHtml(title)}</h1><img src="screenshots/${String(index).padStart(2, "0")}-${escapeHtml(slug)}.png" alt="${escapeHtml(title)}"><dl><dt>Purpose</dt><dd>${escapeHtml(purpose)}</dd><dt>Displayed state</dt><dd>${escapeHtml(state)}</dd><dt>Source</dt><dd>Deterministic synthetic Phase 8 fixture rendered locally.</dd><dt>Actions</dt><dd>${escapeHtml(actions)}</dd><dt>Known facts</dt><dd>${escapeHtml(known)}</dd><dt>Unknowns</dt><dd>${escapeHtml(unknown)}</dd><dt>Next step</dt><dd>${escapeHtml(next)}</dd><dt>Live source modified</dt><dd>${modified ? "Yes — synthetic transaction only." : "No."}</dd></dl></section>`).join("\n");
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>MellowYak Phase 8 Screen Guide</title><style>@page{size:A4 landscape;margin:9mm}*{box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;color:#102334;margin:0}section{page-break-after:always}h1{font-size:20px;margin:0 0 6px}img{display:block;max-width:100%;max-height:126mm;margin:0 auto 6px;border:1px solid #cad6dc;border-radius:8px}dl{display:grid;grid-template-columns:138px 1fr;gap:3px 10px;margin:0;font-size:9px;line-height:1.2}dt{font-weight:800}dd{margin:0}.cover{display:grid;place-items:center;text-align:center;min-height:170mm}.cover h1{font-size:34px}.cover p{max-width:760px;font-size:15px}</style></head><body><section class="cover"><div><h1>MellowYak Phase 8</h1><h2>Validated Repair, Safe Apply, Rollback, and Demo Lab</h2><p>Deterministic synthetic delivery catalog · English base + Hebrew RTL · 2026-08-25</p><p>No private source, user path, credential, prompt, provider data, or live evidence is included.</p></div></section>${sections}</body></html>`;
}

async function waitForServer() {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    try { if ((await fetch(baseUrl)).ok) return; } catch { /* Vite is still starting */ }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Vite capture server did not start at ${baseUrl}`);
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
    for (const [slug] of rows) {
      const index = rows.findIndex((row) => row[0] === slug);
      const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1, colorScheme: "dark", reducedMotion: "reduce" });
      await context.addInitScript(() => {
        let callbackId = 0;
        const callbacks = new Map();
        window.__TAURI_INTERNALS__ = {
          callbacks,
          transformCallback: (callback, once = false) => { callbackId += 1; callbacks.set(callbackId, { callback, once }); return callbackId; },
          unregisterCallback: (id) => callbacks.delete(id),
          invoke: async (command) => {
            if (command === "engine_bootstrap") return { host: "127.0.0.1", port: 43128, token: "phase8-synthetic-review-only" };
            if (command === "plugin:updater|check") return null;
            if (command.includes("listen")) return 1;
            if (command === "take_pending_route") return null;
            if (command === "get_start_at_login") return false;
            return null;
          },
        };
      });
      const page = await context.newPage();
      await page.route("http://127.0.0.1:43128/**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "{}" }));
      await page.goto(`${baseUrl}/?phase8State=${slug}`, { waitUntil: "networkidle" });
      await page.locator(`[data-phase8-state="${slug}"]`).waitFor();
      if (String(slug).startsWith("hebrew-")) await page.locator('main[dir="rtl"]').waitFor();
      const filename = `${String(index).padStart(2, "0")}-${slug}.png`;
      await page.screenshot({ path: path.join(screenshots, filename), fullPage: true });
      await context.close();
      process.stdout.write(`${filename}\n`);
    }

    const manifest = {
      schema: "mellowyak.phase8.screenshot-delivery.v1",
      generated_at: generatedAt,
      fixture: "deterministic_synthetic_public",
      screenshots: rows.map(([slug, title, purpose, state, actions, known, unknown, next, modified], index) => ({
        file: `screenshots/${String(index).padStart(2, "0")}-${slug}.png`, locale: String(slug).startsWith("hebrew-") ? "he-IL" : "en-US", title, purpose, displayed_state: state, source_of_data: "deterministic synthetic Phase 8 review fixture rendered locally", available_actions: actions, known_facts: known, unknowns: unknown, expected_next_step: next, live_source_modified: modified,
      })),
    };
    await writeFile(path.join(delivery, "PHASE_8_SCREEN_GUIDE.md"), guideMarkdown());
    await writeFile(path.join(delivery, "PHASE_8_SCREEN_GUIDE.html"), guideHtml());
    await writeFile(path.join(delivery, "PHASE_8_SCREENSHOT_MANIFEST.json"), `${JSON.stringify(manifest, null, 2)}\n`);
    const pdfPage = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    await pdfPage.goto(`file://${path.join(delivery, "PHASE_8_SCREEN_GUIDE.html")}`, { waitUntil: "networkidle" });
    await pdfPage.pdf({ path: path.join(delivery, "MellowYak-Phase-8-Screen-Guide.pdf"), format: "A4", landscape: true, printBackground: true, margin: { top: "9mm", right: "9mm", bottom: "9mm", left: "9mm" } });
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
