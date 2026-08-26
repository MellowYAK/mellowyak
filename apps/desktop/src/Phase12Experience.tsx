import { useEffect, useMemo, useState } from "react";

import { getWorkflowStateModel } from "./api";
import "./phase12.css";

type T = (key: string, parameters?: Record<string, string | number>) => string;

export const phase12CaptureStates = [
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
] as const;

export type Phase12CaptureState = (typeof phase12CaptureStates)[number];

type Machine = "behavior" | "episode" | "verification" | "regression" | "repair_workspace" | "candidate" | "apply" | "updater";
type Category = "reference" | "runtime" | "capture" | "knownGood" | "episode" | "regression" | "repair" | "candidate" | "apply" | "home" | "diagnostics" | "updater" | "manual";

interface ScreenTruth {
  machine: Machine;
  state: string;
  previous: string;
  category: Category;
  sourceModified: boolean;
  tone: "good" | "warn" | "bad" | "active" | "neutral";
}

const truth: Record<Phase12CaptureState, ScreenTruth> = {
  "00-reference-project-created": { machine: "repair_workspace", state: "READY", previous: "CREATING", category: "reference", sourceModified: false, tone: "good" },
  "01-runtime-wizard-detected-profiles": { machine: "verification", state: "NOT_SELECTED", previous: "NOT_SELECTED", category: "runtime", sourceModified: false, tone: "neutral" },
  "02-runtime-wizard-approved": { machine: "verification", state: "QUEUED", previous: "NOT_SELECTED", category: "runtime", sourceModified: false, tone: "good" },
  "03-behavior-capture-ready": { machine: "behavior", state: "DRAFT", previous: "DRAFT", category: "capture", sourceModified: false, tone: "neutral" },
  "04-behavior-capture-active": { machine: "behavior", state: "CAPTURING", previous: "DRAFT", category: "capture", sourceModified: false, tone: "active" },
  "05-behavior-capture-review": { machine: "behavior", state: "CAPTURED", previous: "CAPTURING", category: "capture", sourceModified: false, tone: "warn" },
  "06-known-good-accepted-pass": { machine: "behavior", state: "KNOWN_GOOD", previous: "VALIDATING", category: "knownGood", sourceModified: false, tone: "good" },
  "07-project-overview-known-good": { machine: "behavior", state: "KNOWN_GOOD", previous: "VALIDATING", category: "knownGood", sourceModified: false, tone: "good" },
  "08-harmless-episode": { machine: "episode", state: "STABILIZED", previous: "SETTLING", category: "episode", sourceModified: true, tone: "warn" },
  "09-check-passed-no-regression": { machine: "verification", state: "PASSED", previous: "RUNNING", category: "episode", sourceModified: true, tone: "good" },
  "10-controlled-regression-episode": { machine: "episode", state: "CHECKS_RUNNING", previous: "IMPACT_PENDING", category: "episode", sourceModified: true, tone: "active" },
  "11-regression-confirmed-live": { machine: "regression", state: "CONFIRMED", previous: "HIGH", category: "regression", sourceModified: true, tone: "bad" },
  "12-regression-evidence-technical": { machine: "regression", state: "CONFIRMED", previous: "HIGH", category: "regression", sourceModified: true, tone: "bad" },
  "13-repair-workspace-live-data": { machine: "repair_workspace", state: "READY", previous: "CREATING", category: "repair", sourceModified: true, tone: "active" },
  "14-bad-candidate-rejected": { machine: "candidate", state: "REJECTED", previous: "VALIDATING", category: "candidate", sourceModified: true, tone: "bad" },
  "15-valid-candidate-validated": { machine: "candidate", state: "VALIDATED", previous: "VALIDATING", category: "candidate", sourceModified: true, tone: "good" },
  "16-apply-awaiting-confirmation": { machine: "apply", state: "AWAITING_CONFIRMATION", previous: "NOT_STARTED", category: "apply", sourceModified: false, tone: "warn" },
  "17-apply-preflight": { machine: "apply", state: "PREFLIGHT", previous: "AWAITING_CONFIRMATION", category: "apply", sourceModified: false, tone: "active" },
  "18-apply-writing": { machine: "apply", state: "WRITING", previous: "PREPARING", category: "apply", sourceModified: true, tone: "active" },
  "19-live-verification": { machine: "apply", state: "VERIFYING_LIVE", previous: "CAPTURING_LIVE_SOURCE", category: "apply", sourceModified: true, tone: "active" },
  "20-applied-and-verified": { machine: "apply", state: "COMMITTED", previous: "VERIFYING_LIVE", category: "apply", sourceModified: true, tone: "good" },
  "21-post-check-failed": { machine: "apply", state: "VERIFYING_LIVE", previous: "CAPTURING_LIVE_SOURCE", category: "apply", sourceModified: true, tone: "bad" },
  "22-rollback-running": { machine: "apply", state: "ROLLING_BACK", previous: "VERIFYING_LIVE", category: "apply", sourceModified: true, tone: "active" },
  "23-rolled-back-byte-identical": { machine: "apply", state: "ROLLED_BACK", previous: "ROLLING_BACK", category: "apply", sourceModified: false, tone: "good" },
  "24-home-needs-attention": { machine: "regression", state: "CONFIRMED", previous: "HIGH", category: "home", sourceModified: true, tone: "bad" },
  "25-home-resolved": { machine: "regression", state: "RESOLVED", previous: "CONFIRMED", category: "home", sourceModified: true, tone: "good" },
  "26-diagnostics-ad-hoc-signed": { machine: "updater", state: "PRODUCTION_CHANNEL_UNPUBLISHED", previous: "NOT_CHECKED", category: "diagnostics", sourceModified: false, tone: "warn" },
  "27-updater-not-checked": { machine: "updater", state: "NOT_CHECKED", previous: "NOT_CHECKED", category: "updater", sourceModified: false, tone: "neutral" },
  "28-updater-update-available": { machine: "updater", state: "UPDATE_AVAILABLE", previous: "CHECKING", category: "updater", sourceModified: false, tone: "warn" },
  "29-updater-downloading": { machine: "updater", state: "DOWNLOADING", previous: "UPDATE_AVAILABLE", category: "updater", sourceModified: false, tone: "active" },
  "30-updater-invalid-signature": { machine: "updater", state: "INVALID_SIGNATURE", previous: "VERIFYING_SIGNATURE", category: "updater", sourceModified: false, tone: "bad" },
  "31-updater-updated": { machine: "updater", state: "UPDATED", previous: "INSTALLING", category: "updater", sourceModified: false, tone: "good" },
  "32-manual-macos-checklist": { machine: "updater", state: "PRODUCTION_CHANNEL_UNPUBLISHED", previous: "NOT_CHECKED", category: "manual", sourceModified: false, tone: "neutral" },
  "33-hebrew-known-good": { machine: "behavior", state: "KNOWN_GOOD", previous: "VALIDATING", category: "knownGood", sourceModified: false, tone: "good" },
  "34-hebrew-regression": { machine: "regression", state: "CONFIRMED", previous: "HIGH", category: "regression", sourceModified: true, tone: "bad" },
  "35-hebrew-apply-confirmation": { machine: "apply", state: "AWAITING_CONFIRMATION", previous: "NOT_STARTED", category: "apply", sourceModified: false, tone: "warn" },
  "36-hebrew-rollback": { machine: "apply", state: "ROLLED_BACK", previous: "ROLLING_BACK", category: "apply", sourceModified: false, tone: "good" },
  "37-hebrew-diagnostics": { machine: "updater", state: "PRODUCTION_CHANNEL_UNPUBLISHED", previous: "NOT_CHECKED", category: "diagnostics", sourceModified: false, tone: "warn" },
};

const applySteps = ["NOT_STARTED", "AWAITING_CONFIRMATION", "PREFLIGHT", "SAFETY_SNAPSHOT", "JOURNAL_CREATED", "PREPARING", "WRITING", "CAPTURING_LIVE_SOURCE", "VERIFYING_LIVE", "COMMITTED", "ROLLING_BACK", "ROLLED_BACK"];
const applyRollbackSteps = applySteps.filter((step) => step !== "COMMITTED");
const captureSteps = ["DRAFT", "CAPTURING", "CAPTURED", "VALIDATING", "KNOWN_GOOD"];
const updaterSteps = ["NOT_CHECKED", "CHECKING", "UPDATE_AVAILABLE", "DOWNLOADING", "VERIFYING_SIGNATURE", "INSTALLING", "UPDATED"];
const referenceFacts = {
  projectName: "RideFlow Reference",
  sourceIdentity: "rideflow-episode-004",
  runtimeIdentity: "runtime-web-v1",
  restoredPath: "api/selection_mode.txt",
  verified: "VERIFIED",
  unchanged: "UNCHANGED",
  currentVersion: "0.3.0-preview.1",
  candidateVersion: "0.3.0-preview.1",
  platform: "macOS-x86_64",
  pass: "PASS",
  repeatedFail: "FAIL × 2",
};

function statusLabel(t: T, state: string): string {
  return t(`phase12.state.${state}`);
}

function stepsFor(screen: ScreenTruth): string[] {
  if (screen.machine === "apply") return ["ROLLING_BACK", "ROLLED_BACK"].includes(screen.state) ? applyRollbackSteps : applySteps;
  if (screen.machine === "behavior") return captureSteps;
  if (screen.machine === "updater") return updaterSteps;
  if (screen.machine === "episode") return ["OPEN", "SETTLING", "STABILIZED", "IMPACT_PENDING", "CHECKS_RUNNING", "COMPLETE"];
  if (screen.machine === "regression") return ["NONE", "WATCH", "SUSPECTED", "HIGH", "CONFIRMED", "RESOLVED"];
  if (screen.machine === "candidate") return ["DRAFT", "GENERATED", "VALIDATING", "VALIDATED"];
  return ["CREATING", "READY", "CHANGED", "VALIDATING", "VALIDATED"];
}

function RuntimeProfiles({ t, approved }: { t: T; approved: boolean }) {
  const profiles = [
    ["phase12.runtime.web", "node", "127.0.0.1:8262"],
    ["phase12.runtime.api", "python3", "127.0.0.1:8263"],
    ["phase12.runtime.tests", "python3", "unittest"],
    ["phase12.runtime.cli", "python3", "ride_status.py"],
  ];
  return <section className="phase12-profile-grid" aria-label={t("phase12.runtime.profiles")}>
    {profiles.map(([nameKey, executable, endpoint]) => <article key={nameKey} className="panel"><span className="phase12-profile-icon" aria-hidden="true" /> <div><strong>{t(nameKey)}</strong><code dir="ltr">{executable}</code><small dir="ltr">{endpoint}</small></div><span className={`phase12-mini-state ${approved ? "good" : "neutral"}`}>{t(approved ? "phase12.runtime.approved" : "phase12.runtime.detected")}</span></article>)}
  </section>;
}

function ApplyEvidence({ t, state }: { t: T; state: string }) {
  const beforeMutation = ["NOT_STARTED", "AWAITING_CONFIRMATION", "PREFLIGHT"].includes(state);
  const rolledBack = state === "ROLLED_BACK";
  const journalCreated = ["JOURNAL_CREATED", "PREPARING", "WRITING", "CAPTURING_LIVE_SOURCE", "VERIFYING_LIVE", "COMMITTED", "ROLLING_BACK", "ROLLED_BACK"].includes(state);
  const mutationStarted = ["WRITING", "CAPTURING_LIVE_SOURCE", "VERIFYING_LIVE", "COMMITTED", "ROLLING_BACK", "ROLLED_BACK"].includes(state);
  const liveVerificationRan = ["VERIFYING_LIVE", "COMMITTED", "ROLLING_BACK", "ROLLED_BACK"].includes(state);
  return <section className="panel phase12-apply-evidence"><h2>{t(rolledBack ? "phase12.rollback.title" : "phase12.apply.transactionTitle")}</h2><dl className="truth-dl">
    <div><dt>{t("phase12.apply.candidateValidation")}</dt><dd>{t("phase12.value.passed")}</dd></div>
    <div><dt>{t("phase12.apply.liveFreshness")}</dt><dd>{t("phase12.value.passed")}</dd></div>
    <div><dt>{t("phase12.apply.safetySnapshot")}</dt><dd>{beforeMutation ? t("phase12.value.notCreated") : t("phase12.value.created")}</dd></div>
    <div><dt>{t("phase12.apply.journal")}</dt><dd>{journalCreated ? t("phase12.value.created") : t("phase12.value.notCreated")}</dd></div>
    <div><dt>{t("phase12.apply.apply")}</dt><dd>{mutationStarted ? t("phase12.value.complete") : t("phase12.value.notStarted")}</dd></div>
    <div><dt>{t("phase12.apply.liveVerification")}</dt><dd>{liveVerificationRan ? t("phase12.value.complete") : t("phase12.value.notStarted")}</dd></div>
    <div><dt>{t("phase12.apply.commit")}</dt><dd>{state === "COMMITTED" ? t("phase12.value.complete") : t("phase12.value.notStarted")}</dd></div>
    {rolledBack && <><div><dt>{t("phase12.rollback.paths_restored")}</dt><dd dir="ltr">{referenceFacts.restoredPath}</dd></div><div><dt>{t("phase12.rollback.byte_identity_result")}</dt><dd>{referenceFacts.verified}</dd></div><div><dt>{t("phase12.rollback.unrelated_path_result")}</dt><dd>{referenceFacts.unchanged}</dd></div></>}
  </dl></section>;
}

function Diagnostics({ t }: { t: T }) {
  const facts = [["signing", "AD_HOC_SIGNED"], ["developer_id", "NO"], ["notarized", "NO"], ["public_distribution", "NOT_READY"], ["updater_fixture", "PASS"], ["production_updater", "PRODUCTION_CHANNEL_UNPUBLISHED"]];
  return <section className="phase12-diagnostics-grid">{facts.map(([key, state]) => <article className="panel" key={key}><span>{t(`phase10.diagnostic.${key}`)}</span><strong>{statusLabel(t, state)}</strong><code dir="ltr">{state}</code></article>)}</section>;
}

function Updater({ t, state }: { t: T; state: string }) {
  const candidate = ["UPDATE_AVAILABLE", "DOWNLOADING", "VERIFYING_SIGNATURE", "INSTALLING", "UPDATED", "INVALID_SIGNATURE"].includes(state) ? referenceFacts.candidateVersion : "—";
  const progress = state === "DOWNLOADING" ? 46 : state === "UPDATED" ? 100 : state === "INVALID_SIGNATURE" ? 72 : 0;
  return <section className="panel phase12-updater"><div className="phase12-update-hero"><div><span>{t("phase12.updater.status")}</span><h2>{statusLabel(t, state)}</h2></div><span className={`phase12-update-orb ${state.toLowerCase()}`} aria-hidden="true" /></div><div className="phase12-progress" role="progressbar" aria-label={t("phase12.updater.progress")} aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}><span style={{ width: `${progress}%` }} /></div><dl className="truth-dl"><div><dt>{t("phase10.update.current")}</dt><dd dir="ltr">{referenceFacts.currentVersion}</dd></div><div><dt>{t("phase12.updater.candidate")}</dt><dd dir="ltr">{candidate}</dd></div><div><dt>{t("phase12.updater.platform")}</dt><dd dir="ltr">{referenceFacts.platform}</dd></div><div><dt>{t("phase10.update.signature")}</dt><dd>{t("phase12.updater.signatureRequired")}</dd></div><div><dt>{t("phase12.updater.data")}</dt><dd>{t("phase12.updater.dataPreserved")}</dd></div></dl></section>;
}

function ManualChecklist({ t }: { t: T }) {
  return <section className="panel phase12-manual"><h2>{t("phase12.manual.title")}</h2>{["tray", "close", "notification", "login", "sleep", "lock", "logout", "alias"].map((item) => <label key={item}><input type="checkbox" disabled /><span>{t(`phase12.manual.${item}`)}</span><strong>{t("phase12.manual.notRun")}</strong></label>)}</section>;
}

export function Phase12Capture({ state, t }: { state: Phase12CaptureState; t: T }) {
  const screen = truth[state];
  const [model, setModel] = useState<Record<string, Record<string, string[]>> | null>(null);
  const [modelError, setModelError] = useState(false);
  useEffect(() => { void getWorkflowStateModel().then(setModel).catch(() => setModelError(true)); }, []);
  const nextStates = useMemo(() => model?.[screen.machine]?.[screen.state] ?? [], [model, screen]);
  const transitionValid = useMemo(
    () => screen.previous === screen.state || Boolean(model?.[screen.machine]?.[screen.previous]?.includes(screen.state)),
    [model, screen],
  );
  const steps = stepsFor(screen);
  const position = Math.max(0, steps.indexOf(screen.state));
  const isHebrew = state.startsWith("3") && ["33", "34", "35", "36", "37"].includes(state.slice(0, 2));
  const actions = screen.category === "apply" && screen.state === "COMMITTED" ? ["returnProject", "viewEvidence", "viewTransaction"] : screen.category === "regression" ? ["runAgain", "openEvidence", "createRepair"] : screen.category === "capture" ? ["cancel", "review", "validate"] : screen.category === "updater" ? ["checkUpdate", "safeNext"] : ["openEvidence", "safeNext"];
  return <div className="phase12-surface" dir={isHebrew ? "rtl" : undefined} data-phase12-fixture="mellowyak.phase12.screenshots.v1" data-phase12-state={state} data-ready={model && transitionValid ? "true" : "false"}>
    <header className="phase12-heading"><div><span className="eyebrow">{t("phase12.eyebrow")}</span><h1>{t(`phase12.screen.${state}.title`)}</h1><p>{t(`phase12.screen.${state}.body`)}</p></div><div className={`phase12-state ${screen.tone}`} role="status" aria-live="polite"><span aria-hidden="true" /><div><small>{t("phase12.currentState")}</small><strong>{statusLabel(t, screen.state)}</strong><code dir="ltr">{screen.state}</code></div></div></header>
    <section className="phase12-identity panel"><div><span>{t("phase12.project")}</span><strong>{referenceFacts.projectName}</strong></div><div><span>{t("phase12.behavior")}</span><strong>{t("phase12.behavior.nearestRide")}</strong></div><div><span>{t("phase12.source")}</span><code dir="ltr">{referenceFacts.sourceIdentity}</code></div><div><span>{t("phase12.runtime")}</span><code dir="ltr">{referenceFacts.runtimeIdentity}</code></div></section>
    {screen.category === "runtime" && <RuntimeProfiles t={t} approved={state === "02-runtime-wizard-approved"} />}
    {screen.category === "apply" && <ApplyEvidence t={t} state={screen.state} />}
    {screen.category === "diagnostics" && <Diagnostics t={t} />}
    {screen.category === "updater" && <Updater t={t} state={screen.state} />}
    {screen.category === "manual" && <ManualChecklist t={t} />}
    {!(["runtime", "apply", "diagnostics", "updater", "manual"] as Category[]).includes(screen.category) && <section className="panel phase12-evidence"><div className="phase12-result"><span>{t("phase12.expected")}</span><strong>{t("phase12.expected.nearestDriver")}</strong></div><div className="phase12-result observed"><span>{t("phase12.observed")}</span><strong>{t(screen.tone === "bad" ? "phase12.observed.failed" : "phase12.observed.passed")}</strong></div><dl className="truth-dl"><div><dt>{t("phase12.baseline")}</dt><dd>{referenceFacts.pass}</dd></div><div><dt>{t("phase12.currentResult")}</dt><dd>{screen.tone === "bad" ? referenceFacts.repeatedFail : screen.state === "CAPTURING" ? t("phase12.value.notStarted") : referenceFacts.pass}</dd></div><div><dt>{t("phase12.externalNetwork")}</dt><dd>{t("phase12.none")}</dd></div><div><dt>{t("phase12.rootCause")}</dt><dd>{t("phase12.notClaimed")}</dd></div></dl></section>}
    <section className="panel phase12-timeline" aria-label={t("phase12.timeline")}><div className="section-head"><div><h2>{t("phase12.timeline")}</h2><p>{t("phase12.timeline.body")}</p></div><code dir="ltr">{screen.machine}</code></div><ol>{steps.map((step, index) => <li key={step} className={step === screen.state ? "current" : index < position ? "complete" : "pending"}><span aria-hidden="true">{index < position ? "✓" : index === position ? "●" : "○"}</span><div><strong>{statusLabel(t, step)}</strong><code dir="ltr">{step}</code></div></li>)}</ol></section>
    <div className="phase12-columns"><section className="panel"><h2>{t("phase12.transitionTruth")}</h2><dl className="truth-dl"><div><dt>{t("phase12.previousState")}</dt><dd>{statusLabel(t, screen.previous)}</dd></div><div><dt>{t("phase12.allowedNext")}</dt><dd>{nextStates.length ? nextStates.map((item) => statusLabel(t, item)).join(" · ") : t("phase12.terminalState")}</dd></div><div><dt>{t("phase12.sourceModified")}</dt><dd>{t(screen.sourceModified ? "phase12.yes" : "phase12.no")}</dd></div><div><dt>{t("phase12.fixtureMode")}</dt><dd>{t("phase12.fixtureActive")}</dd></div></dl></section><section className="panel"><h2>{t("phase10.knownLimits")}</h2><ul><li>{t("phase12.limit.referenceOnly")}</li><li>{t("phase12.limit.noRootCause")}</li><li>{t("phase12.limit.noExternalNetwork")}</li></ul>{modelError && <p role="alert">{t("phase12.modelUnavailable")}</p>}{model && !transitionValid && <p role="alert">{t("phase12.modelTransitionInvalid")}</p>}</section></div>
    <div className="button-row phase12-actions">{actions.map((action, index) => <button key={action} className={index === 0 ? "primary" : "secondary"}>{t(`phase12.action.${action}`)}</button>)}</div>
  </div>;
}
