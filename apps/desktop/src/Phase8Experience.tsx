import { open } from "@tauri-apps/plugin-dialog";
import { useMemo, useState } from "react";
import {
  createDemoLab,
  exportProductSelfTest,
  runDemoAction,
  runProductSelfTest,
  type DemoLabRun,
  type ProductSelfTestRun,
} from "./api";
import type { TranslationKey } from "./i18n";
import { mascotAssets, type MascotId } from "./mascots";

export const phase8CaptureStates = [
  "repair-workspace-ready",
  "workspace-changes",
  "candidate-patch-preview",
  "candidate-diff",
  "validation-plan",
  "candidate-validating",
  "validation-failed",
  "candidate-validated",
  "apply-blocked-stale-source",
  "apply-confirmation",
  "safety-snapshot-created",
  "applying",
  "post-apply-verification",
  "applied-and-verified",
  "post-apply-failed",
  "rolled-back-safely",
  "recovery-required",
  "portable-repair-package",
  "demo-lab",
  "demo-confirmed-regression",
  "demo-valid-repair",
  "product-self-test-running",
  "product-self-test-passed",
  "hebrew-candidate-validated",
  "hebrew-apply-confirmation",
  "hebrew-rollback-safe",
] as const;

export type Phase8CaptureState = typeof phase8CaptureStates[number];
type Translator = (key: TranslationKey, values?: Record<string, string | number>) => string;

const stateTone: Partial<Record<Phase8CaptureState, string>> = {
  "validation-failed": "danger",
  "apply-blocked-stale-source": "warning",
  "post-apply-failed": "danger",
  "recovery-required": "danger",
  "candidate-validated": "success",
  "applied-and-verified": "success",
  "rolled-back-safely": "success",
  "product-self-test-passed": "success",
  "hebrew-candidate-validated": "success",
  "hebrew-rollback-safe": "success",
};

const stateMascot: Partial<Record<Phase8CaptureState, MascotId>> = {
  "repair-workspace-ready": "yak-thinking",
  "candidate-validating": "yak-working-laptop",
  "validation-failed": "yak-warning-stop",
  "candidate-validated": "yak-success-check",
  "apply-confirmation": "yak-security-shield",
  "rolled-back-safely": "yak-security-shield",
  "recovery-required": "yak-alert-point",
  "demo-lab": "yak-wave",
};

const fileRows = [
  { path: "checkout/service.py", operation: "MODIFY", size: 1840 },
  { path: "tests/test_checkout.py", operation: "MODIFY", size: 972 },
  { path: "checkout/receipt.py", operation: "ADD", size: 624 },
];
const syntheticMetadata = { candidate: "R3 · c8f9a72b", workspace: "ws-8f46 · 7a2b90de" };

function StateCard({ state, t }: { state: Phase8CaptureState; t: Translator }) {
  const stateKey = `phase8.state.${state}` as TranslationKey;
  const descriptionKey = `phase8.state.${state}.body` as TranslationKey;
  const mascot = stateMascot[state] ?? (stateTone[state] === "success" ? "yak-success-check" : "yak-working-laptop");
  const showDiff = state === "candidate-diff";
  const showChecks = ["validation-plan", "candidate-validating", "validation-failed", "candidate-validated", "post-apply-verification", "applied-and-verified", "product-self-test-running", "product-self-test-passed", "hebrew-candidate-validated"].includes(state);
  const showConfirmation = state === "apply-confirmation" || state === "hebrew-apply-confirmation";
  const showJournal = ["safety-snapshot-created", "applying", "post-apply-verification", "post-apply-failed", "rolled-back-safely", "recovery-required", "hebrew-rollback-safe"].includes(state);
  return <section className={`phase8-state panel ${stateTone[state] ?? ""}`} data-phase8-state={state}>
    <header className="phase8-state-head">
      <div><span className="eyebrow">{t("phase8.eyebrow")}</span><h1>{t(stateKey)}</h1><p>{t(descriptionKey)}</p></div>
      <img src={mascotAssets[mascot].src} alt={t(mascotAssets[mascot].altKey)} />
    </header>
    <div className="phase8-identity-grid">
      <div><span>{t("phase8.candidateVersion")}</span><strong>{syntheticMetadata.candidate}</strong></div>
      <div><span>{t("phase8.workspaceIdentity")}</span><strong>{syntheticMetadata.workspace}</strong></div>
      <div><span>{t("phase8.liveFreshness")}</span><strong>{t(state.includes("stale") ? "phase8.freshness.stale" : "phase8.freshness.current")}</strong></div>
      <div><span>{t("phase8.liveSourceModified")}</span><strong>{t(["applying", "post-apply-verification", "applied-and-verified", "post-apply-failed"].includes(state) ? "common.yes" : "common.no")}</strong></div>
    </div>
    {(state === "workspace-changes" || state === "candidate-patch-preview" || state === "candidate-diff" || state === "candidate-validated" || state === "apply-confirmation" || state === "portable-repair-package" || state.startsWith("hebrew-")) && <div className="phase8-files">
      <div className="section-head"><h2>{t("phase8.candidateFiles")}</h2><span>{t("phase8.fileSummary", { added: 1, modified: 2, deleted: 0, renamed: 0 })}</span></div>
      {fileRows.map((file) => <article key={file.path}><code dir="ltr">{file.path}</code><span className={`operation ${file.operation.toLowerCase()}`}>{t(`phase8.operation.${file.operation}` as TranslationKey)}</span><small>{t("phase8.bytes", { count: file.size })}</small><button className="secondary">{t("phase8.viewDiff")}</button></article>)}
    </div>}
    {showDiff && <pre className="phase8-diff" dir="ltr"><code>{"@@ -14,5 +14,8 @@\n- return charge(cart)\n+ result = charge(cart)\n+ if result.accepted:\n+     return receipt(result)"}</code></pre>}
    {showChecks && <div className="phase8-checks">
      <h2>{t("phase8.requiredChecks")}</h2>
      {["originalProbe", "impactedProbe", "runtimeHealth"].map((check, index) => <article key={check}><span className={state.includes("failed") && index === 0 ? "check-fail" : "check-pass"}>{state === "candidate-validating" || state === "product-self-test-running" ? "◌" : state.includes("failed") && index === 0 ? "×" : "✓"}</span><div><strong>{t(`phase8.check.${check}` as TranslationKey)}</strong><small>{t(index === 0 ? "phase8.check.originalFirst" : "phase8.check.workspaceBound")}</small></div></article>)}
    </div>}
    {showConfirmation && <div className="phase8-confirmation">
      <h2>{t("phase8.confirm.title")}</h2>
      <p>{t("phase8.confirm.onlyCandidate")}</p><p>{t("phase8.confirm.safetySnapshot")}</p><p>{t("phase8.confirm.rollback")}</p><p>{t("phase8.confirm.unrelated")}</p>
      <label><input type="checkbox" defaultChecked /> <span>{t("phase8.confirm.deliberate")}</span></label>
    </div>}
    {showJournal && <div className="phase8-timeline">
      {["prepared", "snapshot", "writes", "verification", state.includes("rollback") || state.includes("failed") || state.includes("recovery") ? "rollback" : "commit"].map((step, index) => <div key={step} className={index < 3 ? "done" : index === 3 ? "active" : "pending"}><span>{index < 3 ? "✓" : index === 3 ? "●" : "○"}</span><small>{t(`phase8.journal.${step}` as TranslationKey)}</small></div>)}
    </div>}
    <div className="phase8-actions">
      <button className="secondary">{t("phase8.technicalDetails")}</button>
      <button className="secondary">{t("phase8.exportCandidate")}</button>
      <button className="primary" disabled={state === "validation-failed" || state === "apply-blocked-stale-source" || state === "recovery-required"}>{t(showConfirmation ? "phase8.applyRepair" : state === "candidate-validated" || state === "hebrew-candidate-validated" ? "phase8.prepareApply" : "phase8.next")}</button>
    </div>
    <footer className="phase8-source-safety">{t("phase8.sourceSafety")}</footer>
  </section>;
}

export function Phase8Experience({ t, captureState, onError }: { t: Translator; captureState?: Phase8CaptureState | null; onError?: (code: string) => void }) {
  const [view, setView] = useState<"demo" | "selfTest">(captureState?.startsWith("product-self-test") ? "selfTest" : "demo");
  const [demo, setDemo] = useState<DemoLabRun | null>(null);
  const [selfTest, setSelfTest] = useState<ProductSelfTestRun | null>(null);
  const [busy, setBusy] = useState(false);
  const state = useMemo<Phase8CaptureState>(() => captureState ?? (view === "selfTest" ? (selfTest?.status === "PASS" ? "product-self-test-passed" : "product-self-test-running") : demo?.scenario === "CONFIRMED_REGRESSION" ? "demo-confirmed-regression" : demo?.scenario === "VALIDATED" ? "demo-valid-repair" : "demo-lab"), [captureState, demo, selfTest, view]);
  const execute = async (operation: () => Promise<void>) => {
    setBusy(true);
    try { await operation(); }
    catch (reason) { onError?.(reason instanceof Error ? reason.message : "PHASE8_OPERATION_FAILED"); }
    finally { setBusy(false); }
  };
  const createDemo = () => execute(async () => {
    const selected = await open({ directory: true, multiple: false, title: t("phase8.demo.chooseFolder") });
    if (typeof selected === "string") setDemo(await createDemoLab(selected));
  });
  const demoAction = (action: Parameters<typeof runDemoAction>[1]) => execute(async () => { if (demo) setDemo(await runDemoAction(demo.id, action)); });
  const runSelfTest = () => execute(async () => { setView("selfTest"); setSelfTest(await runProductSelfTest()); });
  return <div className="phase8-page">
    {!captureState && <nav className="phase8-tabs" aria-label={t("phase8.navLabel")}><button className={view === "demo" ? "active" : ""} onClick={() => setView("demo")}>{t("phase8.demo.title")}</button><button className={view === "selfTest" ? "active" : ""} onClick={() => setView("selfTest")}>{t("phase8.selfTest.title")}</button></nav>}
    <StateCard state={state} t={t} />
    {!captureState && view === "demo" && <section className="panel phase8-controls"><div><h2>{t("phase8.demo.controls")}</h2><p>{t("phase8.demo.syntheticNotice")}</p></div><div className="button-row">
      {!demo && <button className="primary" disabled={busy} onClick={() => void createDemo()}>{t("phase8.demo.create")}</button>}
      {demo && <><button className="secondary" disabled={busy} onClick={() => void demoAction("inject-regression")}>{t("phase8.demo.inject")}</button><button className="secondary" disabled={busy} onClick={() => void demoAction("create-bad-candidate")}>{t("phase8.demo.badCandidate")}</button><button className="secondary" disabled={busy} onClick={() => void demoAction("create-valid-candidate")}>{t("phase8.demo.validCandidate")}</button><button className="primary" disabled={busy} onClick={() => void demoAction("apply-valid")}>{t("phase8.demo.apply")}</button><button className="secondary danger" disabled={busy} onClick={() => void demoAction("simulate-post-apply-failure")}>{t("phase8.demo.rollback")}</button><button className="secondary" disabled={busy} onClick={() => void demoAction("reset")}>{t("phase8.demo.reset")}</button></>}
    </div></section>}
    {!captureState && view === "selfTest" && <section className="panel phase8-controls"><div><h2>{t("phase8.selfTest.controls")}</h2><p>{t("phase8.selfTest.disposable")}</p></div><div className="button-row"><button className="primary" disabled={busy} onClick={() => void runSelfTest()}>{t("phase8.selfTest.run")}</button>{selfTest && <button className="secondary" onClick={() => void execute(async () => { await exportProductSelfTest(selfTest.id); })}>{t("phase8.selfTest.export")}</button>}</div>{selfTest && <div className="phase8-self-test-list">{selfTest.steps.map((step, index) => <article key={index}><span>{String(step.status) === "PASS" ? "✓" : "•"}</span><strong>{t("phase8.selfTest.step", { name: String(step.step) })}</strong><small>{t("phase8.duration", { count: Number(step.duration_ms ?? 0) })}</small></article>)}</div>}</section>}
  </div>;
}
