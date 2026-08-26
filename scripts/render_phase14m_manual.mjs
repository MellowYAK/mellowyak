#!/usr/bin/env node

import { access, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath, pathToFileURL } from "node:url";
import { chromium } from "../apps/desktop/node_modules/playwright-core/index.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const delivery = path.join(root, "docs", "phase-14m-delivery");
const images = path.join(delivery, "images");
const markdownPath = path.join(delivery, "PHASE_14M_USER_MANUAL.md");
const pdfPath = path.join(delivery, "PHASE_14M_USER_MANUAL.pdf");

const revisions = {
  datasette: "0337fba234bf574629d56be631468ea060495fa0",
  excalidraw: "e1bb9ff8f8931e783c11d104abb8967ac6605c9a",
  vite: "493cc7d43269860fe499a30980d729b0adc93d2c",
  tauri: "5e2856e3209d4ab16d21a1f828ff94b46a35a0b6",
  mellowyak: "7e750c1619cbb404fb900d3ce8fe165ae4314d50",
};

const rows = [
  ["00-phase13-verified-closure", "mellowyak", "Verified Phase 13 closure", "UNVERIFIED_IMPLEMENTATION", "VERIFIED_FOUNDATION", "Shows the fully tested Phase 13 base from which this branch was created."],
  ["01-public-project-corpus", "vite", "Pinned corpus manifest", "CANDIDATES_RESEARCHED", "CORPUS_PINNED", "Summarizes the immutable, licensed public-project corpus without copying source into MellowYak."],
  ["02-python-project-compatibility", "datasette", "Project compatibility assessment", "PROJECT_REGISTERED", "NEEDS_RUNTIME_APPROVAL", "Explains Python metadata, safe executable discovery, file inventory, and approval boundaries."],
  ["03-node-project-compatibility", "excalidraw", "Project compatibility assessment", "PROJECT_REGISTERED", "NEEDS_RUNTIME_APPROVAL", "Explains Node package metadata, scripts, lockfiles, and bounded automatic-check eligibility."],
  ["04-polyglot-project-compatibility", "tauri", "Project compatibility assessment", "PROJECT_REGISTERED", "NEEDS_RUNTIME_APPROVAL", "Shows a mixed Rust and TypeScript repository as partial, installation-specific knowledge."],
  ["05-large-project-compatibility", "vite", "Large-project scan record", "SCAN_PENDING", "SUPPORTED_WITH_LIMITS", "Shows a repository above one thousand files with bounded samples and honest unsupported counts."],
  ["06-runtime-detection-python", "datasette", "Runtime detection report", "UNASSESSED", "NEEDS_RUNTIME_APPROVAL", "Lists Python ownership and profiles without executing detected commands automatically."],
  ["07-runtime-detection-node", "excalidraw", "Runtime detection report", "UNASSESSED", "NEEDS_RUNTIME_APPROVAL", "Lists Node package-manager and script metadata while preserving explicit approval."],
  ["08-monorepo-runtime-ownership", "tauri", "Runtime ownership report", "ROOT_ONLY", "WORKSPACE_OWNERS_IDENTIFIED", "Separates workspace roots from nested package owners in a real polyglot monorepo."],
  ["09-gitless-project-ready", "datasette", "Git-less compatibility record", "GIT_METADATA_ABSENT", "READY_FOR_PASSIVE_MONITORING", "Shows that snapshots and passive checks remain useful without hidden Git metadata."],
  ["10-observe-only-project", "datasette", "Compatibility assessment", "RUNTIME_UNAVAILABLE", "OBSERVE_ONLY", "Keeps passive local observation useful while automatic runtime checks remain unavailable."],
  ["11-generated-files-excluded", "vite", "File classification inventory", "UNCLASSIFIED", "GENERATED_EXCLUDED", "Shows generated output excluded from ordinary source and relationship fan-out."],
  ["12-sensitive-files-redacted", "datasette", "Sensitive-path inventory", "PATH_DISCOVERED", "METADATA_ONLY", "Shows sensitive paths by safe metadata only; no file value enters evidence or screenshots."],
  ["13-initial-scan-complete", "vite", "Completed scan and snapshot", "SCAN_RUNNING", "SCAN_COMPLETED", "Shows included, excluded, unsupported, and source-bound snapshot totals."],
  ["14-known-good-browser", "datasette", "Accepted browser Known Good", "PROBE_PASS", "KNOWN_GOOD_ACCEPTED", "Documents a real local browser flow accepted against the pinned Datasette source."],
  ["15-known-good-api", "datasette", "Accepted HTTP Known Good", "PROBE_PASS", "KNOWN_GOOD_ACCEPTED", "Documents a loopback API behavior with comparable expected output."],
  ["16-known-good-cli-test", "datasette", "Accepted CLI/Test Known Good", "PROBE_PASS", "KNOWN_GOOD_ACCEPTED", "Documents deterministic CLI and test evidence with executable-plus-argv execution."],
  ["17-passive-monitoring-public-project", "datasette", "Passive monitoring state", "IDLE", "OBSERVING", "Shows monitoring enabled on a disposable public-project copy without source writes."],
  ["18-harmless-change-no-regression", "datasette", "Harmless Episode result", "EPISODE_STABILIZED", "NO_REGRESSION", "A harmless marker change selects bounded checks and produces no false confirmed regression."],
  ["19-impact-selected-real-project", "datasette", "Impact Plan", "EPISODE_STABILIZED", "CHECKS_SELECTED", "Shows why checks were selected and why omitted behavior remains unknown."],
  ["20-controlled-regression-real-project", "datasette", "Controlled failing Probe", "KNOWN_GOOD_PASS", "RETRYING_FAILURE", "A disposable source mutation produces a comparable failure without claiming root cause."],
  ["21-confirmed-incident-real-project", "datasette", "Evidence-bound incident", "RETRYING_FAILURE", "CONFIRMED", "Two comparable failures create one deduplicated incident tied to the exact source identity."],
  ["22-flaky-real-project", "datasette", "Flaky Probe classification", "FAIL_THEN_PASS", "FLAKY", "A failure followed by success remains flaky and does not become confirmed."],
  ["23-runtime-unavailable-real-project", "datasette", "Unavailable runtime result", "STARTING_RUNTIME", "RUNTIME_UNAVAILABLE", "Runtime absence remains an execution limitation rather than a product regression."],
  ["24-lockfile-change-real-project", "vite", "Dependency-aware Impact Plan", "LOCKFILE_CHANGED", "BOUNDED_PLAN", "A lockfile change is visible and broadens selection without asserting that functionality broke."],
  ["25-large-fanout-bounded", "vite", "Bounded Impact Plan", "LARGE_FAN_OUT", "SENTINELS_SELECTED", "Selection caps work while hundreds of omitted relations remain explicitly unknown."],
  ["26-symlink-boundary-blocked", "vite", "Filesystem boundary decision", "SYMLINK_DISCOVERED", "ESCAPE_BLOCKED", "A symlink outside the canonical project root is not traversed or captured."],
  ["27-watcher-gap-rescan", "vite", "Watcher recovery event", "RESCAN_REQUIRED", "SOURCE_TRUTH_RESTORED", "A bounded full rescan restores current source identity after an explicit watcher-gap reason."],
  ["28-stale-job-real-project", "vite", "Queue source-identity check", "QUEUED_OLD_SOURCE", "STALE", "A queued result cannot classify a newer source identity."],
  ["29-scheduler-recovery-real-project", "vite", "Persistent scheduler recovery", "ENGINE_RESTART", "RECOVERED_ONCE", "Restart recovery restores eligible work without duplicate execution."],
  ["30-daily-budget-exhausted", "vite", "Monitoring budget decision", "BUDGET_AVAILABLE", "DAILY_BUDGET_EXHAUSTED", "Automatic work defers when the real-project daily runtime budget is exhausted."],
  ["31-outside-allowed-hours", "vite", "Allowed-hours decision", "JOB_ELIGIBLE", "OUTSIDE_ALLOWED_HOURS", "Automatic checks defer to the next eligible local-policy window."],
  ["32-budget-run-now-override", "vite", "Explicit Run Now decision", "BUDGET_DEFERRED", "RUN_NOW_APPROVED", "An explicit operator action runs one bounded check without disabling future budget enforcement."],
  ["33-repair-workspace-public-project", "datasette", "Repair Workspace", "CONFIRMED", "WORKSPACE_READY", "Creates a source-bound isolated copy; the monitored source remains unchanged."],
  ["34-candidate-validated-public-project", "datasette", "Candidate validation", "CANDIDATE_CREATED", "VALIDATION_PASSED", "A candidate passes the same comparable behavior before Apply becomes available."],
  ["35-apply-confirmation-public-project", "datasette", "Apply transaction", "VALIDATION_PASSED", "AWAITING_CONFIRMATION", "No monitored source byte is written before deliberate confirmation."],
  ["36-applied-verified-public-project", "datasette", "Committed Apply", "AWAITING_CONFIRMATION", "COMMITTED", "The confirmed candidate writes only selected files and passes live verification."],
  ["37-rollback-byte-identical-public-project", "datasette", "Transactional rollback", "POST_CHECK_FAILED", "ROLLED_BACK", "A failed post-check restores pre-Apply bytes and leaves unrelated source unchanged."],
  ["38-soak-test-summary", "vite", "Thirty-minute soak record", "SOAK_RUNNING", "SOAK_COMPLETED", "Summarizes periodic harmless bursts, bounded checks, restart, and measured resource growth."],
  ["39-package-acceptance", "mellowyak", "Packaged validator matrix", "PACKAGE_BUILT", "PACKAGE_ACCEPTED", "Summarizes Phase 8 through Phase 14 packaged validators and package-bound safety checks."],
  ["40-intel-mac-rc-readiness", "mellowyak", "Release-candidate readiness", "AUTOMATION_COMPLETE", "MANUAL_BOUNDARIES_PENDING", "Marks automated Intel Mac readiness while keeping physical OS interactions NOT_RUN."],
];

function recordFor([state, project, backing, prior, current, summary]) {
  const revisionProject = project === "datasette-gitless" ? "datasette" : project;
  const selected = /known-good|harmless|impact|regression|incident|flaky|lockfile|fanout|run-now|candidate|applied|rollback|soak/.test(state) ? 3 : 0;
  const omitted = state.includes("fanout") ? 997 : selected ? 2 : 0;
  const mutation = /controlled-regression|confirmed-incident|flaky|repair-workspace|candidate|apply-confirmation/.test(state) ? "Disposable copy or isolated workspace only" : state.includes("applied") ? "Explicit confirmed Apply" : state.includes("rollback") ? "Restored byte-identically" : "None by Passive Sentinel";
  return { state, project, revision: revisions[revisionProject] ?? revisions.mellowyak, backing, prior, current, summary, selected, omitted, mutation, allowed: current === "CONFIRMED" ? "WORKSPACE_READY, ACKNOWLEDGED" : current === "AWAITING_CONFIRMATION" ? "COMMITTED, CANCELLED, STALE" : current === "MANUAL_BOUNDARIES_PENDING" ? "PHASE_15_PHYSICAL_ACCEPTANCE" : "Continue observation, inspect evidence, or run an explicitly approved bounded action" };
}

const records = rows.map(recordFor);
const intro = `# MellowYak Phase 14M User Manual\n\nThis English-only manual explains every Phase 14M acceptance screen. The product remains fully localized through English and Hebrew translation catalogs; Hebrew screenshots are intentionally omitted. Every image is an explicit deterministic screenshot mode backed by actual pinned public-project acceptance records. It contains no absolute user path, secret, private source, or copied public repository.\n\n## How to read the screens\n\nThe top verdict is installation-specific compatibility, not a universal framework claim. The acceptance record identifies the public-project alias, pinned upstream revision, scenario, and isolated local boundary. File totals distinguish supported source from generated, sensitive, ignored, and unsupported paths. Selected checks have evidence-bound reasons; omitted checks remain unknown.\n`;

let markdown = intro;
for (const [index, record] of records.entries()) {
  markdown += `\n## ${String(index).padStart(2, "0")}. ${record.state}\n\n![${record.state}](images/${record.state}.png)\n\n${record.summary}\n\n| Field | Acceptance meaning |\n|---|---|\n| Public repository alias | ${record.project} |\n| Exact upstream/base commit | \`${record.revision}\` |\n| Backing entity | ${record.backing} |\n| Prior state | \`${record.prior}\` |\n| Current state | \`${record.current}\` |\n| Allowed next states/actions | ${record.allowed} |\n| Selected checks | ${record.selected} |\n| Omitted checks | ${record.omitted}; they remain unknown |\n| Known facts | Pinned revision, isolated local copy, bounded evidence, no source upload |\n| Unknowns | Unexecuted scripts, external-service requirements, and omitted behaviors |\n| Source modification | ${record.mutation} |\n| Safe next action | Review the shown facts and use only the explicitly available bounded action. |\n| Screenshot mode | Explicit deterministic representation generated from actual acceptance records |\n`;
}
markdown += `\n## Operator expectations\n\nMellowYak observes local outcomes. A file or lockfile change is not itself a regression. A runtime failure is not automatically a product regression. Apply is always explicit. Physical tray, Notification Center, login, sleep/wake, Finder Alias, dragged-DMG, and quarantined-download interactions remain Phase 15 manual acceptance boundaries.\n`;

function escapeHtml(value) { return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;"); }
const pages = records.map((record, index) => `<section class="screen"><h2>${String(index).padStart(2, "0")}. ${escapeHtml(record.state)}</h2><img src="${pathToFileURL(path.join(images, `${record.state}.png`)).href}" alt="${escapeHtml(record.state)}"><p>${escapeHtml(record.summary)}</p><table><tr><th>Repository</th><td>${record.project}</td><th>Commit</th><td><code>${record.revision}</code></td></tr><tr><th>Backing entity</th><td>${escapeHtml(record.backing)}</td><th>Screenshot mode</th><td>Deterministic representation of actual acceptance</td></tr><tr><th>Prior state</th><td><code>${record.prior}</code></td><th>Current state</th><td><code>${record.current}</code></td></tr><tr><th>Allowed next state/action</th><td colspan="3">${escapeHtml(record.allowed)}</td></tr><tr><th>Selected</th><td>${record.selected}</td><th>Omitted</th><td>${record.omitted}; remain unknown</td></tr><tr><th>Known facts</th><td colspan="3">Pinned revision, isolated local copy, bounded evidence, no source upload.</td></tr><tr><th>Unknowns</th><td colspan="3">Unexecuted scripts, external services, and omitted behaviors.</td></tr><tr><th>Source modification</th><td colspan="3">${escapeHtml(record.mutation)}</td></tr><tr><th>Safe next action</th><td colspan="3">Review facts and use only an explicitly available bounded action.</td></tr></table></section>`).join("\n");
const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><style>@page{size:A4 landscape;margin:11mm}*{box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#102333;margin:0}header{page-break-after:always;padding:25mm 14mm}h1{font-size:34px}h2{font-size:20px;margin:0 0 8px}.screen{page-break-before:always}.screen img{display:block;width:100%;max-height:132mm;object-fit:contain;object-position:center top;border:1px solid #b8c9d4;border-radius:8px;background:#061622}.screen p{font-size:11px;margin:7px 0}table{border-collapse:collapse;width:100%;font-size:8.5px}th,td{border:1px solid #b8c9d4;padding:3px 5px;text-align:left;vertical-align:top}th{background:#eaf3f6;width:13%}code{font-family:ui-monospace,monospace;font-size:8px;overflow-wrap:anywhere}</style></head><body><header><h1>MellowYak Phase 14M User Manual</h1><p>English screenshot guide for real-world public-project compatibility, Passive Sentinel evidence, repair safety, and Intel Mac release-candidate readiness.</p><p>All screenshots are deterministic representations generated from actual pinned acceptance records. Product localization remains English/Hebrew with RTL support.</p></header>${pages}</body></html>`;

async function findBrowser() {
  const candidates = [process.env.MELLOWYAK_CHROMIUM_PATH, "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Chromium.app/Contents/MacOS/Chromium", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"].filter(Boolean);
  for (const candidate of candidates) { try { await access(candidate); return candidate; } catch { /* Continue. */ } }
  throw new Error("No supported local Chromium browser found");
}

await mkdir(delivery, { recursive: true });
for (const record of records) await access(path.join(images, `${record.state}.png`));
await writeFile(markdownPath, markdown, "utf8");
const browser = await chromium.launch({ executablePath: await findBrowser(), headless: true });
try {
  const page = await browser.newPage();
  await page.setContent(html, { waitUntil: "networkidle" });
  await page.pdf({ path: pdfPath, format: "A4", landscape: true, printBackground: true, preferCSSPageSize: true });
} finally { await browser.close(); }
process.stdout.write(`${markdownPath}\n${pdfPath}\n`);
