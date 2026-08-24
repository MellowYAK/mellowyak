import { open } from "@tauri-apps/plugin-dialog";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  analyzeChange,
  cancelProjectScan,
  createContextReceipt,
  createProject,
  detectProject,
  getChangeImpact,
  getCurrentChange,
  getImpactSummary,
  getImpactPaths,
  getProject,
  listBehaviorCandidates,
  listBehaviors,
  listProjects,
  loadStartup,
  openDataFolder,
  openProjectFolder,
  searchImpact,
  setChangeIntent,
  setProjectMonitoring,
  startProjectScan,
  updateBehaviorCandidate,
  type BehaviorCandidate,
  type Change,
  type ChangeImpact,
  type ContextReceipt,
  type ImpactExplorerItem,
  type ImpactSummary,
  type Project,
  type ProjectDetection,
  type ProtectedBehavior,
  type SetupSnapshot,
  type StartupStatus,
} from "./api";
import { useI18n, type Locale } from "./i18n";
import { mascotAssets, type MascotId } from "./mascots";
import { BehaviorsScreen } from "./BehaviorsScreen";
import { StartupAnimation, startupStepKeys } from "./StartupAnimation";
import { useDesktopUpdater, type UpdaterState } from "./updater";

type Screen = "home" | "add" | "project" | "change" | "impact" | "behaviors";
type Tone = "good" | "warn" | "neutral";

function StatusRow({ label, value, tone = "neutral" }: { label: string; value: string; tone?: Tone }) {
  return <div className="status-row"><span>{label}</span><strong className={tone}>{value}</strong></div>;
}

function Tags({ values, empty }: { values: string[]; empty: string }) {
  return values.length
    ? <div className="tags">{values.map((value) => <span key={value}>{value}</span>)}</div>
    : <p className="muted">{empty}</p>;
}

type Translator = ReturnType<typeof useI18n>["t"];

function MascotArt({ pose, t, className = "" }: { pose: MascotId; t: Translator; className?: string }) {
  const asset = mascotAssets[pose];
  return <img className={`mascot-art ${className}`} src={asset.src} alt={t(asset.altKey)} />;
}

function readiness(project: Project, t: Translator): { label: string; tone: Tone } {
  if (!project.git.available) return { label: t("readiness.gitUnavailable"), tone: "warn" };
  if (!project.scan || project.scan.status === "running") return { label: t("readiness.scanIncomplete"), tone: "neutral" };
  if (project.scan.status !== "completed") return { label: t("readiness.scanIncomplete"), tone: "warn" };
  if (project.scan.failed_files || project.scan.unknown_items || project.scan.unsupported_files) {
    return { label: t("readiness.readyWithLimits"), tone: "warn" };
  }
  return { label: t("readiness.ready"), tone: "good" };
}

function Header({ home, locale, setLocale, t, updater }: { home: () => void; locale: Locale; setLocale: (locale: Locale) => void; t: Translator; updater: UpdaterState }) {
  return <><header className="brand-bar">
      <button className="brand-button" onClick={home} aria-label={t("brand.home")}><span className="mark">{t("brand.mark")}</span></button>
      <div><div className="brand-name">{t("brand.name")}</div><div className="tagline">{t("brand.tagline")}</div></div>
      <div className="principle">{t("brand.principle")}</div>
      <label className="language-picker"><span>{t("language.label")}</span><select aria-label={t("language.label")} value={locale} onChange={(event) => setLocale(event.target.value as Locale)}><option value="en">{t("language.en")}</option><option value="he">{t("language.he")}</option></select></label>
    </header>{updater.phase !== "idle" && <section className="update-banner" role="status"><div><strong>{t("update.availableTitle")}</strong><span>{updater.phase === "available" ? t("update.availableBody", { version: updater.version ?? t("common.unknown") }) : updater.phase === "installing" ? t("update.installing") : t("update.relaunching")}</span></div><button className="primary" disabled={updater.phase !== "available"} onClick={() => void updater.install()}>{updater.phase === "available" ? t("update.install") : updater.phase === "installing" ? t("update.installing") : t("update.relaunching")}</button></section>}</>;
}

function ProjectNav({ active, select, t }: { active: "overview" | "change" | "impact" | "behaviors"; select: (screen: "project" | "change" | "impact" | "behaviors") => void; t: Translator }) {
  return <nav className="project-nav" aria-label={t("nav.overview")}>
    <button className={active === "overview" ? "active" : ""} onClick={() => select("project")}>{t("nav.overview")}</button>
    <button className={active === "change" ? "active" : ""} onClick={() => select("change")}>{t("nav.changes")}</button>
    <button className={active === "impact" ? "active" : ""} onClick={() => select("impact")}>{t("nav.impact")}</button>
    <button className={active === "behaviors" ? "active" : ""} onClick={() => select("behaviors")}>{t("nav.behaviors")}</button>
  </nav>;
}

const startupSteps = ["starting", "loading_database", "loading_capabilities", "discovering_projects", "finalizing"] as const;

function StartupScreen({ status, failedStep, leaving, error, slow, retry, locale, setLocale, t, errorText, updater }: {
  status: StartupStatus;
  failedStep: Exclude<StartupStatus, "ready" | "error">;
  leaving: boolean;
  error: string;
  slow: boolean;
  retry: () => void;
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: Translator;
  errorText: (value: string) => string;
  updater: UpdaterState;
}) {
  const visibleStep = status === "error" ? failedStep : status;
  const activeIndex = status === "ready" ? startupSteps.length : Math.max(0, startupSteps.indexOf(visibleStep as typeof startupSteps[number]));
  const progress = status === "ready" ? 100 : activeIndex * 20;
  const operation = status === "ready" ? t("startup.everythingReady") : status === "error" ? t("startup.failedOperation") : t(startupStepKeys[status]);
  return <main className="app-shell startup-shell" dir={locale === "he" ? "rtl" : "ltr"}>
    <Header home={() => undefined} locale={locale} setLocale={setLocale} t={t} updater={updater} />
    <section className={`startup-card ${status === "error" ? "startup-error" : ""} ${leaving ? "leaving" : ""}`} aria-busy={status !== "ready" && status !== "error"}>
      <StartupAnimation status={status} alt={t("startup.mascotAlt")} />
      <div className="startup-copy">
        <div className="eyebrow">{t("startup.eyebrow")}</div>
        <h1>{status === "ready" ? t("startup.readyTitle") : status === "error" ? t("startup.errorTitle") : t("startup.title")}</h1>
        <p>{status === "error" ? t("startup.errorBody") : t("startup.explanation")}</p>
      </div>
      <div className="startup-operation" role="status" aria-live="polite"><span className="activity-dot" aria-hidden="true" />{operation}</div>
      <div className="startup-progress-row"><div className="startup-progress" role="progressbar" aria-label={t("startup.progressLabel")} aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}><span style={{ width: `${progress}%` }} /></div><strong>{t("startup.progressValue", { progress })}</strong></div>
      <ol className="startup-checklist">
        {startupSteps.map((step, index) => {
          const stepState = index < activeIndex || status === "ready" ? "complete" : index === activeIndex ? status === "error" ? "failed" : "active" : "pending";
          const marker = stepState === "complete" ? "✓" : stepState === "failed" ? "!" : stepState === "active" ? "●" : "○";
          return <li key={step} className={stepState}><span aria-hidden="true">{marker}</span><span>{t(startupStepKeys[step])}</span></li>;
        })}
      </ol>
      {slow && status !== "ready" && status !== "error" && <p className="startup-slow" role="status">{t("startup.slow")}</p>}
      {status === "error" && <div className="startup-recovery"><button className="primary" onClick={retry}>{t("startup.retry")}</button><details><summary>{t("startup.details")}</summary><pre dir="ltr">{errorText(error)}</pre></details></div>}
      <footer className="startup-privacy">{t("startup.privacy")}</footer>
    </section>
  </main>;
}

export function App() {
  const { locale, direction, setLocale, status, errorText, t } = useI18n();
  const updater = useDesktopUpdater();
  const [snapshot, setSnapshot] = useState<SetupSnapshot | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selected, setSelected] = useState<Project | null>(null);
  const [impact, setImpact] = useState<ImpactSummary | null>(null);
  const [currentChange, setCurrentChange] = useState<Change | null>(null);
  const [changeImpact, setChangeImpact] = useState<ChangeImpact | null>(null);
  const [impactPaths, setImpactPaths] = useState<Array<Record<string, unknown>>>([]);
  const [receipt, setReceipt] = useState<ContextReceipt | null>(null);
  const [candidates, setCandidates] = useState<BehaviorCandidate[]>([]);
  const [knownBehaviors, setKnownBehaviors] = useState<ProtectedBehavior[]>([]);
  const [taskIntent, setTaskIntent] = useState("");
  const [impactQuery, setImpactQuery] = useState("");
  const [impactResults, setImpactResults] = useState<ImpactExplorerItem[]>([]);
  const [detection, setDetection] = useState<ProjectDetection | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [monitoring, setMonitoring] = useState<"passive" | "paused">("passive");
  const [screen, setScreen] = useState<Screen>("home");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [startupStatus, setStartupStatus] = useState<StartupStatus>("starting");
  const [startupFailedStep, setStartupFailedStep] = useState<Exclude<StartupStatus, "ready" | "error">>("starting");
  const [startupError, setStartupError] = useState("");
  const [startupVisible, setStartupVisible] = useState(true);
  const [startupLeaving, setStartupLeaving] = useState(false);
  const [startupSlow, setStartupSlow] = useState(false);
  const [startupAttempt, setStartupAttempt] = useState(0);
  const [focusBehaviorId, setFocusBehaviorId] = useState<string | null>(null);

  const reloadProjects = useCallback(async () => setProjects(await listProjects()), []);

  useEffect(() => {
    let active = true;
    const timers: number[] = [];
    let currentStep: Exclude<StartupStatus, "ready" | "error"> = "starting";
    const startedAt = Date.now();
    setSnapshot(null);
    setProjects([]);
    setStartupError("");
    setStartupSlow(false);
    setStartupLeaving(false);
    setStartupStatus("starting");
    setStartupVisible(true);
    timers.push(window.setTimeout(() => active && setStartupSlow(true), 10_000));
    loadStartup((next) => { currentStep = next; if (active) setStartupStatus(next); })
      .then(({ snapshot: setup, projects: saved }) => {
        if (!active) return;
        setSnapshot(setup);
        setProjects(saved);
        const minimumRemaining = Math.max(0, 800 - (Date.now() - startedAt));
        timers.push(window.setTimeout(() => {
          if (!active) return;
          setStartupStatus("ready");
          timers.push(window.setTimeout(() => {
            if (!active) return;
            setStartupLeaving(true);
            timers.push(window.setTimeout(() => active && setStartupVisible(false), 180));
          }, 450));
        }, minimumRemaining));
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setStartupError(reason instanceof Error ? reason.message : "LOCAL_ENGINE_UNAVAILABLE");
        setStartupFailedStep(currentStep);
        setStartupStatus("error");
      });
    return () => { active = false; timers.forEach((timer) => window.clearTimeout(timer)); };
  }, [startupAttempt]);

  useEffect(() => {
    if (screen !== "project" || !selected) return;
    let active = true;
    const refresh = async () => {
      try {
        const [project, summary] = await Promise.all([getProject(selected.id), getImpactSummary(selected.id)]);
        if (!active) return;
        setSelected(project);
        setImpact(summary);
        setProjects((items) => items.map((item) => item.id === project.id ? project : item));
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : "PROJECT_REFRESH_FAILED");
      }
    };
    void refresh();
    const interval = window.setInterval(() => void refresh(), selected.scan?.status === "running" || !selected.scan ? 750 : 5000);
    return () => { active = false; window.clearInterval(interval); };
  }, [screen, selected?.id, selected?.scan?.status]);

  useEffect(() => {
    if (screen !== "change" || !selected) return;
    let active = true;
    Promise.all([getProject(selected.id), getCurrentChange(selected.id), listBehaviorCandidates(selected.id), listBehaviors(selected.id)])
      .then(async ([project, change, behaviorCandidates, protectedBehaviors]) => {
        if (!active) return;
        setSelected(project); setCurrentChange(change); setTaskIntent(change.task_intent ?? ""); setCandidates(behaviorCandidates); setKnownBehaviors(protectedBehaviors);
        try {
          const [analysis, paths] = await Promise.all([getChangeImpact(project.id, change.id), getImpactPaths(project.id, change.id)]);
          if (active) { setChangeImpact(analysis); setImpactPaths(paths); }
        } catch { if (active) { setChangeImpact(null); setImpactPaths([]); } }
      })
      .catch((reason: unknown) => active && setError(reason instanceof Error ? reason.message : "CHANGE_LOAD_FAILED"));
    return () => { active = false; };
  }, [screen, selected?.id]);

  const home = () => {
    setScreen("home"); setDetection(null); setError(""); setCurrentChange(null); setChangeImpact(null); setReceipt(null);
    void reloadProjects().catch(() => undefined);
  };

  const selectProjectScreen = (next: "project" | "change" | "impact" | "behaviors") => {
    setError(""); setScreen(next);
  };

  const runAnalysis = async () => {
    if (!selected || !currentChange) return;
    setBusy(true); setError("");
    try {
      const changed = await setChangeIntent(selected.id, currentChange.id, taskIntent);
      const [analysis, paths, behaviorCandidates] = await Promise.all([
        analyzeChange(selected.id, changed.id), getImpactPaths(selected.id, changed.id), listBehaviorCandidates(selected.id),
      ]);
      setCurrentChange(changed); setChangeImpact(analysis); setImpactPaths(paths); setCandidates(behaviorCandidates); setReceipt(null);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "IMPACT_ANALYSIS_FAILED"); }
    finally { setBusy(false); }
  };

  const generateReceipt = async () => {
    if (!selected || !currentChange) return;
    setBusy(true); setError("");
    try { setReceipt(await createContextReceipt(selected.id, currentChange.id)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "CONTEXT_RECEIPT_FAILED"); }
    finally { setBusy(false); }
  };

  const copyReceipt = async () => {
    if (receipt) await navigator.clipboard.writeText(JSON.stringify(receipt, null, 2));
  };

  const changeCandidate = async (candidate: BehaviorCandidate, action: "keep" | "dismiss" | "prepare") => {
    if (!selected) return;
    try {
      const updated = await updateBehaviorCandidate(selected.id, candidate.id, action);
      setCandidates((items) => items.map((item) => item.id === candidate.id ? { ...item, ...updated } : item));
      if (action === "prepare" && updated.behavior_draft_id) {
        setFocusBehaviorId(updated.behavior_draft_id);
        setScreen("behaviors");
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "PHASE4_OPERATION_FAILED");
    }
  };

  const runImpactSearch = async () => {
    if (!selected) return;
    setBusy(true); setError("");
    try { setImpactResults(await searchImpact(selected.id, impactQuery)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "IMPACT_SEARCH_FAILED"); }
    finally { setBusy(false); }
  };

  const chooseFolder = async () => {
    setBusy(true); setError("");
    try {
      const chosen = await open({ directory: true, multiple: false, title: t("add.dialogTitle") });
      const path = Array.isArray(chosen) ? chosen[0] : chosen;
      if (!path) return;
      const detected = await detectProject(path);
      setDetection(detected); setDisplayName(detected.suggested_name);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "PROJECT_DETECTION_FAILED");
    } finally { setBusy(false); }
  };

  const connect = async () => {
    if (!detection) return;
    setBusy(true); setError("");
    try {
      const project = await createProject(detection.selected_path, displayName, monitoring);
      setProjects((items) => [project, ...items]); setSelected(project); setImpact(null); setScreen("project");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "PROJECT_CREATE_FAILED");
    } finally { setBusy(false); }
  };

  const scanPercent = useMemo(() => {
    if (!selected?.scan?.total_candidates) return selected?.scan?.status === "completed" ? 100 : 0;
    return Math.min(100, Math.round(selected.scan.processed_files * 100 / selected.scan.total_candidates));
  }, [selected]);

  if (startupVisible) return <StartupScreen status={startupStatus} failedStep={startupFailedStep} leaving={startupLeaving} error={startupError} slow={startupSlow} retry={() => setStartupAttempt((attempt) => attempt + 1)} locale={locale} setLocale={setLocale} t={t} errorText={errorText} updater={updater} />;

  if (screen === "add") return <main className="app-shell" dir={direction}><Header home={home} locale={locale} setLocale={setLocale} t={t} updater={updater} />
    <section className="page-head"><div><div className="eyebrow">{t("add.eyebrow")}</div><h1>{t("add.title")}</h1><p>{t("add.subtitle")}</p></div><button className="secondary" onClick={home}>{t("common.back")}</button></section>
    {error && <section className="panel error" role="alert">{errorText(error)}</section>}
    {!detection ? <section className="panel folder-picker"><MascotArt pose="yak-search-inspect" t={t} className="mascot-empty" /><h2>{t("add.chooseTitle")}</h2><p>{t("add.chooseBody")}</p><button className="primary" disabled={busy} onClick={() => void chooseFolder()}>{busy ? t("add.inspecting") : t("add.chooseButton")}</button></section>
      : <div className="content-grid add-grid">
        <section className="panel"><div className="section-head"><h2>{t("add.detected")}</h2><span className="local-badge">{t("common.localOnly")}</span></div>
          <label className="field"><span>{t("add.projectName")}</span><input value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
          <StatusRow label={t("add.selectedFolder")} value={detection.selected_path} /><StatusRow label={t("add.repositoryRoot")} value={detection.repository_path} />
          <StatusRow label={t("add.candidateFiles")} value={String(detection.candidate_files)} /><StatusRow label={t("add.ignoredPaths")} value={String(detection.ignored_paths)} />
          <h3>{t("add.languages")}</h3><Tags values={detection.languages} empty={t("add.noLanguage")} />
          <h3>{t("add.frameworkRuntime")}</h3><Tags values={[...detection.frameworks, ...detection.runtime_hints]} empty={t("add.noFramework")} />
          <h3>{t("add.tests")}</h3><Tags values={detection.tests} empty={t("add.noTests")} />
        </section>
        <section className="panel"><h2>{t("add.gitObservation")}</h2>
          <StatusRow label={t("add.status")} value={detection.git.available ? t("add.available") : t("readiness.gitUnavailable")} tone={detection.git.available ? "good" : "warn"} />
          <StatusRow label={t("add.branch")} value={detection.git.branch || (detection.git.is_detached ? t("add.detachedHead") : t("common.unknown"))} />
          <StatusRow label={t("add.head")} value={detection.git.head_sha?.slice(0, 12) || t("common.unknown")} />
          <StatusRow label={t("add.worktree")} value={detection.git.is_dirty ? t("add.changesPresent") : t("add.clean")} tone={detection.git.is_dirty ? "warn" : "good"} />
          <StatusRow label={t("add.changes")} value={t("add.changeCounts", { staged: detection.git.staged.length, unstaged: detection.git.unstaged.length, untracked: detection.git.untracked.length })} />
          <label className="field"><span>{t("add.passiveMonitoring")}</span><select value={monitoring} onChange={(event) => setMonitoring(event.target.value as "passive" | "paused")}><option value="passive">{t("add.monitorOn")}</option><option value="paused">{t("common.paused")}</option></select></label>
          <div className="privacy-note"><strong>{t("add.sourceLocalTitle")}</strong><span>{t("add.sourceLocalBody")}</span></div>
          <div className="button-row"><button className="secondary" onClick={() => setDetection(null)}>{t("add.chooseAnother")}</button><button className="primary" disabled={busy || !displayName.trim()} onClick={() => void connect()}>{busy ? t("add.connecting") : t("add.connect")}</button></div>
        </section>
      </div>}
  </main>;

  if (screen === "change" && selected) {
    const impacted = changeImpact?.results.filter((item) => !item.unknown && !item.stale) ?? [];
    const boundaries = changeImpact?.results.filter((item) => item.unknown || item.stale) ?? [];
    const linkedBehaviors = knownBehaviors.filter((behavior) => behavior.links.some((link) => link.link_type === "FILE" && currentChange?.changed_paths.includes(link.link_key)));
    return <main className="app-shell" dir={direction}><Header home={home} locale={locale} setLocale={setLocale} t={t} updater={updater} />
      <ProjectNav active="change" select={selectProjectScreen} t={t} />
      <section className="page-head"><div><div className="eyebrow">{currentChange?.status === "change_detected" ? t("change.detected") : t("change.local")}</div><h1>{t("change.title")}</h1><p>{currentChange?.change_kind === "uncommitted_worktree" ? t("change.workingTree", { head: currentChange.head_sha?.slice(0, 12) ?? t("change.unknownHead") }) : `${currentChange?.base_head_sha?.slice(0, 12) ?? t("common.unknown")} → ${currentChange?.head_sha?.slice(0, 12) ?? t("common.unknown")}`}</p></div><span className={selected.monitoring_status === "active" ? "live-dot" : "muted"}>{selected.monitoring_status === "active" ? t("common.live").toUpperCase() : t("common.paused").toUpperCase()}</span></section>
      {error && <section className="panel error" role="alert">{errorText(error)}</section>}
      {!currentChange ? <section className="panel loading">{t("change.stabilizing")}</section> : <>
        <section className="panel change-command"><label className="field"><span>{t("change.intent")}</span><input value={taskIntent} maxLength={2000} placeholder={t("change.intentPlaceholder")} onChange={(event) => setTaskIntent(event.target.value)} /></label><button className="primary" disabled={busy || currentChange.status === "no_changes"} onClick={() => void runAnalysis()}>{busy ? t("change.analyzing") : t("change.analyze")}</button></section>
        {changeImpact && <div className="analysis-banner"><strong>{t("change.impactAnalyzed")}</strong><span>{t("change.relatedSummary", { count: changeImpact.analysis.impacted_node_count, algorithm: changeImpact.analysis.algorithm_version })}</span>{changeImpact.analysis.stale && <em>{t("change.staleRerun")}</em>}</div>}
        <div className="change-grid">
          <section className="panel"><div className="section-head"><h2>{t("change.changedFiles")}</h2><span>{currentChange.changed_paths.length}</span></div>{currentChange.changed_paths.length ? <ul className="compact-list">{currentChange.changed_paths.map((path) => <li key={path}><code dir="ltr">{path}</code></li>)}</ul> : <p className="muted">{t("change.noChangedFiles")}</p>}</section>
          <section className="panel"><div className="section-head"><h2>{t("change.relatedEntities")}</h2><span>{impacted.length}</span></div>{impacted.length ? <div className="entity-list">{impacted.map((item) => <article key={item.id}><div><strong>{item.display_name}</strong><small>{t("change.entityMeta", { type: item.node_type, depth: item.minimum_depth })}</small></div><span>{item.impact_class}</span><p>{item.explanation}</p></article>)}</div> : <p className="muted">{t("change.noEntities")}</p>}</section>
          <section className="panel"><div className="section-head"><h2>{t("change.impactPaths")}</h2><span>{impactPaths.length}</span></div>{impactPaths.length ? <div className="path-list">{impactPaths.map((path) => <article key={String(path.id)}><strong>{String(path.result)}</strong><small>{t("change.pathMeta", { className: String(path.impact_class), depth: String(path.depth) })}</small><pre dir="ltr">{JSON.stringify(path.steps, null, 2)}</pre></article>)}</div> : <p className="muted">{t("change.noPaths")}</p>}</section>
          <section className="panel"><div className="section-head"><h2>{t("change.boundaries")}</h2><span>{boundaries.length}</span></div>{boundaries.length ? <ul className="boundary-list">{boundaries.map((item) => <li key={item.id}><strong>{item.display_name}</strong><span>{item.unknown_reason ?? (item.stale ? t("change.staleRelation") : t("change.unknownBoundary"))}</span></li>)}</ul> : <p className="muted">{t("change.noBoundaries")}</p>}</section>
          <section className="panel receipt-panel"><div className="section-head"><h2>{t("receipt.title")}</h2><button className="secondary" disabled={busy || !changeImpact} onClick={() => void generateReceipt()}>{receipt ? t("receipt.regenerate") : t("receipt.generate")}</button></div><p className="muted">{t("receipt.description")}</p>{receipt && <><div className="receipt-summary"><StatusRow label={t("common.schema")} value={receipt.schema} /><StatusRow label={t("receipt.selectedFiles")} value={String(receipt.size_metrics.selected_files ?? 0)} /><StatusRow label={t("receipt.sourceBytes")} value={String(receipt.size_metrics.selected_source_bytes ?? 0)} tone="good" /><StatusRow label={t("receipt.status")} value={receipt.stale ? t("common.stale") : receipt.truncated ? t("receipt.bounded") : t("common.current")} tone={receipt.stale ? "warn" : "good"} /></div><div className="button-row"><button className="secondary" onClick={() => void copyReceipt()}>{t("receipt.copy")}</button></div><details><summary>{t("receipt.details")}</summary><pre dir="ltr">{JSON.stringify({ selected_files: receipt.selected_files, selection_reasons: receipt.selection_reasons, excluded_context: receipt.excluded_context, unknowns: receipt.unknowns, constraints: receipt.constraints }, null, 2)}</pre></details></>}</section>
          <section className="panel behavior-panel"><div className="section-head"><h2>{t("candidate.title")}</h2><span>{candidates.length}</span></div><p className="muted">{t("candidate.description")}</p>{candidates.length ? <div className="candidate-list">{candidates.map((candidate) => <article key={candidate.id}><div><strong>{candidate.title ?? candidate.source_key ?? t("candidate.observed")}</strong><small>{t("candidate.meta", { status: status(candidate.status) })}</small></div><div className="mini-actions"><button onClick={() => void changeCandidate(candidate, "keep")}>{t("candidate.keep")}</button><button onClick={() => void changeCandidate(candidate, "dismiss")}>{t("candidate.dismiss")}</button><button onClick={() => void changeCandidate(candidate, "prepare")}>{t("candidate.prepare")}</button></div></article>)}</div> : <p className="muted">{t("candidate.none")}</p>}</section>
          <section className="panel behavior-panel"><div className="section-head"><h2>{t("change.knownBehaviorLinks")}</h2><span>{linkedBehaviors.length}</span></div><p className="muted">{t("change.behaviorLinkCaution")}</p>{linkedBehaviors.length ? <ul className="compact-list">{linkedBehaviors.map((behavior) => <li key={behavior.id}><strong>{behavior.current_version.title}</strong><span>{t(`behavior.state.${behavior.lifecycle_state}`)}</span></li>)}</ul> : <p className="muted">{t("change.noKnownBehaviorLinks")}</p>}</section>
        </div>
      </>}
    </main>;
  }

  if (screen === "impact" && selected) return <main className="app-shell" dir={direction}><Header home={home} locale={locale} setLocale={setLocale} t={t} updater={updater} />
    <ProjectNav active="impact" select={selectProjectScreen} t={t} />
    <section className="page-head"><div><div className="eyebrow">{t("impact.eyebrow")}</div><h1>{t("impact.title")}</h1><p>{t("impact.subtitle")}</p></div><span className="local-badge">{t("common.localOnly")}</span></section>
    {error && <section className="panel error" role="alert">{errorText(error)}</section>}
    <section className="panel impact-search"><label className="field"><span>{t("impact.searchLabel")}</span><input value={impactQuery} placeholder={t("impact.searchPlaceholder")} onChange={(event) => setImpactQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void runImpactSearch(); }} /></label><button className="primary" disabled={busy} onClick={() => void runImpactSearch()}>{busy ? t("impact.searching") : t("impact.search")}</button></section>
    <section className="explorer-results">{impactResults.map((item, index) => <article className="panel explorer-card" key={`${item.node.type}-${item.node.label}-${index}`}><div className="section-head"><div><h2>{item.node.label}</h2><span className="muted">{item.node.type}{item.node.relative_path ? ` · ${item.node.relative_path}` : ""}</span></div><span>{t("impact.relations", { count: item.relationships.length })}</span></div><div className="relationship-list">{item.relationships.map((relation, relationIndex) => <div key={`${relation.direction}-${relation.target}-${relationIndex}`}><span className={`direction ${relation.direction}`}>{status(relation.direction)}</span><strong>{relation.type} → {relation.target}</strong><small>{t("impact.scanMeta", { provenance: relation.provenance, scan: relation.source_scan_revision, stale: relation.stale ? t("impact.staleSuffix") : "" })}</small></div>)}</div>{item.recent_changes.length > 0 && <div className="recent-changes"><strong>{t("impact.recentChanges")}</strong><Tags values={item.recent_changes} empty="" /></div>}</article>)}</section>
    {!impactResults.length && <section className="panel mascot-helper"><MascotArt pose="yak-teaching-map" t={t} className="mascot-helper-art" /><p className="muted">{t("impact.empty")}</p></section>}
  </main>;

  if (screen === "behaviors" && selected) return <main className="app-shell" dir={direction}><Header home={home} locale={locale} setLocale={setLocale} t={t} updater={updater} />
    <ProjectNav active="behaviors" select={selectProjectScreen} t={t} />
    {error && <section className="panel error" role="alert">{errorText(error)}</section>}
    <BehaviorsScreen projectId={selected.id} initialBehaviorId={focusBehaviorId} t={t} onError={setError} />
  </main>;

  if (screen === "project" && selected) {
    const ready = readiness(selected, t);
    return <main className="app-shell" dir={direction}><Header home={home} locale={locale} setLocale={setLocale} t={t} updater={updater} /><ProjectNav active="overview" select={selectProjectScreen} t={t} />
      <section className="page-head"><div><div className="eyebrow">{t("project.eyebrow")}</div><h1>{selected.display_name}</h1><p>{selected.repository_path}</p></div><span className={`readiness ${ready.tone}`}>{ready.label}</span></section>
      {error && <section className="panel error" role="alert">{errorText(error)}</section>}
      <div className="project-grid">
        <section className="panel scan-panel"><div className="section-head"><h2>{t("project.sourceScan")}</h2><span>{scanPercent}%</span></div>{(!selected.scan || selected.scan.status === "running") && <MascotArt pose="yak-working-laptop" t={t} className="mascot-scan" />}<div className="progress"><span style={{ width: `${scanPercent}%` }} /></div>
          {!selected.scan ? <p className="muted">{t("project.preparing")}</p> : <><StatusRow label={t("add.status")} value={status(selected.scan.status)} tone={selected.scan.status === "completed" ? "good" : selected.scan.status === "failed" ? "warn" : "neutral"} /><StatusRow label={t("project.progress")} value={t("project.progressValue", { processed: selected.scan.processed_files, total: selected.scan.total_candidates })} /><StatusRow label={t("project.indexed")} value={String(selected.scan.included_files)} /><StatusRow label={t("project.excluded")} value={String(selected.scan.excluded_files)} /><StatusRow label={t("project.sensitive")} value={String(selected.scan.sensitive_files)} /><StatusRow label={t("common.unknown")} value={String(selected.scan.unknown_items)} /><StatusRow label={t("project.unsupported")} value={String(selected.scan.unsupported_files)} /></>}
          <div className="button-row">{selected.scan?.status === "running" ? <button className="secondary danger" onClick={() => void cancelProjectScan(selected.id)}>{t("project.cancelScan")}</button> : <button className="secondary" onClick={() => void startProjectScan(selected.id)}>{t("project.runScan")}</button>}</div>
        </section>
        <section className="panel"><div className="section-head"><h2>{t("project.gitMonitoring")}</h2><span className={selected.monitoring_status === "active" ? "live-dot" : "muted"}>{status(selected.monitoring_status)}</span></div>
          <StatusRow label={t("project.git")} value={selected.git.available ? selected.git.branch || t("add.detachedHead") : t("readiness.gitUnavailable")} tone={selected.git.available ? "good" : "warn"} /><StatusRow label={t("add.head")} value={selected.git.head_sha?.slice(0, 12) || t("common.unknown")} /><StatusRow label={t("add.worktree")} value={selected.git.is_dirty ? t("add.changesPresent") : t("add.clean")} tone={selected.git.is_dirty ? "warn" : "good"} /><StatusRow label={t("add.changes")} value={t("add.changeCounts", { staged: selected.git.staged.length, unstaged: selected.git.unstaged.length, untracked: selected.git.untracked.length })} />
          <div className="button-row"><button className="secondary" onClick={() => void openProjectFolder(selected.id)}>{t("common.openFolder")}</button><button className="secondary" onClick={() => void setProjectMonitoring(selected.id, selected.monitoring_status !== "active")}>{selected.monitoring_status === "active" ? t("project.pauseMonitoring") : t("project.resumeMonitoring")}</button></div>
        </section>
        <section className="panel impact-panel"><h2>{t("project.impactFoundation")}</h2><div className="metric-grid"><div><strong>{impact?.files_indexed ?? 0}</strong><span>{t("project.filesIndexed")}</span></div><div><strong>{impact?.direct_relationships ?? 0}</strong><span>{t("project.directRelationships")}</span></div><div><strong>{impact?.tests_found ?? 0}</strong><span>{t("project.testsFound")}</span></div><div><strong>{impact?.languages ?? 0}</strong><span>{t("project.languages")}</span></div></div><div className="coverage-note"><strong>{t("project.knownCoverage")}</strong><span>{t("project.coverage", { unknown: impact?.unknown_references ?? 0, unsupported: impact?.unsupported_files ?? 0, stale: impact?.stale_relationships ?? 0 })}</span></div><Tags values={selected.languages} empty={t("project.coveragePending")} /></section>
      </div>
    </main>;
  }

  return <main className="app-shell" dir={direction}><Header home={home} locale={locale} setLocale={setLocale} t={t} updater={updater} />
    <section className="hero"><div className="hero-copy"><div className="eyebrow">{t("home.eyebrow")}</div><h1>{projects.length ? t("home.projectsTitle") : t("home.readyTitle")}</h1><p>{t("home.localData")}</p><div className="privacy-pills"><span>{t("home.noDocker")}</span><span>{t("home.noDatabase")}</span><span>{t("home.noCloud")}</span></div></div><MascotArt pose={projects.length ? "yak-peek-laptop" : "yak-wave"} t={t} className="mascot-hero" /></section>
    {error ? <section className="panel error" role="alert"><h2>{t("home.engineUnavailable")}</h2><p>{errorText(error)}</p></section> : snapshot ? <>
      {projects.length ? <section className="project-list"><div className="section-head"><h2>{t("home.connectedProjects")}</h2><button className="primary" onClick={() => setScreen("add")}>{t("home.addProject")}</button></div>{projects.map((project) => { const ready = readiness(project, t); return <button className="project-card" key={project.id} onClick={() => { setSelected(project); setImpact(null); setScreen("project"); }}><span><strong>{project.display_name}</strong><small>{project.repository_path}</small></span><span className={`readiness ${ready.tone}`}>{ready.label}</span></button>; })}</section>
        : <div className="content-grid"><section className="panel"><div className="section-head"><h2>{t("home.verifiedStatus")}</h2><span className="live-dot">{t("common.live")}</span></div><StatusRow label={t("home.localEngine")} value={snapshot.health.status === "ready" ? t("home.running") : status(snapshot.health.status)} tone="good" /><StatusRow label={t("home.storage")} value={snapshot.storage.data_root} /><StatusRow label={t("home.database")} value={t("home.sqliteLocal")} tone="good" /><StatusRow label={t("home.networkMode")} value={t("common.localOnly")} tone="good" /><StatusRow label={t("home.cloud")} value={snapshot.privacy.cloud_connected ? t("home.connected") : t("home.notConnected")} /></section><section className="panel privacy-card"><h2>{t("home.privateTitle")}</h2><ul><li>{t("home.codeLocal")}</li><li>{t("home.projectLocal")}</li><li>{t("home.evidenceLocal")}</li></ul><p>{t("home.connectorNotice")}</p><div className="versions"><span>{t("common.app")} <strong>{snapshot.health.app_version}</strong></span><span>{t("common.engine")} <strong>{snapshot.health.engine_version}</strong></span><span>{t("common.schema")} <strong>{snapshot.health.database_schema_version}</strong></span></div></section></div>}
      <footer className="actions">{!projects.length && <button className="primary" onClick={() => setScreen("add")}>{t("home.firstProject")}</button>}<button className="secondary" onClick={() => void openDataFolder()}>{t("home.openData")}</button><details><summary>{t("home.diagnostics")}</summary><pre dir="ltr">{JSON.stringify(snapshot.readiness, null, 2)}</pre></details></footer>
    </> : null}
  </main>;
}
