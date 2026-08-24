import { useEffect, useMemo, useState } from "react";
import {
  acceptBaseline,
  archiveBehavior,
  configureRuntime,
  createBehavior,
  deleteEvidenceArtifact,
  getEvidenceBundle,
  listBehaviors,
  listCaptures,
  listEvidence,
  listRuntimes,
  pauseCapture,
  resumeCapture,
  revokeBaseline,
  startCapture,
  stopCapture,
  submitCaptureReview,
  updateBehavior,
  type BrowserCapture,
  type EvidenceBundle,
  type ProtectedBehavior,
  type RuntimeConfiguration,
} from "./api";
import type { TranslationKey } from "./i18n";
import { mascotAssets } from "./mascots";

type Translator = (key: TranslationKey, values?: Record<string, string | number>) => string;

interface Props {
  projectId: string;
  initialBehaviorId: string | null;
  t: Translator;
  onError: (code: string) => void;
}

const emptyDraft = { title: "", description: "", expected_outcome: "", criticality: "MEDIUM", persona: "", preconditions: "" };

function failure(reason: unknown): string {
  return reason instanceof Error ? reason.message : "PHASE4_OPERATION_FAILED";
}

export function BehaviorsScreen({ projectId, initialBehaviorId, t, onError }: Props) {
  const [behaviors, setBehaviors] = useState<ProtectedBehavior[]>([]);
  const [runtimes, setRuntimes] = useState<RuntimeConfiguration[]>([]);
  const [captures, setCaptures] = useState<BrowserCapture[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(initialBehaviorId);
  const [draft, setDraft] = useState(emptyDraft);
  const [runtimeName, setRuntimeName] = useState("");
  const [runtimeUrl, setRuntimeUrl] = useState("");
  const [selectedRuntime, setSelectedRuntime] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [reviewNotes, setReviewNotes] = useState("");
  const [bundle, setBundle] = useState<EvidenceBundle | null>(null);
  const [stepLabels, setStepLabels] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    const [nextBehaviors, nextRuntimes, nextCaptures] = await Promise.all([
      listBehaviors(projectId),
      listRuntimes(projectId),
      listCaptures(projectId),
    ]);
    setBehaviors(nextBehaviors);
    setRuntimes(nextRuntimes);
    setCaptures(nextCaptures);
    setSelectedId((current) => current ?? nextBehaviors[0]?.id ?? null);
    setSelectedRuntime((current) => current || nextRuntimes[0]?.id || "");
  };

  useEffect(() => {
    void refresh().catch((reason) => onError(failure(reason)));
  }, [projectId]);

  useEffect(() => {
    if (initialBehaviorId) setSelectedId(initialBehaviorId);
  }, [initialBehaviorId]);

  const selected = useMemo(
    () => behaviors.find((behavior) => behavior.id === selectedId) ?? null,
    [behaviors, selectedId],
  );
  const behaviorCaptures = useMemo(
    () => captures.filter((capture) => capture.behavior_id === selectedId),
    [captures, selectedId],
  );
  const activeCapture = behaviorCaptures.find((capture) => capture.status === "RECORDING") ?? null;
  const reviewCapture = behaviorCaptures.find((capture) => capture.status === "REVIEW_REQUIRED") ?? null;

  const run = async (operation: () => Promise<void>) => {
    setBusy(true);
    onError("");
    try {
      await operation();
    } catch (reason) {
      onError(failure(reason));
    } finally {
      setBusy(false);
    }
  };

  const saveDraft = () => void run(async () => {
    const saved = selected
      ? await updateBehavior(projectId, selected.id, draft)
      : await createBehavior(projectId, draft);
    setSelectedId(saved.id);
    setDraft(emptyDraft);
    await refresh();
  });

  const editSelected = () => {
    if (!selected) return;
    setDraft({
      title: selected.current_version.title,
      description: selected.current_version.description,
      expected_outcome: selected.current_version.expected_outcome,
      criticality: selected.current_version.criticality,
      persona: selected.current_version.persona,
      preconditions: selected.current_version.preconditions,
    });
  };

  const saveRuntime = () => void run(async () => {
    const saved = await configureRuntime(projectId, runtimeName, runtimeUrl);
    setSelectedRuntime(saved.id);
    setRuntimeName("");
    setRuntimeUrl("");
    await refresh();
  });

  const beginCapture = () => void run(async () => {
    if (!selected || !selectedRuntime) return;
    await startCapture(projectId, selected.id, selectedRuntime);
    await refresh();
  });

  const finishCapture = () => void run(async () => {
    if (!activeCapture) return;
    const stopped = await stopCapture(projectId, activeCapture.id);
    const evidence = await listEvidence(projectId);
    const captureBundle = evidence.bundles.find((item) => item.capture_id === stopped.id);
    if (captureBundle) setBundle(await getEvidenceBundle(projectId, captureBundle.id));
    await refresh();
  });

  const updateReviewStep = (stepId: string, included: boolean) => void run(async () => {
    if (!reviewCapture) return;
    await submitCaptureReview(projectId, reviewCapture.id, reviewCapture.expected_assertions, reviewNotes, [{ id: stepId, included, label: stepLabels[stepId] }]);
    await refresh();
  });

  const excludeObservation = (observationId: string) => void run(async () => {
    if (!reviewCapture) return;
    await submitCaptureReview(projectId, reviewCapture.id, reviewCapture.expected_assertions, reviewNotes, [], [observationId]);
    await refresh();
  });

  const removeReviewArtifact = (artifactId: string) => void run(async () => {
    await deleteEvidenceArtifact(projectId, artifactId);
    if (bundle) setBundle(await getEvidenceBundle(projectId, bundle.id));
  });

  const approveBaseline = () => void run(async () => {
    if (!reviewCapture) return;
    await submitCaptureReview(projectId, reviewCapture.id, [{
      type: "HUMAN_NOTE",
      value: selected?.current_version.expected_outcome ?? "",
    }], reviewNotes);
    const result = await acceptBaseline(
      projectId,
      reviewCapture.id,
      reviewer,
      reviewNotes,
    );
    setBundle(await getEvidenceBundle(projectId, result.evidence_bundle_id));
    setReviewer("");
    setReviewNotes("");
    await refresh();
  });

  const openBundle = (bundleId: string) => void run(async () => {
    setBundle(await getEvidenceBundle(projectId, bundleId));
  });
  const summary = {
    total: behaviors.length,
    draft: behaviors.filter((item) => item.lifecycle_state === "DRAFT").length,
    protected: behaviors.filter((item) => item.lifecycle_state === "PROTECTED").length,
    stale: captures.filter((item) => item.status === "STALE_SOURCE").length,
    runtimeMissing: runtimes.length ? 0 : behaviors.length,
  };

  return <>
    <section className="page-head">
      <div>
        <div className="eyebrow">{t("behavior.eyebrow")}</div>
        <h1>{t("behavior.title")}</h1>
        <p>{t("behavior.subtitle")}</p>
      </div>
      <span className="local-badge">{t("common.localOnly")}</span>
    </section>
    <section className="metric-grid behavior-summary" aria-label={t("behavior.summary")}>
      <div><strong>{summary.total}</strong><span>{t("behavior.summaryTotal")}</span></div>
      <div><strong>{summary.draft}</strong><span>{t("behavior.summaryDraft")}</span></div>
      <div><strong>{summary.protected}</strong><span>{t("behavior.summaryProtected")}</span></div>
      <div><strong>{summary.stale}</strong><span>{t("behavior.summaryStale")}</span></div>
      <div><strong>{summary.runtimeMissing}</strong><span>{t("behavior.summaryRuntime")}</span></div>
    </section>
    <div className="behavior-workspace">
      <aside className="panel behavior-sidebar">
        <div className="section-head">
          <h2>{t("behavior.list")}</h2>
          <button className="secondary" onClick={() => { setSelectedId(null); setDraft(emptyDraft); }}>
            {t("behavior.new")}
          </button>
        </div>
        {behaviors.length ? behaviors.map((behavior) =>
          <button
            className={`behavior-row ${selectedId === behavior.id ? "active" : ""}`}
            key={behavior.id}
            onClick={() => setSelectedId(behavior.id)}
          >
            <strong>{behavior.current_version.title}</strong>
            <small>{t(`behavior.state.${behavior.lifecycle_state}` as TranslationKey)}</small>
          </button>) : <div className="mascot-helper"><img className="mascot-art mascot-helper-art" src={mascotAssets["yak-wave"].src} alt={t(mascotAssets["yak-wave"].altKey)} /><p className="muted">{t("behavior.empty")}</p></div>}
      </aside>
      <div className="behavior-main">
        <section className="panel behavior-editor">
          <div className="section-head">
            <h2>{selected ? t("behavior.edit") : t("behavior.create")}</h2>
            {selected && <button className="secondary" onClick={editSelected}>{t("behavior.loadCurrent")}</button>}
          </div>
          <label className="field"><span>{t("behavior.name")}</span><input value={draft.title} maxLength={240} onChange={(event) => setDraft({ ...draft, title: event.target.value })} /></label>
          <label className="field"><span>{t("behavior.description")}</span><textarea value={draft.description} maxLength={4000} onChange={(event) => setDraft({ ...draft, description: event.target.value })} /></label>
          <label className="field"><span>{t("behavior.expected")}</span><textarea value={draft.expected_outcome} maxLength={4000} onChange={(event) => setDraft({ ...draft, expected_outcome: event.target.value })} /></label>
          <label className="field"><span>{t("behavior.criticality")}</span><select value={draft.criticality} onChange={(event) => setDraft({ ...draft, criticality: event.target.value })}>{(["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const).map((value) => <option value={value} key={value}>{t(`behavior.criticality.${value}` as TranslationKey)}</option>)}</select></label>
          <label className="field"><span>{t("behavior.persona")}</span><input value={draft.persona} maxLength={500} onChange={(event) => setDraft({ ...draft, persona: event.target.value })} /></label>
          <label className="field"><span>{t("behavior.preconditions")}</span><textarea value={draft.preconditions} maxLength={4000} onChange={(event) => setDraft({ ...draft, preconditions: event.target.value })} /></label>
          <div className="button-row"><button className="primary" disabled={busy || !draft.title.trim() || selected?.lifecycle_state === "ARCHIVED"} onClick={saveDraft}>{busy ? t("common.working") : selected ? t("behavior.saveVersion") : t("behavior.createDraft")}</button></div>
        </section>
        {selected && <>
          <section className="panel">
            <div className="section-head"><h2>{t("behavior.current")}</h2><span className={`readiness ${selected.lifecycle_state === "PROTECTED" ? "good" : "neutral"}`}>{t(`behavior.state.${selected.lifecycle_state}` as TranslationKey)}</span></div>
            <h3>{selected.current_version.title}</h3>
            <p>{selected.current_version.description || t("behavior.noDescription")}</p>
            <p className="privacy-note"><strong>{t("behavior.expected")}</strong><span>{selected.current_version.expected_outcome || t("behavior.noExpected")}</span></p>
            <div className="metric-grid"><div><strong>{t(`behavior.criticality.${selected.current_version.criticality}` as TranslationKey)}</strong><span>{t("behavior.criticality")}</span></div><div><strong>{t("behavior.verificationNotConfigured")}</strong><span>{t("behavior.automaticVerification")}</span></div></div>
            {selected.last_accepted_baseline_id && <div className="analysis-banner"><strong>{t("behavior.lastKnownGood")}</strong><span>{t("behavior.acceptedIdentity", { head: String(selected.current_version.source_revision.head_sha ?? t("common.unknown")), fingerprint: String(selected.current_version.source_revision.worktree_fingerprint ?? t("common.unknown")) })}</span></div>}
            <div className="button-row"><button className="secondary danger" disabled={busy || selected.lifecycle_state === "ARCHIVED"} onClick={() => void run(async () => { await archiveBehavior(projectId, selected.id); await refresh(); })}>{t("behavior.archive")}</button></div>
            <details><summary>{t("behavior.versionHistory")}</summary><ol className="compact-list">{selected.versions.map((version) => <li key={version.id}>{t("behavior.version", { number: version.version_number })} · {version.title}</li>)}</ol></details>
          </section>
          <section className="panel runtime-panel">
            <div className="section-head"><h2>{t("runtime.title")}</h2><span>{runtimes.length}</span></div>
            <p className="muted">{t("runtime.security")}</p>
            <div className="inline-form">
              <label className="field"><span>{t("runtime.name")}</span><input value={runtimeName} onChange={(event) => setRuntimeName(event.target.value)} /></label>
              <label className="field"><span>{t("runtime.url")}</span><input dir="ltr" value={runtimeUrl} placeholder={t("runtime.placeholder")} onChange={(event) => setRuntimeUrl(event.target.value)} /></label>
              <button className="secondary" disabled={busy || !runtimeName.trim() || !runtimeUrl.trim()} onClick={saveRuntime}>{t("runtime.save")}</button>
            </div>
            {runtimes.length > 0 && <label className="field"><span>{t("runtime.captureWith")}</span><select value={selectedRuntime} onChange={(event) => setSelectedRuntime(event.target.value)}>{runtimes.map((runtime) => <option value={runtime.id} key={runtime.id}>{runtime.display_name} · {runtime.allowed_origin}</option>)}</select></label>}
          </section>
          <section className="panel capture-panel">
            <div className="section-head"><h2>{t("capture.title")}</h2><span>{behaviorCaptures.length}</span></div>
            <p className="muted">{t("capture.description")}</p>
            {!activeCapture && !reviewCapture && <button className="primary" disabled={busy || !selectedRuntime || selected.lifecycle_state === "ARCHIVED"} onClick={beginCapture}>{t("capture.start")}</button>}
            {activeCapture && <div className="capture-live" role="status"><img className="mascot-art mascot-helper-art" src={mascotAssets["yak-working-laptop"].src} alt={t(mascotAssets["yak-working-laptop"].altKey)} /><strong>{t("capture.recording")}</strong><span>{activeCapture.entry_url}</span><div className="metric-grid"><div><strong>{activeCapture.steps.length}</strong><span>{t("capture.steps")}</span></div><div><strong>{activeCapture.observations.length}</strong><span>{t("capture.observations")}</span></div><div><strong>{t("common.localOnly")}</strong><span>{t("capture.privacy")}</span></div></div><div className="button-row"><button className="secondary" disabled={busy} onClick={() => void run(async () => { activeCapture.paused ? await resumeCapture(projectId, activeCapture.id) : await pauseCapture(projectId, activeCapture.id); await refresh(); })}>{activeCapture.paused ? t("capture.resume") : t("capture.pause")}</button><button className="primary" disabled={busy} onClick={finishCapture}>{t("capture.stopReview")}</button></div></div>}
            {reviewCapture && <div className="capture-review">
              <div className="analysis-banner"><strong>{t("capture.reviewRequired")}</strong><span>{t("capture.reviewNotice")}</span></div>
              <div className="metric-grid"><div><strong>{reviewCapture.steps.length}</strong><span>{t("capture.steps")}</span></div><div><strong>{reviewCapture.observations.length}</strong><span>{t("capture.observations")}</span></div></div>
              <ol className="compact-list">{reviewCapture.steps.map((step) => <li key={step.id}><strong>{step.ordinal}. {step.event_type}</strong><code dir="ltr">{step.selector ?? step.page_url}</code><input aria-label={t("capture.stepLabel")} value={stepLabels[step.id] ?? step.label} onChange={(event) => setStepLabels({ ...stepLabels, [step.id]: event.target.value })} /><button className="secondary" disabled={busy} onClick={() => updateReviewStep(step.id, !step.included)}>{step.included ? t("capture.excludeStep") : t("capture.includeStep")}</button></li>)}</ol>
              <ul className="compact-list">{reviewCapture.observations.map((observation) => <li key={observation.id}><code>{observation.observation_type}</code><button className="secondary" disabled={busy || !observation.included} onClick={() => excludeObservation(observation.id)}>{observation.included ? t("capture.excludeObservation") : t("capture.excluded")}</button></li>)}</ul>
              {bundle?.status === "CAPTURED" && <div className="bundle-details"><h3>{t("capture.reviewArtifacts")}</h3>{bundle.items.map((item) => <article key={item.ordinal}><strong>{t(`evidence.type.${item.item_type}` as TranslationKey)}</strong><span>{t("evidence.bytes", { count: item.artifact.size_bytes })}</span>{item.item_type.includes("screenshot") && <button className="secondary danger" disabled={busy} onClick={() => removeReviewArtifact(item.artifact.id)}>{t("capture.deleteScreenshot")}</button>}</article>)}</div>}
              <p className="muted">{t("capture.noVerdict")}</p>
              <p className="privacy-note">{t("capture.screenshotWarning")}</p>
              <label className="field"><span>{t("capture.reviewer")}</span><input value={reviewer} onChange={(event) => setReviewer(event.target.value)} /></label>
              <label className="field"><span>{t("capture.notes")}</span><textarea value={reviewNotes} onChange={(event) => setReviewNotes(event.target.value)} /></label>
              <button className="primary" disabled={busy || !reviewer.trim()} onClick={approveBaseline}>{t("capture.accept")}</button>
            </div>}
            {behaviorCaptures.filter((capture) => capture.status !== "RECORDING" && capture.status !== "REVIEW_REQUIRED").map((capture) => <article className="capture-history" key={capture.id}><span>{t(`capture.state.${capture.status}` as TranslationKey)}</span><code dir="ltr">{capture.entry_url}</code></article>)}
          </section>
          <section className="panel evidence-panel">
            <div className="section-head"><h2>{t("evidence.title")}</h2><span>{selected.baselines.length}</span></div>
            <p className="muted">{t("evidence.description")}</p>
            {selected.baselines.map((baseline) => <button className="evidence-row" key={baseline.id} onClick={() => openBundle(baseline.evidence_bundle_id)}><strong>{t("evidence.acceptedBaseline")}</strong><small>{baseline.evidence_bundle_id}</small></button>)}
            {!selected.baselines.length && <p className="muted">{t("evidence.empty")}</p>}
            {bundle && <div className="bundle-details"><h3>{t("evidence.bundle")}</h3><code dir="ltr">{bundle.manifest_sha256}</code>{bundle.items.map((item) => <article key={item.ordinal}><strong>{t(`evidence.type.${item.item_type}` as TranslationKey)}</strong><span>{t("evidence.bytes", { count: item.artifact.size_bytes })}</span><code dir="ltr">{item.artifact.sha256}</code><em>{item.artifact.integrity_verified ? t("evidence.integrityVerified") : t("evidence.integrityFailed")}</em></article>)}</div>}
            {selected.last_accepted_baseline_id && <button className="secondary danger" disabled={busy} onClick={() => void run(async () => { await revokeBaseline(projectId, selected.id); setBundle(null); await refresh(); })}>{t("evidence.revoke")}</button>}
          </section>
        </>}
      </div>
    </div>
  </>;
}
