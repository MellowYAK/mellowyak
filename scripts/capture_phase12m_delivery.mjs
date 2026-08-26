#!/usr/bin/env node

import { spawn, spawnSync } from "node:child_process";
import { access, mkdir } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { chromium } from "../apps/desktop/node_modules/playwright-core/index.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const desktop = path.join(root, "apps", "desktop");
const images = path.join(root, "docs", "phase-12m-delivery", "images");
const port = Number(process.env.MELLOWYAK_CAPTURE_PORT ?? 1432);
const baseUrl = `http://127.0.0.1:${port}`;
const enginePort = 43132;

const states = [
  "00-reference-project-created",
  "01-runtime-wizard-detected-profiles",
  "02-runtime-wizard-approved",
  "03-behavior-capture-ready",
  "04-behavior-capture-active",
  "05-behavior-capture-review",
  "06-known-good-accepted-pass",
  "07-project-overview-known-good",
  "08-harmless-episode",
  "09-check-passed-no-regression",
  "10-controlled-regression-episode",
  "11-regression-confirmed-live",
  "12-regression-evidence-technical",
  "13-repair-workspace-live-data",
  "14-bad-candidate-rejected",
  "15-valid-candidate-validated",
  "16-apply-awaiting-confirmation",
  "17-apply-preflight",
  "18-apply-writing",
  "19-live-verification",
  "20-applied-and-verified",
  "21-post-check-failed",
  "22-rollback-running",
  "23-rolled-back-byte-identical",
  "24-home-needs-attention",
  "25-home-resolved",
  "26-diagnostics-ad-hoc-signed",
  "27-updater-not-checked",
  "28-updater-update-available",
  "29-updater-downloading",
  "30-updater-invalid-signature",
  "31-updater-updated",
  "32-manual-macos-checklist",
  "33-hebrew-known-good",
  "34-hebrew-regression",
  "35-hebrew-apply-confirmation",
  "36-hebrew-rollback",
  "37-hebrew-diagnostics",
];

function loadAuthoritativeStateModel() {
  const result = spawnSync(
    path.join(root, "engine", ".venv", "bin", "python"),
    [
      "-c",
      "import json; from mellowyak_engine.workflow import state_model; print(json.dumps(state_model(), sort_keys=True))",
    ],
    {
      cwd: root,
      encoding: "utf8",
      env: {
        ...process.env,
        PYTHONPATH: path.join(root, "engine", "src"),
      },
    },
  );
  if (result.status !== 0) {
    throw new Error(result.stderr || "Unable to load the backend workflow state model");
  }
  return JSON.parse(result.stdout);
}

async function findBrowser() {
  const candidates = [
    process.env.MELLOWYAK_CHROMIUM_PATH,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
  ].filter(Boolean);
  for (const candidate of candidates) {
    try {
      await access(candidate);
      return candidate;
    } catch {
      // Continue to the next local browser candidate.
    }
  }
  throw new Error("No supported local Chromium browser found");
}

async function waitForServer() {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    try {
      if ((await fetch(baseUrl)).ok) return;
    } catch {
      // Vite is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("Phase 12M capture server did not start");
}

const stateModel = loadAuthoritativeStateModel();
await mkdir(images, { recursive: true });
const browserPath = await findBrowser();
const server = spawn(
  "npm",
  ["run", "dev", "--", "--host", "127.0.0.1", "--port", String(port), "--strictPort"],
  { cwd: desktop, stdio: ["ignore", "pipe", "pipe"] },
);
let serverOutput = "";
server.stdout.on("data", (chunk) => { serverOutput += chunk.toString(); });
server.stderr.on("data", (chunk) => { serverOutput += chunk.toString(); });

try {
  await waitForServer();
  const browser = await chromium.launch({ executablePath: browserPath, headless: true });
  try {
    for (const state of states) {
      const context = await browser.newContext({
        viewport: { width: 1440, height: 1000 },
        deviceScaleFactor: 1,
        colorScheme: "dark",
        reducedMotion: "reduce",
      });
      await context.addInitScript(({ port: bootstrapPort }) => {
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
            if (command === "engine_bootstrap") {
              return {
                host: "127.0.0.1",
                port: bootstrapPort,
                token: "phase12-synthetic-capture",
              };
            }
            if (command === "get_start_at_login") return false;
            if (command.includes("listen")) return 1;
            return null;
          },
        };
      }, { port: enginePort });
      const page = await context.newPage();
      await page.route(`http://127.0.0.1:${enginePort}/**`, (route) => {
        const pathname = new URL(route.request().url()).pathname;
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(pathname === "/workflow/state-model" ? stateModel : {}),
        });
      });
      await page.goto(
        `${baseUrl}/?phase12Fixture=mellowyak.phase12.screenshots.v1&phase12State=${state}`,
        { waitUntil: "networkidle" },
      );
      const surface = page.locator(`[data-phase12-state="${state}"][data-ready="true"]`);
      await surface.waitFor();
      if (state.startsWith("3") && Number(state.slice(0, 2)) >= 33) {
        await page.locator('main[dir="rtl"]').waitFor();
      }
      await page.screenshot({ path: path.join(images, `${state}.png`), fullPage: true });
      await context.close();
      process.stdout.write(`${state}.png\n`);
    }
  } finally {
    await browser.close();
  }
} catch (reason) {
  if (serverOutput) process.stderr.write(serverOutput);
  throw reason;
} finally {
  server.kill("SIGTERM");
}
