#!/usr/bin/env node

import { spawn } from "node:child_process";
import { access, mkdir } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { chromium } from "../apps/desktop/node_modules/playwright-core/index.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const desktop = path.join(root, "apps", "desktop");
const images = path.join(root, "docs", "phase-14m-delivery", "images");
const port = Number(process.env.MELLOWYAK_CAPTURE_PORT ?? 1434);
const baseUrl = `http://127.0.0.1:${port}`;
const enginePort = 43134;
const states = [
  "00-phase13-verified-closure", "01-public-project-corpus", "02-python-project-compatibility", "03-node-project-compatibility", "04-polyglot-project-compatibility", "05-large-project-compatibility", "06-runtime-detection-python", "07-runtime-detection-node", "08-monorepo-runtime-ownership", "09-gitless-project-ready", "10-observe-only-project", "11-generated-files-excluded", "12-sensitive-files-redacted", "13-initial-scan-complete", "14-known-good-browser", "15-known-good-api", "16-known-good-cli-test", "17-passive-monitoring-public-project", "18-harmless-change-no-regression", "19-impact-selected-real-project", "20-controlled-regression-real-project", "21-confirmed-incident-real-project", "22-flaky-real-project", "23-runtime-unavailable-real-project", "24-lockfile-change-real-project", "25-large-fanout-bounded", "26-symlink-boundary-blocked", "27-watcher-gap-rescan", "28-stale-job-real-project", "29-scheduler-recovery-real-project", "30-daily-budget-exhausted", "31-outside-allowed-hours", "32-budget-run-now-override", "33-repair-workspace-public-project", "34-candidate-validated-public-project", "35-apply-confirmation-public-project", "36-applied-verified-public-project", "37-rollback-byte-identical-public-project", "38-soak-test-summary", "39-package-acceptance", "40-intel-mac-rc-readiness",
];

async function browserPath() {
  const candidates = [process.env.MELLOWYAK_CHROMIUM_PATH, "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Chromium.app/Contents/MacOS/Chromium", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"].filter(Boolean);
  for (const candidate of candidates) { try { await access(candidate); return candidate; } catch { /* Continue. */ } }
  throw new Error("No supported local Chromium browser found");
}

async function waitForServer() {
  for (let attempt = 0; attempt < 120; attempt += 1) { try { if ((await fetch(baseUrl)).ok) return; } catch { /* Vite is starting. */ } await new Promise((resolve) => setTimeout(resolve, 250)); }
  throw new Error("Phase 14 capture server did not start");
}

await mkdir(images, { recursive: true });
const server = spawn("npm", ["run", "dev", "--", "--host", "127.0.0.1", "--port", String(port), "--strictPort"], { cwd: desktop, stdio: ["ignore", "pipe", "pipe"] });
let output = "";
server.stdout.on("data", (chunk) => { output += chunk.toString(); });
server.stderr.on("data", (chunk) => { output += chunk.toString(); });
try {
  await waitForServer();
  const browser = await chromium.launch({ executablePath: await browserPath(), headless: true });
  try {
    for (const state of states) {
      const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1, colorScheme: "dark", reducedMotion: "reduce", locale: "en-US" });
      await context.addInitScript(({ bootstrapPort }) => {
        let callbackId = 0; const callbacks = new Map();
        window.__TAURI_INTERNALS__ = { callbacks, transformCallback: (callback, once = false) => { callbackId += 1; callbacks.set(callbackId, { callback, once }); return callbackId; }, unregisterCallback: (id) => callbacks.delete(id), invoke: async (command) => command === "engine_bootstrap" ? { host: "127.0.0.1", port: bootstrapPort, token: "phase14-local-capture" } : command === "get_start_at_login" ? false : command.includes("listen") ? 1 : null };
      }, { bootstrapPort: enginePort });
      const page = await context.newPage();
      await page.route(`http://127.0.0.1:${enginePort}/**`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: "{}" }));
      await page.goto(`${baseUrl}/?phase14Fixture=mellowyak.phase14.screenshots.v1&phase14State=${state}`, { waitUntil: "networkidle" });
      await page.locator(`[data-phase14-state="${state}"][data-ready="true"]`).waitFor();
      await page.screenshot({ path: path.join(images, `${state}.png`), fullPage: true });
      await context.close();
      process.stdout.write(`${state}.png\n`);
    }
  } finally { await browser.close(); }
} catch (reason) { if (output) process.stderr.write(output); throw reason; } finally { server.kill("SIGTERM"); }
