import { useState } from "react";
import {
  createRepairWorkspace,
  createRepairCandidate,
  deleteRepairWorkspace,
  exportPortableRepair,
  getRepairCandidateDiff,
  getRepairApply,
  openRepairWorkspace,
  prepareRepairApply,
  refreshRepairCandidate,
  validateRepairCandidate,
  confirmRepairApply,
  type ApplyTransaction,
  type CandidateValidation,
  type RepairCandidate,
  type RepairWorkspace,
} from "./api";
import type { TranslationKey } from "./i18n";

export type Phase7Translator = (key: TranslationKey, values?: Record<string, string | number>) => string;

function applyProgressKey(state: string): TranslationKey {
  const keys: Record<string, TranslationKey> = {
    PREFLIGHT: "repairContract.progress.checkingSource",
    SAFETY_SNAPSHOT: "repairContract.progress.safetySnapshot",
    JOURNAL_CREATED: "repairContract.progress.transaction",
    PREPARING: "repairContract.progress.transaction",
    WRITING: "repairContract.progress.applying",
    CAPTURING_LIVE_SOURCE: "repairContract.progress.rechecking",
    VERIFYING_LIVE: "repairContract.progress.rechecking",
    ROLLING_BACK: "repairContract.progress.restoring",
  };
  return keys[state] ?? "repairContract.progress.waiting";
}

const limitationKeys: Record<string, TranslationKey> = {
  RUNTIME_SETUP_INCOMPLETE: "limitation.runtimeSetupIncomplete.title",
  RUNTIME_UNAVAILABLE: "limitation.runtimeUnavailable.title",
  AUTOMATIC_REPLAY_NOT_CONFIGURED: "limitation.automaticReplay.title",
  UNSUPPORTED_FILES: "limitation.unsupportedFiles.title",
  UNKNOWN_RELATIONSHIPS: "limitation.unknownRelationships.title",
  SNAPSHOT_STORAGE_LIMIT: "limitation.snapshotStorage.title",
  DEEP_OBSERVATION_UNAVAILABLE: "limitation.deepObservation.title",
};

function limitationPrefix(code: string): string {
  const key = limitationKeys[code] ?? "limitation.other.title";
  return key.slice(0, -".title".length);
}

export function ReadyWithLimitsDetails({ limitations, t }: { limitations: string[]; t: Phase7Translator }) {
  const [open, setOpen] = useState(false);
  if (!limitations.length) return <span className="readiness good">{t("readiness.ready")}</span>;
  return <div className="limits-control">
    <button className="readiness warn clickable" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
      {t("readiness.readyWithLimits")}
    </button>
    {open && <section className="limits-popover panel" aria-label={t("limits.title")}>
      <div className="section-head"><h2>{t("limits.title")}</h2><button className="secondary" onClick={() => setOpen(false)}>{t("common.close")}</button></div>
      <p className="muted">{t("limits.intro")}</p>
      <div className="limits-list">{limitations.map((code, index) => {
        const prefix = limitationPrefix(code);
        return <article key={`${code}-${index}`}>
          <strong>{t(`${prefix}.title` as TranslationKey)}</strong>
          <dl>
            <div><dt>{t("limits.meaning")}</dt><dd>{t(`${prefix}.meaning` as TranslationKey)}</dd></div>
            <div><dt>{t("limits.why")}</dt><dd>{t(`${prefix}.why` as TranslationKey)}</dd></div>
            <div><dt>{t("limits.stillWorks")}</dt><dd>{t(`${prefix}.stillWorks` as TranslationKey)}</dd></div>
            <div><dt>{t("limits.next")}</dt><dd>{t(`${prefix}.next` as TranslationKey)}</dd></div>
          </dl>
        </article>;
      })}</div>
    </section>}
  </div>;
}

const signalKeys: Record<string, TranslationKey> = {
  WATCH: "signal.watch",
  SUSPECTED: "signal.suspected",
  CONFIRMED: "signal.confirmed",
};

export function SignalExplanation({ state, reasonCodes = [], technical = {}, t }: {
  state: string;
  reasonCodes?: string[];
  technical?: Record<string, unknown>;
  t: Phase7Translator;
}) {
  const normalized = state.toUpperCase();
  const key = signalKeys[normalized] ?? "signal.unknown";
  return <section className={`signal-explanation signal-${normalized.toLowerCase()}`}>
    <strong>{t(key)}</strong>
    <p>{t(normalized === "CONFIRMED" ? "signal.confirmedBody" : normalized === "SUSPECTED" ? "signal.suspectedBody" : "signal.watchBody")}</p>
    <details><summary>{t("common.technicalDetails")}</summary><pre dir="ltr">{JSON.stringify({ reason_codes: reasonCodes, ...technical }, null, 2)}</pre></details>
  </section>;
}

export function RepairWorkspacePanel({ projectId, regressionId, initial, t, onError }: {
  projectId: string;
  regressionId: string;
  initial?: RepairWorkspace | null;
  t: Phase7Translator;
  onError: (code: string) => void;
}) {
  const [workspace, setWorkspace] = useState<RepairWorkspace | null>(initial ?? null);
  const [candidate, setCandidate] = useState<RepairCandidate | null>(null);
  const [validation, setValidation] = useState<CandidateValidation | null>(null);
  const [transaction, setTransaction] = useState<ApplyTransaction | null>(null);
  const [diff, setDiff] = useState<string[]>([]);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const awaitingConfirmation = transaction?.state === "AWAITING_CONFIRMATION";
  const committed = transaction?.state === "COMMITTED";
  const rolledBack = transaction?.state === "ROLLED_BACK";
  const run = async (operation: () => Promise<void>) => {
    setBusy(true);
    try { await operation(); }
    catch (reason) { onError(reason instanceof Error ? reason.message : "REPAIR_WORKSPACE_FAILED"); }
    finally { setBusy(false); }
  };
  return <section className="panel repair-workspace-panel">
    <div className="section-head"><div><h2>{t("repairWorkspace.title")}</h2><p className="muted">{t("repairWorkspace.description")}</p></div>{workspace && <span className="local-badge">{t("common.localOnly")}</span>}</div>
    {!workspace ? <button className="primary" disabled={busy} onClick={() => void run(async () => setWorkspace(await createRepairWorkspace(projectId, regressionId)))}>{busy ? t("common.working") : t("repairWorkspace.create")}</button>
      : <>
        <div className="status-row"><span>{t("repairWorkspace.snapshot")}</span><code dir="ltr">{workspace.snapshot_id.slice(0, 16)}</code></div>
        <div className="status-row"><span>{t("repairWorkspace.location")}</span><code dir="ltr">{workspace.relative_path}</code></div>
        <p className="privacy-note">{t("repairWorkspace.safety")}</p>
        <div className="button-row">
          <button className="secondary" disabled={busy} onClick={() => void run(async () => { await openRepairWorkspace(projectId, workspace.id); })}>{t("repairWorkspace.open")}</button>
          <button className="secondary danger" disabled={busy} onClick={() => void run(async () => { await deleteRepairWorkspace(projectId, workspace.id); setWorkspace(null); })}>{t("repairWorkspace.delete")}</button>
        </div>
        <section className="repair-candidate-flow">
          <div className="section-head"><div><h3>{t("phase8.candidateFiles")}</h3><p className="muted">{t("phase8.state.workspace-changes.body")}</p></div>{candidate && <span className={`readiness ${candidate.state === "VALIDATED" ? "good" : candidate.state === "VALIDATION_FAILED" ? "warn" : "neutral"}`}>{candidate.state}</span>}</div>
          {!candidate ? <button className="primary" disabled={busy} onClick={() => void run(async () => setCandidate(await createRepairCandidate(projectId, workspace.id)))}>{t("phase8.createCandidate")}</button> : <>
            <div className="phase8-identity-grid"><div><span>{t("phase8.candidateVersion")}</span><strong>R{candidate.revision}</strong></div><div><span>{t("phase8.workspaceIdentity")}</span><code dir="ltr">{candidate.workspace_manifest_digest.slice(0, 16)}</code></div><div><span>{t("phase8.totalBytes")}</span><strong>{candidate.logical_bytes}</strong></div><div><span>{t("phase8.binaryFiles")}</span><strong>{candidate.binary_count}</strong></div></div>
            <div className="phase8-files">{candidate.files.map((file) => <article key={`${file.ordinal}-${file.relative_path}`}><code dir="ltr">{file.relative_path}</code><span className={`operation ${file.operation.toLowerCase()}`}>{t(`phase8.operation.${file.operation}` as TranslationKey)}</span><small>{t("phase8.bytes", { count: file.byte_size })}</small><button className="secondary" disabled={file.classification.toLowerCase() !== "text"} onClick={() => void run(async () => setDiff((await getRepairCandidateDiff(projectId, candidate.id, file.relative_path)).lines))}>{t("phase8.viewDiff")}</button></article>)}</div>
            {diff.length > 0 && <pre className="phase8-diff" dir="ltr"><code>{diff.join("\n")}</code></pre>}
            {validation && <div className="analysis-banner"><strong>{t("phase8.validationResult")}</strong><span>{validation.status}</span><span>{t("phase8.validationChecks", { count: validation.items.length })}</span></div>}
            {transaction && <section className="phase8-confirmation" aria-live="polite">
              <div className="section-head"><h3>{awaitingConfirmation ? t("phase8.confirm.title") : t("phase12.apply.transactionTitle")}</h3><span className={`readiness ${committed ? "good" : rolledBack ? "warn" : "neutral"}`}>{t(`phase12.state.${transaction.state}` as TranslationKey)}</span></div>
              {awaitingConfirmation && <section className="repair-contract"><h3>{t("repairContract.verifiedTitle")}</h3><ul><li>{t("repairContract.testedAway")}</li><li>{t("repairContract.behaviorPassed")}</li><li>{t("repairContract.liveMatched")}</li></ul><p>{t("repairContract.explicit")}</p><p>{t("repairContract.recheck")}</p><p>{t("repairContract.rollback")}</p><div className="button-row"><button className="secondary" onClick={() => setDiff(candidate.files.flatMap((file) => file.relative_path))}>{t("repairContract.review")}</button></div></section>}
              {!awaitingConfirmation && !committed && !rolledBack && <p className="analysis-banner"><strong>{t(applyProgressKey(transaction.state))}</strong></p>}
              {committed && <section className="repair-contract success"><h3>{t("repairContract.protectedAgain")}</h3><ul><li>{t("repairContract.applied")}</li><li>{t("repairContract.livePassed")}</li><li>{t("repairContract.snapshotRetained")}</li></ul></section>}
              {transaction.state === "ROLLING_BACK" && <section className="repair-contract warning"><h3>{t("repairContract.liveFailed")}</h3><p>{t("repairContract.restoring")}</p></section>}
              {rolledBack && <section className="repair-contract success"><h3>{t("repairContract.restored")}</h3><p>{t("repairContract.nothingElse")}</p><p>{t("repairContract.candidateAvailable")}</p></section>}
              {awaitingConfirmation && <><p>{t("phase8.confirm.onlyCandidate")}</p><p>{t("phase8.confirm.safetySnapshot")}</p><p>{t("phase8.confirm.rollback")}</p><p>{t("phase8.confirm.unrelated")}</p></>}
              <dl className="truth-dl">
                <div><dt>{t("phase12.apply.candidateValidation")}</dt><dd>{t("phase12.value.passed")}</dd></div>
                <div><dt>{t("phase12.apply.liveFreshness")}</dt><dd>{t("phase12.value.passed")}</dd></div>
                <div><dt>{t("phase12.apply.safetySnapshot")}</dt><dd>{transaction.safety_snapshot_id ? t("phase12.value.created") : t("phase12.value.notCreated")}</dd></div>
                <div><dt>{t("phase12.apply.journal")}</dt><dd>{transaction.journal_relative_path ? t("phase12.value.created") : t("phase12.value.notCreated")}</dd></div>
                <div><dt>{t("phase12.apply.apply")}</dt><dd>{["WRITING", "CAPTURING_LIVE_SOURCE", "VERIFYING_LIVE", "COMMITTED", "ROLLING_BACK", "ROLLED_BACK"].includes(transaction.state) ? t("phase12.value.complete") : t("phase12.value.notStarted")}</dd></div>
                <div><dt>{t("phase12.apply.liveVerification")}</dt><dd>{["COMMITTED", "ROLLING_BACK", "ROLLED_BACK"].includes(transaction.state) ? t("phase12.value.complete") : t("phase12.value.notStarted")}</dd></div>
                <div><dt>{t("phase12.apply.commit")}</dt><dd>{committed ? t("phase12.value.complete") : t("phase12.value.notStarted")}</dd></div>
              </dl>
              {awaitingConfirmation && <label><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} /> <span>{t("phase8.confirm.deliberate")}</span></label>}
              {rolledBack && <section className="truth-limitations"><strong>{t("phase12.rollback.title")}</strong><dl className="truth-dl">{Object.entries(transaction.rollback_evidence).map(([key, value]) => <div key={key}><dt>{t(`phase12.rollback.${key}` as TranslationKey)}</dt><dd dir={key.includes("path") ? "ltr" : undefined}>{Array.isArray(value) ? value.join(", ") : String(value)}</dd></div>)}</dl></section>}
              <details><summary>{t("common.technicalDetails")}</summary><pre dir="ltr">{JSON.stringify({ id: transaction.id, state: transaction.state, events: transaction.events }, null, 2)}</pre></details>
            </section>}
            <div className="button-row"><button className="secondary" disabled={busy} onClick={() => void run(async () => { setValidation(null); setTransaction(null); setConfirmed(false); setCandidate(await refreshRepairCandidate(projectId, candidate.id)); })}>{t("phase8.refreshCandidate")}</button><button className="secondary" disabled={busy} onClick={() => void run(async () => { await exportPortableRepair(projectId, workspace.id, candidate.files.filter((file) => !file.excluded).map((file) => file.relative_path)); })}>{t("phase8.portableExport")}</button>{candidate.state !== "VALIDATED" && <button className="primary" disabled={busy} onClick={() => void run(async () => { const result = await validateRepairCandidate(projectId, candidate.id); setValidation(result); setCandidate({ ...candidate, state: result.status === "PASSED" ? "VALIDATED" : "VALIDATION_FAILED" }); })}>{t("phase8.validateCandidate")}</button>}{candidate.state === "VALIDATED" && !transaction && <button className="primary" disabled={busy} onClick={() => void run(async () => setTransaction(await prepareRepairApply(projectId, candidate.id)))}>{t("phase8.prepareApply")}</button>}{awaitingConfirmation && transaction.confirmation_nonce && <button className="primary" disabled={busy || !confirmed} onClick={() => void run(async () => { setTransaction(await confirmRepairApply(projectId, candidate.id, transaction.confirmation_nonce ?? "")); setConfirmed(false); })}>{t("phase8.applyRepair")}</button>}{transaction && !awaitingConfirmation && !committed && !rolledBack && <button className="secondary" disabled={busy} onClick={() => void run(async () => setTransaction(await getRepairApply(projectId, transaction.id)))}>{t("phase10.action.refresh")}</button>}{committed && <><button className="primary">{t("phase12.action.returnProject")}</button><button className="secondary">{t("phase12.action.viewEvidence")}</button><button className="secondary">{t("phase12.action.viewTransaction")}</button></>}</div>
          </>}
        </section>
        <details><summary>{t("common.technicalDetails")}</summary><pre dir="ltr">{JSON.stringify({ manifest_digest: workspace.manifest_digest, items: workspace.items }, null, 2)}</pre></details>
      </>}
  </section>;
}
