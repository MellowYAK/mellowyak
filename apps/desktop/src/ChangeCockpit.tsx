import { useEffect, useState } from "react";
import {
  cancelVerification,
  copyRepairContext,
  createProtectionPlan,
  createRepairContext,
  getGate,
  getEvidenceBundle,
  getProtectionPlan,
  listRegressions,
  openProjectFolder,
  openEvidenceArtifact,
  retryVerification,
  saveRepairContext,
  submitHumanResult,
  verifyRequired,
  type GateDecision,
  type ProtectionPlan,
  type RegressionFinding,
  type RepairContext,
  type VerificationRun,
} from "./api";
import type { TranslationKey } from "./i18n";
import { mascotAssets } from "./mascots";

type Translator = (key: TranslationKey, values?: Record<string, string | number>) => string;

const selectionKeys = {
  REQUIRED: "cockpit.selectionRequired",
  SUGGESTED: "cockpit.selectionSuggested",
  SKIPPED: "cockpit.selectionSkipped",
  NEEDS_REVIEW: "cockpit.selectionNeedsReview",
  UNKNOWN: "cockpit.selectionUnknown",
} as const satisfies Record<string, TranslationKey>;

const gateReasonKeys = {
  BLOCKED: "cockpit.gateBlocked",
  VERIFIED_COMPLETE: "cockpit.gateVerified",
  RECHECK_REQUIRED: "cockpit.gateRecheck",
  NEEDS_REVIEW: "cockpit.gateNeedsReview",
  STALE: "cockpit.gateStale",
  IN_PROGRESS: "cockpit.gateInProgress",
} as const satisfies Record<string, TranslationKey>;

export function ChangeCockpit({ projectId, changeId, impactReady, t, onError }: {
  projectId: string;
  changeId: string;
  impactReady: boolean;
  t: Translator;
  onError: (message: string) => void;
}) {
  const [plan, setPlan] = useState<ProtectionPlan | null>(null);
  const [run, setRun] = useState<VerificationRun | null>(null);
  const [gate, setGate] = useState<GateDecision | null>(null);
  const [regressions, setRegressions] = useState<RegressionFinding[]>([]);
  const [repair, setRepair] = useState<RepairContext | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    const [latestPlan, latestRegressions] = await Promise.all([
      getProtectionPlan(projectId, changeId).catch(() => null),
      listRegressions(projectId),
    ]);
    setPlan(latestPlan);
    setRegressions(latestRegressions.filter((item) => item.change_id === changeId));
    setGate(await getGate(projectId, changeId).catch(() => null));
  };

  useEffect(() => { void refresh().catch((reason) => onError(String(reason))); }, [changeId, projectId]);

  const action = async (operation: () => Promise<void>) => {
    setBusy(true);
    onError("");
    try { await operation(); } catch (reason) { onError(reason instanceof Error ? reason.message : String(reason)); }
    finally { setBusy(false); }
  };

  const latestRegression = regressions[0] ?? null;
  const mascot = gate?.state === "VERIFIED_COMPLETE"
    ? mascotAssets["yak-success-check"]
    : latestRegression ? mascotAssets["yak-alert-point"] : mascotAssets["yak-working-laptop"];

  return <section className="change-cockpit" aria-label={t("cockpit.title")}>
    <div className="cockpit-head panel">
      <div><div className="eyebrow">{t("cockpit.eyebrow")}</div><h2>{t("cockpit.title")}</h2><p>{t("cockpit.subtitle")}</p></div>
      <img className="mascot-helper-art" src={mascot.src} alt={t(mascot.altKey)} />
    </div>
    <div className="change-grid">
      <section className="panel"><h3>{t("cockpit.changedFiles")}</h3><p className="muted">{t("cockpit.changedFilesHint")}</p></section>
      <section className="panel"><h3>{t("cockpit.impactSummary")}</h3><p className="muted">{impactReady ? t("cockpit.impactReady") : t("cockpit.impactRequired")}</p></section>
      <section className="panel">
        <div className="section-head"><h3>{t("cockpit.protectionPlan")}</h3><button className="secondary" disabled={!impactReady || busy} onClick={() => void action(async () => { const value = await createProtectionPlan(projectId, changeId); setPlan(value); await refresh(); })}>{t("cockpit.createPlan")}</button></div>
        {plan ? <div className="cockpit-metrics"><span>{t("cockpit.protected", { count: plan.items.length })}</span><span>{t("cockpit.required", { count: plan.counts.required })}</span><span>{t("cockpit.suggested", { count: plan.counts.suggested })}</span><span>{t("cockpit.skipped", { count: plan.counts.skipped })}</span><span>{t("cockpit.unknown", { count: plan.counts.unknown })}</span></div> : <p className="muted">{t("cockpit.noPlan")}</p>}
      </section>
      <section className="panel"><h3>{t("cockpit.requiredChecks")}</h3>{plan?.items.filter((item) => item.selection_class === "REQUIRED").map((item) => <article className="cockpit-item" key={item.id}><strong>{item.behavior_name}</strong><span>{item.criticality} · {item.verification_method}</span><small>{t(selectionKeys[item.selection_class])}</small><button className="secondary" disabled={busy} onClick={() => void action(async () => { if (!plan) return; setRun(await verifyRequired(projectId, changeId, plan.id, [item.id])); await refresh(); })}>{t("cockpit.runOne")}</button></article>)}</section>
      <section className="panel"><h3>{t("cockpit.suggestedChecks")}</h3><span>{plan?.counts.suggested ?? 0}</span></section>
      <section className="panel"><h3>{t("cockpit.skippedBehaviors")}</h3><span>{plan?.counts.skipped ?? 0}</span></section>
      <section className="panel"><h3>{t("cockpit.boundaries")}</h3><span>{(plan?.counts.unknown ?? 0) + (plan?.counts.needs_review ?? 0)}</span></section>
      <section className="panel">
        <div className="section-head"><h3>{t("cockpit.runner")}</h3><button className="primary" disabled={!plan || busy} onClick={() => void action(async () => { if (!plan) return; const value = await verifyRequired(projectId, changeId, plan.id); setRun(value); await refresh(); })}>{t("cockpit.runRequired")}</button></div>
        {run && <><strong>{run.status}</strong>{run.items.map((item) => <article className="cockpit-item" key={item.id}><span>{item.result}</span><small>{t("cockpit.duration", { value: Math.round(item.duration_ms) })}</small>{item.evidence_bundle_id && <button className="secondary" onClick={() => void action(async () => { const bundle = await getEvidenceBundle(projectId, item.evidence_bundle_id!); if (bundle.items[0]) await openEvidenceArtifact(projectId, bundle.items[0].artifact.id); })}>{t("cockpit.openEvidence")}</button>}{item.result === "NEEDS_REVIEW" && <div className="mini-actions"><button onClick={() => void action(async () => { setRun(await submitHumanResult(projectId, run.id, item.id, "WORKS", t("cockpit.humanNote"))); await refresh(); })}>{t("cockpit.works")}</button><button onClick={() => void action(async () => { setRun(await submitHumanResult(projectId, run.id, item.id, "DOES_NOT_WORK", t("cockpit.humanNote"))); await refresh(); })}>{t("cockpit.doesNotWork")}</button><button onClick={() => void action(async () => { setRun(await submitHumanResult(projectId, run.id, item.id, "UNABLE_TO_DETERMINE", t("cockpit.humanNote"))); await refresh(); })}>{t("cockpit.unable")}</button></div>}</article>)}<div className="button-row">{run.status === "RUNNING" && <button className="secondary" onClick={() => void action(async () => { setRun(await cancelVerification(projectId, run.id)); await refresh(); })}>{t("cockpit.cancel")}</button>}<button className="secondary" onClick={() => void action(async () => { setRun(await retryVerification(projectId, run.id)); await refresh(); })}>{t("cockpit.retry")}</button></div></>}
      </section>
      <section className="panel regression-panel"><h3>{t("cockpit.regression")}</h3>{latestRegression ? <><strong>{t("cockpit.regressionDetected")}</strong><p>{t("cockpit.regressionReason")}</p><details><summary>{t("cockpit.sourceIdentity")}</summary><pre dir="ltr">{JSON.stringify(latestRegression.source_identity, null, 2)}</pre></details></> : <p className="muted">{t("cockpit.noRegression")}</p>}</section>
      <section className="panel"><div className="section-head"><h3>{t("cockpit.repairContext")}</h3><button className="secondary" disabled={!latestRegression || busy} onClick={() => void action(async () => { if (latestRegression) setRepair(await createRepairContext(projectId, latestRegression.id)); })}>{t("cockpit.createRepair")}</button></div>{repair && <><code dir="ltr">{repair.digest}</code><div className="button-row"><button onClick={() => void action(async () => { const text = await copyRepairContext(projectId, repair.id); await navigator.clipboard.writeText(text); })}>{t("cockpit.copyRepair")}</button><button onClick={() => void action(async () => { await saveRepairContext(projectId, repair.id); })}>{t("cockpit.saveRepair")}</button><button onClick={() => void openProjectFolder(projectId)}>{t("cockpit.openFiles")}</button></div></>}</section>
      <section className="panel"><h3>{t("cockpit.evidenceTimeline")}</h3><p className="muted">{t("cockpit.evidencePreserved")}</p></section>
      <section className={`panel gate-panel ${gate?.state === "BLOCKED" ? "error" : ""}`}><h3>{t("cockpit.gate")}</h3><strong>{gate?.state ?? t("cockpit.recheckRequired")}</strong><p>{gate ? t(gateReasonKeys[gate.state as keyof typeof gateReasonKeys] ?? "cockpit.gatePending") : t("cockpit.gatePending")}</p>{gate?.limitations.length ? <small>{t("cockpit.gateLimits")}</small> : null}</section>
    </div>
  </section>;
}
