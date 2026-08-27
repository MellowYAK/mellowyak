#!/usr/bin/env node

import { spawn } from "node:child_process";
import { access, mkdir, rm } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { chromium } from "../apps/desktop/node_modules/playwright-core/index.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const desktop = path.join(root, "apps", "desktop");
const images = path.join(root, "docs", "phase-15m-delivery", "images");
const port = Number(process.env.MELLOWYAK_CAPTURE_PORT ?? 1435);
const baseUrl = `http://127.0.0.1:${port}`;
const enginePort = 43135;
const fixture = "mellowyak.phase15.screenshots.v1";
const states = [
  "00-product-lock-overview",
  "01-current-known-good-locked",
  "02-change-decision-required",
  "03-expected-change-reverified",
  "04-promotion-confirmation",
  "05-known-good-promoted",
  "06-repair-verified",
  "07-repair-live-progress",
  "08-repair-rolled-back",
  "09-yak-receipt",
  "10-yak-receipt-unknowns",
  "11-intel-mac-package-status",
];

async function browserPath() {
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
      // Continue to the next locally installed browser.
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
  throw new Error("Phase 15M capture server did not start");
}

async function captureHumanScroll(page, state) {
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.waitForTimeout(250);
  let part = 1;
  let previousY = -1;
  while (true) {
    const position = await page.evaluate(() => ({
      y: Math.round(window.scrollY),
      viewport: window.innerHeight,
      height: document.documentElement.scrollHeight,
    }));
    const filename = `${state}-part-${String(part).padStart(2, "0")}.png`;
    await page.screenshot({ path: path.join(images, filename), fullPage: false });
    process.stdout.write(`${filename} · scroll ${position.y}/${Math.max(0, position.height - position.viewport)}\n`);
    const bottom = Math.max(0, position.height - position.viewport);
    if (position.y >= bottom || position.y === previousY) break;
    previousY = position.y;
    await page.evaluate(() => window.scrollBy({ top: Math.floor(window.innerHeight * 0.76), behavior: "smooth" }));
    await page.waitForTimeout(500);
    part += 1;
  }
}

await rm(images, { recursive: true, force: true });
await mkdir(images, { recursive: true });
const server = spawn(
  "npm",
  ["run", "dev", "--", "--host", "127.0.0.1", "--port", String(port), "--strictPort"],
  { cwd: desktop, stdio: ["ignore", "pipe", "pipe"] },
);
let output = "";
server.stdout.on("data", (chunk) => { output += chunk.toString(); });
server.stderr.on("data", (chunk) => { output += chunk.toString(); });

try {
  await waitForServer();
  const browser = await chromium.launch({ executablePath: await browserPath(), headless: true });
  try {
    for (const state of states) {
      const context = await browser.newContext({
        viewport: { width: 1440, height: 1000 },
        deviceScaleFactor: 1,
        colorScheme: "dark",
        reducedMotion: "reduce",
        locale: "en-US",
      });
      await context.addInitScript(({ bootstrapPort }) => {
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
          invoke: async (command) => command === "engine_bootstrap"
            ? { host: "127.0.0.1", port: bootstrapPort, token: "phase15-local-capture" }
            : command === "get_start_at_login"
              ? false
              : command.includes("listen")
                ? 1
                : null,
        };
      }, { bootstrapPort: enginePort });
      const page = await context.newPage();
      await page.route(`http://127.0.0.1:${enginePort}/**`, (route) => route.fulfill({
        status: 200,
        contentType: "application/json",
        body: "{}",
      }));
      await page.goto(`${baseUrl}/?phase15Fixture=${fixture}&phase15State=${state}`, { waitUntil: "networkidle" });
      await page.locator(`[data-phase15-state="${state}"][data-ready="true"]`).waitFor();
      await captureHumanScroll(page, state);
      await context.close();
    }
  } finally {
    await browser.close();
  }
} catch (reason) {
  if (output) process.stderr.write(output);
  throw reason;
} finally {
  server.kill("SIGTERM");
}
