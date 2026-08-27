#!/usr/bin/env node

import { access, mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath, pathToFileURL } from "node:url";
import { chromium } from "../apps/desktop/node_modules/playwright-core/index.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const delivery = path.join(root, "docs", "phase-16m-delivery");
const temp = process.env.MELLOWYAK_PHASE16M_RENDER_ROOT
  ?? "/private/tmp/mellowyak-phase16m-pdf-render";

const defaultDocuments = [
  "PHASE_16M_EXECUTION_AND_EVIDENCE_REPORT",
  "PHASE_16M_VISUAL_MANUAL_AND_CHECKLIST",
];
const documents = process.argv.length > 2 ? process.argv.slice(2) : defaultDocuments;

function escapeHtml(value) {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function inline(value) {
  let rendered = escapeHtml(value);
  rendered = rendered.replace(/`([^`]+)`/g, "<code>$1</code>");
  rendered = rendered.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  rendered = rendered.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  return rendered;
}

function cells(line) {
  return line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((item) => item.trim());
}

function markdownToHtml(markdown, sourcePath) {
  const lines = markdown.split(/\r?\n/);
  const out = [];
  let list = null;
  let inCode = false;
  let sectionOpen = false;

  const closeList = () => {
    if (list) out.push(`</${list}>`);
    list = null;
  };
  const closeSection = () => {
    if (sectionOpen) out.push("</section>");
    sectionOpen = false;
  };

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (line.startsWith("```")) {
      closeList();
      if (inCode) out.push("</code></pre>");
      else out.push("<pre><code>");
      inCode = !inCode;
      continue;
    }
    if (inCode) {
      out.push(`${escapeHtml(line)}\n`);
      continue;
    }
    const heading = line.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      closeList();
      const level = heading[1].length;
      if (level === 3) {
        closeSection();
        out.push('<section class="visual-section">');
        sectionOpen = true;
      }
      out.push(`<h${level}>${inline(heading[2])}</h${level}>`);
      continue;
    }
    const image = line.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
    if (image) {
      closeList();
      const imagePath = path.resolve(path.dirname(sourcePath), image[2]);
      out.push(`<figure><img src="${pathToFileURL(imagePath).href}" alt="${escapeHtml(image[1])}"><figcaption>${escapeHtml(image[1])}</figcaption></figure>`);
      continue;
    }
    if (/^\|.*\|\s*$/.test(line) && index + 1 < lines.length && /^\|?[\s:|-]+\|\s*$/.test(lines[index + 1])) {
      closeList();
      const header = cells(line);
      const rows = [];
      index += 2;
      while (index < lines.length && /^\|.*\|\s*$/.test(lines[index])) {
        rows.push(cells(lines[index]));
        index += 1;
      }
      index -= 1;
      const wide = header.length > 6 ? " wide" : "";
      out.push(`<table class="report-table${wide}"><thead><tr>${header.map((item) => `<th>${inline(item)}</th>`).join("")}</tr></thead><tbody>`);
      for (const row of rows) out.push(`<tr>${row.map((item) => `<td>${inline(item)}</td>`).join("")}</tr>`);
      out.push("</tbody></table>");
      continue;
    }
    const bullet = line.match(/^[-*]\s+(.+)$/);
    const numbered = line.match(/^\d+\.\s+(.+)$/);
    if (bullet || numbered) {
      const wanted = bullet ? "ul" : "ol";
      if (list !== wanted) {
        closeList();
        list = wanted;
        out.push(`<${list}>`);
      }
      out.push(`<li>${inline((bullet ?? numbered)[1])}</li>`);
      continue;
    }
    if (!line.trim()) {
      closeList();
      continue;
    }
    closeList();
    if (line.startsWith("> ")) out.push(`<blockquote>${inline(line.slice(2))}</blockquote>`);
    else out.push(`<p>${inline(line)}</p>`);
  }
  closeList();
  closeSection();
  return out.join("\n");
}

const css = `
  @page { size: A4 portrait; margin: 14mm 12mm 15mm; }
  @page wide { size: A4 landscape; margin: 11mm; }
  * { box-sizing: border-box; }
  html { color: #172536; background: white; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
  body { margin: 0; font-size: 10.4pt; line-height: 1.42; }
  h1 { color: #09253a; font-size: 25pt; line-height: 1.08; margin: 0 0 8mm; }
  h2 { color: #0c6b72; font-size: 17pt; margin: 8mm 0 3mm; break-after: avoid; }
  h3 { color: #123c56; font-size: 14pt; margin: 0 0 3mm; break-after: avoid; }
  h4 { font-size: 11.5pt; break-after: avoid; }
  p { margin: 0 0 3mm; orphans: 3; widows: 3; }
  ul, ol { margin: 2mm 0 4mm 6mm; padding-left: 5mm; }
  li { margin-bottom: 1.2mm; }
  code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .86em; overflow-wrap: anywhere; background: #eef4f7; padding: .2em .35em; border-radius: 3px; }
  pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #edf3f6; padding: 3mm; border-radius: 4px; break-inside: avoid; }
  blockquote { margin: 3mm 0; border-left: 3px solid #37bfc0; padding-left: 4mm; color: #445b69; }
  table { width: 100%; border-collapse: collapse; margin: 3mm 0 5mm; font-size: 7.7pt; line-height: 1.25; }
  table.wide { page: wide; table-layout: fixed; font-size: 6.5pt; }
  thead { display: table-header-group; }
  tr { break-inside: avoid; }
  th, td { border: 1px solid #b8c8d2; padding: 1.4mm; vertical-align: top; overflow-wrap: anywhere; }
  th { background: #dceff1; color: #12333c; text-align: left; }
  figure { margin: 2mm 0 4mm; text-align: center; break-inside: avoid; }
  img { display: block; max-width: 100%; max-height: 148mm; width: auto; height: auto; margin: 0 auto; object-fit: contain; }
  figcaption { margin-top: 1.5mm; color: #586c78; font-size: 8pt; }
  .visual-section { break-before: page; }
  .visual-section:first-of-type { break-before: auto; }
`;

async function browserPath() {
  const candidates = [
    process.env.MELLOWYAK_CHROMIUM_PATH,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/MellowYak.app/Contents/Resources/browser/chromium/chrome-mac-x64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
  ].filter(Boolean);
  for (const candidate of candidates) {
    try { await access(candidate); return candidate; } catch { /* continue */ }
  }
  throw new Error("No local Chromium executable is available");
}

await mkdir(temp, { recursive: true });
const browser = await chromium.launch({ executablePath: await browserPath(), headless: true });
try {
  for (const name of documents) {
    const markdownPath = path.join(delivery, `${name}.md`);
    const htmlPath = path.join(temp, `${name}.html`);
    const markdown = await readFile(markdownPath, "utf8");
    const html = `<!doctype html><html><head><meta charset="utf-8"><title>${name}</title><style>${css}</style></head><body>${markdownToHtml(markdown, markdownPath)}</body></html>`;
    await writeFile(htmlPath, html);
    const page = await browser.newPage();
    const failures = [];
    page.on("requestfailed", (request) => failures.push(request.url()));
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "networkidle" });
    await page.evaluate(async () => {
      await document.fonts.ready;
      await Promise.all([...document.images].map((image) => image.complete && image.naturalWidth > 0
        ? Promise.resolve()
        : new Promise((resolve, reject) => { image.onload = resolve; image.onerror = reject; })));
    });
    if (failures.length) throw new Error(`Failed assets in ${name}: ${failures.join(", ")}`);
    await page.pdf({
      path: path.join(delivery, `${name}.pdf`),
      printBackground: true,
      preferCSSPageSize: true,
      displayHeaderFooter: true,
      headerTemplate: "<span></span>",
      footerTemplate: '<div style="font-size:8px;color:#667;width:100%;text-align:center"><span class="pageNumber"></span> / <span class="totalPages"></span></div>',
      margin: { top: "14mm", right: "12mm", bottom: "15mm", left: "12mm" },
    });
    await page.close();
    process.stdout.write(`${name}.pdf\n`);
  }
} finally {
  await browser.close();
}
