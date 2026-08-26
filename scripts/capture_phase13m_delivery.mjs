#!/usr/bin/env node

import { spawn } from "node:child_process";
import { access, mkdir } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { chromium } from "../apps/desktop/node_modules/playwright-core/index.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const desktop = path.join(root, "apps", "desktop");
const images = path.join(root, "docs", "phase-13m-delivery", "images");
const port = Number(process.env.MELLOWYAK_CAPTURE_PORT ?? 1433);
const baseUrl = `http://127.0.0.1:${port}`;
const enginePort = 43133;

const states = [
  "00-monitoring-policy-default",
  "01-project-auto-check-policy",
  "02-behavior-auto-check-policy",
  "03-passive-monitoring-idle",
  "04-filesystem-burst-observed",
  "05-episode-settling",
  "06-episode-stabilized",
  "07-impact-plan-created",
  "08-checks-selected-and-omitted",
  "09-automatic-check-queued",
  "10-runtime-starting",
  "11-automatic-check-running",
  "12-automatic-check-passed",
  "13-no-regression-result",
  "14-controlled-regression-running",
  "15-retry-in-progress",
  "16-confirmed-regression-deduplicated",
  "17-tray-needs-attention",
  "18-flaky-check-detected",
  "19-runtime-unavailable",
  "20-rapid-writes-one-episode",
  "21-large-fanout-sentinel-selection",
  "22-lockfile-change-plan",
  "23-job-superseded-stale",
  "24-scheduler-recovered",
  "25-battery-saver-deferred",
  "26-normal-mode-resumed",
  "27-quiet-mode-alert-persisted",
  "28-home-background-monitoring",
  "29-project-overview-background-result",
  "30-activity-orchestration-timeline",
  "31-advanced-queue",
  "32-impact-memory",
  "33-monitoring-settings",
];

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
      // Continue through locally installed browsers.
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
  throw new Error("Phase 13M capture server did not start");
}

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
              return { host: "127.0.0.1", port: bootstrapPort, token: "phase13-synthetic-capture" };
            }
            if (command === "get_start_at_login") return false;
            if (command.includes("listen")) return 1;
            return null;
          },
        };
      }, { port: enginePort });
      const page = await context.newPage();
      await page.route(`http://127.0.0.1:${enginePort}/**`, (route) => route.fulfill({
        status: 200,
        contentType: "application/json",
        body: "{}",
      }));
      await page.goto(
        `${baseUrl}/?phase13Fixture=mellowyak.phase13.screenshots.v1&phase13State=${state}`,
        { waitUntil: "networkidle" },
      );
      await page.locator(`[data-phase13-state="${state}"][data-ready="true"]`).waitFor();
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
