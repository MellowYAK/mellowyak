#!/usr/bin/env node

import { access, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { chromium } from "../apps/desktop/node_modules/playwright-core/index.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const delivery = path.join(root, "docs", "phase-11m-macos-delivery");
const rows = [
  ["00-macos-diagnostics", "macOS diagnostics", "Inspect local engine, schema, package, self-test, and bounded operational facts."],
  ["01-macos-acceptance-lab-ready", "Acceptance Lab ready", "A synthetic disposable local lab is ready; it is not a private project."],
  ["02-macos-acceptance-lab-known-good", "Known-good evidence", "Review passing evidence before accepting a known-good milestone."],
  ["03-macos-acceptance-lab-watch", "WATCH", "A harmless change remains WATCH and is not labeled as a regression."],
  ["04-macos-acceptance-lab-confirmed-regression", "Confirmed regression", "Comparable prior pass and reproducible current failure establish the bounded regression."],
  ["05-macos-repair-workspace", "Repair Workspace", "Work remains isolated from live source until a candidate is validated."],
  ["06-macos-candidate-validated", "Candidate validated", "The candidate passed only in its isolated workspace."],
  ["07-macos-apply-confirmation", "Apply confirmation", "Review the source-bound transaction and explicitly confirm before any write."],
  ["08-macos-applied-and-verified", "Applied and verified", "Fresh live verification completed after the transaction."],
  ["09-macos-rolled-back-safely", "Rolled back safely", "A failed post-check restored affected bytes and preserved unrelated files."],
  ["10-macos-native-tray", "Native tray — TEST-ONLY PREVIEW", "Production-component preview only; it is not evidence of a physical native click."],
  ["11-macos-notification-destination", "Notification destination", "The validated in-app entity destination opened after activation."],
  ["12-macos-start-at-login", "Start at Login", "Configure persisted background behavior and the native login item."],
  ["13-macos-update-available", "Update available", "Visual reference for the production Update Status surface."],
  ["14-macos-update-downloading", "Update downloading", "Visual reference; exact complete-download evidence is in MACOS_UPDATER_E2E.json."],
  ["15-macos-update-signature-rejected", "Update signature rejected", "Visual reference; tampered and wrong-key rejection is machine-recorded."],
  ["16-macos-update-completed", "Update completed", "Visual reference; the disposable higher-version install is machine-recorded."],
  ["17-macos-package-status", "Package status", "Diagnostics reference; exact app, engine, browser and DMG identities are in PACKAGE_INVENTORY.md."],
  ["18-macos-signing-status", "Signing status", "Diagnostics reference; only ad-hoc structural signing is verified."],
  ["19-macos-performance", "Performance", "Diagnostics reference; exact local measurements are in MACOS_PERFORMANCE.json."],
  ["20-hebrew-macos-diagnostics", "Hebrew RTL diagnostics", "The equivalent diagnostics surface uses Hebrew RTL and translation keys."],
  ["21-hebrew-update-status", "Hebrew RTL destination", "Hebrew RTL product destination; updater transition evidence remains machine-readable."],
];

async function browserPath() {
  const candidates = [
    process.env.MELLOWYAK_CHROMIUM_PATH,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
  ].filter(Boolean);
  for (const candidate of candidates) {
    try { await access(candidate); return candidate; } catch { /* try next */ }
  }
  throw new Error("No local Chromium browser found");
}

const sections = rows.map(([name, title, description]) => `
  <section><h1>${title}</h1><img src="screenshots/${name}.png" alt="${title}">
  <p>${description}</p><p><strong>Data:</strong> deterministic synthetic fixture.
  <strong>Source write:</strong> none during capture.</p></section>`).join("\n");
const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>MellowYak Phase 11M macOS Screen Guide</title><style>
@page{size:A4 landscape;margin:9mm}body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#102334;margin:0}section{page-break-after:always}h1{font-size:22px;margin:0 0 7px}img{display:block;max-width:100%;max-height:150mm;margin:auto;border:1px solid #cad6dc;border-radius:8px}p{font-size:11px;line-height:1.35}.cover{display:grid;place-items:center;min-height:175mm;text-align:center}.cover h1{font-size:38px}</style></head><body><section class="cover"><div><h1>MellowYak Phase 11M</h1><h2>macOS Native Hardening and Acceptance</h2><p>22 synthetic product screens · Intel macOS · 2026-08-25</p><p>No private project or user data.</p></div></section>${sections}</body></html>`;
await writeFile(path.join(delivery, "PHASE_11M_SCREEN_GUIDE.html"), html);
await writeFile(path.join(delivery, "PHASE_11M_SCREENSHOT_MANIFEST.json"), `${JSON.stringify({
  schema: "mellowyak.phase11m.screenshot-delivery.v1",
  generated_at: "2026-08-25",
  data: "deterministic_synthetic",
  native_physical_actions_captured: false,
  screenshots: rows.map(([name, title, description]) => ({ file: `screenshots/${name}.png`, title, description })),
}, null, 2)}\n`);
const browser = await chromium.launch({ executablePath: await browserPath(), headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(`file://${path.join(delivery, "PHASE_11M_SCREEN_GUIDE.html")}`, { waitUntil: "networkidle" });
  await page.pdf({ path: path.join(delivery, "MellowYak-Phase-11M-macOS-Screen-Guide.pdf"), format: "A4", landscape: true, printBackground: true });
} finally {
  await browser.close();
}
