import { useState } from "react";
import {
  createRepairWorkspace,
  createRepairCandidate,
  deleteRepairWorkspace,
  exportPortableRepair,
  getRepairCandidateDiff,
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
            {transaction && <div className="phase8-confirmation"><h3>{t("phase8.confirm.title")}</h3><p>{t("phase8.confirm.onlyCandidate")}</p><p>{t("phase8.confirm.safetySnapshot")}</p><p>{t("phase8.confirm.rollback")}</p><p>{t("phase8.confirm.unrelated")}</p><label><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} /> <span>{t("phase8.confirm.deliberate")}</span></label></div>}
            <div className="button-row"><button className="secondary" disabled={busy} onClick={() => void run(async () => { setValidation(null); setTransaction(null); setCandidate(await refreshRepairCandidate(projectId, candidate.id)); })}>{t("phase8.refreshCandidate")}</button><button className="secondary" disabled={busy} onClick={() => void run(async () => { await exportPortableRepair(projectId, workspace.id, candidate.files.filter((file) => !file.excluded).map((file) => file.relative_path)); })}>{t("phase8.portableExport")}</button>{candidate.state !== "VALIDATED" && <button className="primary" disabled={busy} onClick={() => void run(async () => { const result = await validateRepairCandidate(projectId, candidate.id); setValidation(result); setCandidate({ ...candidate, state: result.status === "PASSED" ? "VALIDATED" : "VALIDATION_FAILED" }); })}>{t("phase8.validateCandidate")}</button>}{candidate.state === "VALIDATED" && !transaction && <button className="primary" disabled={busy} onClick={() => void run(async () => setTransaction(await prepareRepairApply(projectId, candidate.id)))}>{t("phase8.prepareApply")}</button>}{transaction?.confirmation_nonce && <button className="primary" disabled={busy || !confirmed} onClick={() => void run(async () => setTransaction(await confirmRepairApply(projectId, candidate.id, transaction.confirmation_nonce ?? "")))}>{t("phase8.applyRepair")}</button>}</div>
          </>}
        </section>
        <details><summary>{t("common.technicalDetails")}</summary><pre dir="ltr">{JSON.stringify({ manifest_digest: workspace.manifest_digest, items: workspace.items }, null, 2)}</pre></details>
      </>}
  </section>;
}
