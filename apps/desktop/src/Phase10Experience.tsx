import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  cancelProductSelfTest,
  exportProductSelfTest,
  exportSupportBundle,
  getActivityPreferences,
  getDiagnosticsTruthOverview,
  getEpisodeTruthDetail,
  getHomeSummary,
  getPackageAcceptance,
  getProjectTruthActivity,
  getProjectTruthOverview,
  getRegressionTruthDetail,
  getSupportBundle,
  getUpdaterStatus,
  runProductSelfTest,
  recordPerformanceMetric,
  setActivityMode,
  type ActivityPreferences,
  type DiagnosticsTruthOverview,
  type EpisodeTruthDetail,
  type HomeSummary,
  type ProductSelfTestRun,
  type Project,
  type ProjectTruthActivity,
  type ProjectTruthOverview,
  type RegressionTruthDetail,
} from "./api";
import { FirstRunExperience } from "./Phase9Experience";
import { ProjectCompatibilityPanel } from "./ProjectCompatibilityPanel";
import { useLocalEvents } from "./useLocalEvents";
import "./phase10.css";

type T = (key: string, parameters?: Record<string, string | number>) => string;

export const phase10CaptureStates = [
  "first-run-welcome",
  "first-run-choice-unselected",
  "first-run-demo-selected",
  "first-run-background-settings",
  "first-run-complete-demo",
  "home-no-confirmed-issue",
  "home-needs-attention",
  "project-overview-healthy",
  "project-overview-ready-with-limits",
  "project-activity-timeline",
  "episode-detail",
  "check-passed-no-regression",
  "behaviors-known-good",
  "regression-friendly",
  "regression-technical",
  "repair-workspace-operational",
  "candidate-validation-progress",
  "candidate-validated",
  "apply-confirmation",
  "apply-transaction-progress",
  "applied-and-verified",
  "rolled-back-safely",
  "disconnected-projects",
  "reconnect-identity-preview",
  "project-mismatch-alert",
  "diagnostics-real-data",
  "self-test-running",
  "self-test-passed",
  "support-bundle-manifest",
  "update-status",
  "activity-mode-settings",
  "native-tray-preview",
  "hebrew-home",
  "hebrew-project-overview",
  "hebrew-regression",
  "hebrew-diagnostics",
] as const;

export type Phase10CaptureState = (typeof phase10CaptureStates)[number];

const dateTime = (value: string | null | undefined) => value
  ? new Intl.DateTimeFormat(document.documentElement.lang || "en", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value))
  : "—";

const bytes = (value: number) => {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KiB`;
  return `${(value / 1024 / 1024).toFixed(1)} MiB`;
};

const stateKeys: Record<string, string> = {
  NO_PROJECTS: "phase10.state.noProjects",
  EVERYTHING_LOOKS_OKAY: "phase10.state.everythingOkay",
  NO_CONFIRMED_ISSUE_FOUND: "phase10.state.noConfirmedIssue",
  NO_CONFIRMED_ISSUE: "phase10.state.noConfirmedIssue",
  NEEDS_ATTENTION: "phase10.state.needsAttention",
  READY_WITH_LIMITS: "phase10.state.readyWithLimits",
  DISCONNECTED: "phase10.state.disconnected",
  PAUSED: "phase10.state.paused",
  WATCH: "phase10.state.watch",
  SUSPECTED: "phase10.state.suspected",
  HIGH: "phase10.state.high",
  CONFIRMED: "phase10.state.confirmed",
  DETECTED: "phase10.state.confirmed",
  PASS: "phase10.state.passed",
  PASSED: "phase10.state.passed",
  FAIL: "phase10.state.failed",
  FAILED: "phase10.state.failed",
  INCONCLUSIVE: "phase10.state.inconclusive",
  NOT_RUN: "phase10.state.notRun",
  SKIPPED: "phase10.state.skipped",
  CANCELLED: "phase10.state.cancelled",
  RUNTIME_UNAVAILABLE: "phase10.state.runtimeUnavailable",
  NEEDS_REVIEW: "phase10.state.needsReview",
  READY: "phase10.state.ready",
  AVAILABLE: "phase10.state.available",
  UNAVAILABLE: "phase10.state.unavailable",
  VERIFIED: "phase10.state.verified",
  COMMITTED: "phase10.state.committed",
  ROLLED_BACK: "phase10.state.rolledBack",
  FAILED_RECOVERY_REQUIRED: "phase10.state.recoveryRequired",
  APPLYING: "phase10.state.applying",
  POST_VERIFYING: "phase10.state.verifyingLive",
  ACTIVE: "phase10.state.active",
  active: "phase10.state.active",
  AUTHENTICATED_LOOPBACK: "phase12.state.AUTHENTICATED_LOOPBACK",
  YES: "phase12.state.YES",
  NO: "phase12.state.NO",
  NOT_READY: "phase12.state.NOT_READY",
  UNSIGNED: "phase12.state.UNSIGNED",
  AD_HOC_SIGNED: "phase12.state.AD_HOC_SIGNED",
  DEVELOPER_ID_SIGNED: "phase12.state.DEVELOPER_ID_SIGNED",
  NOTARIZED: "phase12.state.NOTARIZED",
  GATEKEEPER_ACCEPTED: "phase12.state.GATEKEEPER_ACCEPTED",
  NOT_CHECKED: "phase12.state.NOT_CHECKED",
  CHECKING: "phase12.state.CHECKING",
  UP_TO_DATE: "phase12.state.UP_TO_DATE",
  UPDATE_AVAILABLE: "phase12.state.UPDATE_AVAILABLE",
  DOWNLOADING: "phase12.state.DOWNLOADING",
  VERIFYING_SIGNATURE: "phase12.state.VERIFYING_SIGNATURE",
  INSTALLING: "phase12.state.INSTALLING",
  RESTART_REQUIRED: "phase12.state.RESTART_REQUIRED",
  UPDATED: "phase12.state.UPDATED",
  NO_UPDATE: "phase12.state.NO_UPDATE",
  INVALID_SIGNATURE: "phase12.state.INVALID_SIGNATURE",
  INCOMPLETE_DOWNLOAD: "phase12.state.INCOMPLETE_DOWNLOAD",
  PRODUCTION_CHANNEL_UNPUBLISHED: "phase12.state.PRODUCTION_CHANNEL_UNPUBLISHED",
};

const activityEventKeys: Record<string, string> = {
  EPISODE_STABILIZED: "phase10.event.EPISODE_STABILIZED",
  EPISODE_STARTED: "phase10.event.EPISODE_STARTED",
  CHECK_COMPLETED: "phase10.event.CHECK_COMPLETED",
  REGRESSION_CONFIRMED: "phase10.event.REGRESSION_CONFIRMED",
  REGRESSION_RESOLVED: "phase10.event.REGRESSION_RESOLVED",
  SNAPSHOT_CREATED: "phase10.event.SNAPSHOT_CREATED",
  APPLY_TRANSACTION: "phase10.event.APPLY_TRANSACTION",
};

function humanState(t: T, state: string | null | undefined): string {
  return t(stateKeys[state ?? ""] ?? "phase10.state.unknown");
}

const technicalCodeKeys: Record<string, string> = {
  ROOT_CAUSE_NOT_PROVEN: "phase12.code.rootCauseNotProven",
  BLAST_RADIUS_MAY_BE_INCOMPLETE: "phase12.code.coverageIncomplete",
  NOT_RELATED_TO_CHANGE: "phase12.code.notSelectedByChange",
  NO_KNOWN_GOOD_BEHAVIORS: "phase12.code.noKnownGoodBehaviors",
  RUNTIME_NOT_CONFIGURED: "phase12.code.runtimeNotConfigured",
  NO_CHECK_RESULT: "phase12.code.noCheckResult",
  ONE_UNKNOWN_BOUNDARY: "phase12.code.unknownBoundary",
  PUBLIC_DISTRIBUTION_NOT_READY: "phase12.code.publicDistributionNotReady",
  WINDOWS_LINUX_ARM_RUNTIME_NOT_VERIFIED: "phase12.code.otherPlatformsNotVerified",
};

function humanCode(t: T, code: string): string {
  return t(technicalCodeKeys[code] ?? "phase12.code.other");
}

function tone(state: string): "good" | "warn" | "bad" | "neutral" {
  if (["PASS", "PASSED", "READY", "VERIFIED", "COMMITTED", "NO_CONFIRMED_ISSUE", "EVERYTHING_LOOKS_OKAY"].includes(state)) return "good";
  if (["FAIL", "FAILED", "CONFIRMED", "DETECTED", "FAILED_RECOVERY_REQUIRED"].includes(state)) return "bad";
  if (["NEEDS_ATTENTION", "READY_WITH_LIMITS", "WATCH", "SUSPECTED", "INCONCLUSIVE", "DISCONNECTED", "PAUSED"].includes(state)) return "warn";
  return "neutral";
}

function TruthPill({ t, state }: { t: T; state: string }) {
  return <span className={`truth-pill ${tone(state)}`}><span aria-hidden="true" />{humanState(t, state)}</span>;
}

function LoadState({ t, error, retry }: { t: T; error?: string; retry?: () => void }) {
  return <section className={`panel truth-load ${error ? "error" : ""}`} role={error ? "alert" : "status"}>
    <strong>{t(error ? "phase10.load.failed" : "phase10.load.loading")}</strong>
    <span>{t(error ? "phase10.load.failedBody" : "phase10.load.loadingBody")}</span>
    {error && retry && <button className="secondary" onClick={retry}>{t("phase10.action.retry")}</button>}
  </section>;
}

function LimitationList({ t, values }: { t: T; values: string[] }) {
  if (!values.length) return null;
  return <div className="truth-limitations"><strong>{t("phase10.knownLimits")}</strong><ul>{values.map((value) => <li key={value}><span>{humanCode(t, value)}</span><details><summary>{t("common.technicalDetails")}</summary><code dir="ltr">{value}</code></details></li>)}</ul></div>;
}

function SummaryMetric({ label, value, state }: { label: string; value: string | number; state?: string }) {
  return <div className="truth-metric"><span>{label}</span><strong>{value}</strong>{state && <small>{state}</small>}</div>;
}

function ActivityRow({ t, item, open }: {
  t: T;
  item: HomeSummary["recent_activity"][number];
  open?: () => void;
}) {
  const changed = Number(item.facts.changed_count ?? 0);
  const content = <>
    <span className="truth-time">{dateTime(item.created_at)}</span>
    <span className="truth-activity-main"><strong>{t(activityEventKeys[item.event_type] ?? "phase10.event.PROJECT_EVENT")}</strong><small>{changed ? t("phase10.activity.changedCount", { count: changed }) : t("phase10.activity.recorded")}</small></span>
    <TruthPill t={t} state={item.state} />
  </>;
  return open ? <button className="truth-activity-row" onClick={open}>{content}</button> : <div className="truth-activity-row">{content}</div>;
}

export function OperationalHome({ t, openProject, openActivity, addProject, data }: {
  t: T;
  openProject: (projectId: string) => void;
  openActivity?: (projectId: string, entityType: string, entityId: string | null) => void;
  addProject?: () => void;
  data?: HomeSummary;
}) {
  const [summary, setSummary] = useState<HomeSummary | null>(data ?? null);
  const [error, setError] = useState("");
  const firstLoad = useRef(true);
  const refresh = useCallback(async () => {
    if (data) return;
    const started = performance.now();
    try {
      setSummary(await getHomeSummary());
      setError("");
      if (firstLoad.current) {
        firstLoad.current = false;
        void recordPerformanceMetric("first_home_data", performance.now() - started, "home");
      }
    }
    catch (reason) { setError(String(reason)); }
  }, [data]);
  useEffect(() => { void refresh(); }, [refresh]);
  useLocalEvents(undefined, () => { void refresh(); });
  if (!summary) return <div className="truth-page"><LoadState t={t} error={error} retry={() => void refresh()} /></div>;
  const counts = summary.counts ?? {};
  const known = summary.known ?? [];
  const unknowns = summary.unknowns ?? [];
  const attention = summary.attention ?? [];
  const projects = summary.projects ?? [];
  const recentActivity = summary.recent_activity ?? [];
  const state = summary.state || "NO_PROJECTS";
  return <div className="truth-page">
    <header className="truth-heading"><div><span className="eyebrow">{t("phase10.home.eyebrow")}</span><h1>{t("phase10.home.title")}</h1><p>{t("phase10.home.subtitle")}</p></div><TruthPill t={t} state={state} /></header>
    <section className={`truth-answer ${tone(state)}`} aria-labelledby="truth-answer-title"><div><span>{t("phase10.home.question")}</span><h2 id="truth-answer-title">{humanState(t, state)}</h2><p>{t(state === "EVERYTHING_LOOKS_OKAY" ? "phase10.home.justified" : "phase10.home.coverageLimited")}</p></div><div className="truth-known"><span>{t("phase10.knownFacts", { count: known.length })}</span><span>{t("phase10.unknownFacts", { count: unknowns.length })}</span></div></section>
    <section className="truth-metric-grid" aria-label={t("phase10.home.summaryLabel")}>
      <SummaryMetric label={t("phase10.metric.monitored")} value={counts.monitored ?? 0} />
      <SummaryMetric label={t("phase10.metric.paused")} value={counts.paused ?? 0} />
      <SummaryMetric label={t("phase10.metric.disconnected")} value={counts.disconnected ?? 0} />
      <SummaryMetric label={t("phase10.metric.needsSetup")} value={counts.needs_setup ?? 0} />
      <SummaryMetric label={t("phase10.metric.regressions")} value={counts.confirmed_regressions ?? 0} />
      <SummaryMetric label={t("phase10.metric.unread")} value={counts.unread_alerts ?? 0} />
    </section>
    {attention.length > 0 && <section className="panel truth-section"><div className="section-head"><div><h2>{t("phase10.home.attention")}</h2><p>{t("phase10.home.attentionBody")}</p></div><span>{attention.length}</span></div><div className="truth-project-list">{attention.map((project) => <button key={project.id} className="truth-project-row" onClick={() => openProject(project.id)}><span><strong>{project.display_name}</strong><small>{(project.limitations ?? []).map((value) => value).join(" · ")}</small></span><TruthPill t={t} state={project.state} /></button>)}</div></section>}
    <div className="truth-columns">
      <section className="panel truth-section"><div className="section-head"><div><h2>{t("phase10.home.projectHealth")}</h2><p>{t("phase10.home.projectHealthBody")}</p></div><span>{projects.length}</span></div><div className="truth-project-list">{projects.map((project) => <button key={project.id} className="truth-project-row" onClick={() => openProject(project.id)}><span><strong>{project.display_name}</strong><small>{t("phase10.home.projectMeta", { behaviors: project.protected_behavior_count, regressions: project.open_regression_count })}</small></span><span className="truth-project-facts"><small>{humanState(t, project.runtime_state)}</small><small>{dateTime(project.last_activity_at)}</small></span><TruthPill t={t} state={project.state} /></button>)}</div>{projects.length === 0 && addProject && <button className="primary truth-empty-action" onClick={addProject}>{t("home.firstProject")}</button>}</section>
      <section className="panel truth-section"><div className="section-head"><div><h2>{t("phase10.home.recent")}</h2><p>{t("phase10.home.recentBody")}</p></div></div><div className="truth-activity-list">{recentActivity.length ? recentActivity.map((item) => <ActivityRow key={`${item.entity_type}-${item.id}`} t={t} item={item} open={openActivity ? () => openActivity(item.project_id, item.entity_type, item.entity_id) : undefined} />) : <p className="muted">{t("phase10.home.noActivity")}</p>}</div></section>
    </div>
  </div>;
}

function CheckRow({ t, check }: { t: T; check: ProjectTruthOverview["latest_checks"][number] }) {
  return <article className="truth-check-row"><TruthPill t={t} state={check.result} /><span><strong>{check.name}</strong><small>{check.behavior_name ?? t("phase10.check.noBehavior")}</small></span><span><small>{t("phase10.check.attempts", { count: check.attempt_count })}</small><small>{check.duration_ms == null ? t("phase10.check.durationUnknown") : t("phase10.check.duration", { value: check.duration_ms })}</small></span><button className="secondary">{t("phase10.action.evidence")}</button></article>;
}

export function OperationalProjectOverview({ t, projectId, data, openActivity, openBehaviors, openRuntime, pause }: {
  t: T;
  projectId: string;
  data?: ProjectTruthOverview;
  openActivity?: () => void;
  openBehaviors?: () => void;
  openRuntime?: () => void;
  pause?: () => void;
}) {
  const [overview, setOverview] = useState<ProjectTruthOverview | null>(data ?? null);
  const [error, setError] = useState("");
  const firstLoad = useRef(true);
  const refresh = useCallback(async () => {
    if (data) return;
    const started = performance.now();
    try {
      setOverview(await getProjectTruthOverview(projectId));
      setError("");
      if (firstLoad.current) {
        firstLoad.current = false;
        void recordPerformanceMetric("first_project_overview_data", performance.now() - started, "project_overview", projectId);
      }
    }
    catch (reason) { setError(String(reason)); }
  }, [data, projectId]);
  useEffect(() => { void refresh(); }, [refresh]);
  useLocalEvents(projectId, () => { void refresh(); });
  if (!overview) return <div className="truth-page"><LoadState t={t} error={error} retry={() => void refresh()} /></div>;
  const project = overview.project;
  const savePoint = project.last_save_point as Record<string, unknown> | null;
  const episode = project.last_episode as Record<string, unknown> | null;
  return <div className="truth-page">
    <header className="truth-heading"><div><span className="eyebrow">{t("phase10.project.eyebrow")}</span><h1>{project.display_name}</h1><p>{t("phase10.project.subtitle")}</p></div><div className="truth-heading-actions"><TruthPill t={t} state={project.state} />{pause && <button className="secondary" onClick={pause}>{t(project.monitoring_state === "active" ? "phase10.action.pause" : "phase10.action.resume")}</button>}</div></header>
    <section className={`truth-answer ${tone(project.state)}`}><div><span>{t("phase10.project.currentStatus")}</span><h2>{humanState(t, project.state)}</h2><p>{t(project.state === "READY_WITH_LIMITS" ? "phase10.project.limitedExplanation" : "phase10.project.statusExplanation")}</p></div><div className="truth-known"><span>{t("phase10.project.checkSummary", { passed: overview.latest_checks.filter((item) => ["PASS", "PASSED"].includes(item.result)).length, failed: overview.latest_checks.filter((item) => ["FAIL", "FAILED"].includes(item.result)).length, inconclusive: overview.latest_checks.filter((item) => item.result === "INCONCLUSIVE").length })}</span><span>{t("phase10.project.issueSummary", { regressions: project.open_regression_count, recovery: project.recovery_required_count })}</span></div></section>
    <section className="truth-card-grid">
      <button className="truth-card" onClick={openActivity}><span>{t("phase10.card.lastChange")}</span><strong>{episode ? t("phase10.card.filesChanged", { count: Number(episode.changed_count ?? 0) }) : t("phase10.common.noneRecorded")}</strong><small>{dateTime(String(episode?.ended_at ?? episode?.started_at ?? ""))}</small></button>
      <button className="truth-card" onClick={openActivity}><span>{t("phase10.card.lastSavePoint")}</span><strong>{savePoint ? String(savePoint.creation_reason) : t("phase10.common.noneRecorded")}</strong><small>{savePoint ? dateTime(String(savePoint.created_at)) : t("phase10.card.createFirst")}</small></button>
      <button className="truth-card" onClick={openBehaviors}><span>{t("phase10.card.behaviors")}</span><strong>{project.protected_behavior_count}</strong><small>{t("phase10.card.protected")}</small></button>
      <button className="truth-card" onClick={openActivity}><span>{t("phase10.card.latestChecks")}</span><strong>{overview.latest_checks.length}</strong><small>{overview.latest_checks[0] ? humanState(t, overview.latest_checks[0].result) : t("phase10.common.noneRecorded")}</small></button>
      <button className="truth-card" onClick={openRuntime}><span>{t("phase10.card.runtime")}</span><strong>{humanState(t, project.runtime_state)}</strong><small>{t("phase10.card.runtimeDetail")}</small></button>
      <div className="truth-card"><span>{t("phase10.card.storage")}</span><strong>{humanState(t, String(overview.storage.integrity_state))}</strong><small>{t("phase10.card.storageDetail", { count: Number(overview.storage.snapshot_count), size: bytes(Number(overview.storage.logical_bytes)) })}</small></div>
    </section>
    <ProjectCompatibilityPanel projectId={projectId} t={t} />
    <div className="truth-columns">
      <section className="panel truth-section"><div className="section-head"><div><h2>{t("phase10.project.latestChecks")}</h2><p>{t("phase10.project.latestChecksBody")}</p></div></div>{overview.latest_checks.length ? overview.latest_checks.map((check) => <CheckRow key={check.id} t={t} check={check} />) : <p className="muted">{t("phase10.project.noChecks")}</p>}</section>
      <section className="panel truth-section"><div className="section-head"><div><h2>{t("phase10.project.recent")}</h2><p>{t("phase10.project.recentBody")}</p></div>{openActivity && <button className="secondary" onClick={openActivity}>{t("phase10.action.viewAll")}</button>}</div>{overview.recent_activity.map((item) => <ActivityRow key={`${item.entity_type}-${item.id}`} t={t} item={item} />)}</section>
    </div>
    <LimitationList t={t} values={overview.unknowns} />
    <details className="panel truth-technical"><summary>{t("phase10.technicalDetails")}</summary><dl><div><dt>{t("phase10.technical.branch")}</dt><dd dir="ltr">{String(overview.source_identity.branch ?? "—")}</dd></div><div><dt>{t("phase10.technical.sourceIdentity")}</dt><dd dir="ltr">{String(overview.source_identity.head_sha ?? overview.source_identity.worktree_fingerprint ?? "—")}</dd></div><div><dt>{t("phase10.technical.knownGood")}</dt><dd dir="ltr">{String(overview.last_known_good?.snapshot_id ?? "—")}</dd></div></dl></details>
  </div>;
}

export function EpisodeDetail({ t, detail }: { t: T; detail: EpisodeTruthDetail }) {
  const changedEntries = Object.entries(detail.changed);
  return <div className="truth-page truth-detail">
    <header className="truth-heading"><div><span className="eyebrow">{t("phase10.episode.eyebrow")}</span><h1>{t("phase10.episode.title")}</h1><p>{t("phase10.episode.subtitle", { time: dateTime(String(detail.episode.ended_at ?? detail.episode.started_at ?? "")) })}</p></div><TruthPill t={t} state={String(detail.result.signal)} /></header>
    <section className="panel truth-section"><h2>{t("phase10.episode.changed")}</h2><div className="truth-change-groups">{changedEntries.map(([kind, paths]) => paths.length ? <div key={kind}><strong>{t(`phase10.change.${kind}`)}</strong><ul>{paths.map((path, index) => <li key={`${kind}-${index}`}><code dir="ltr">{typeof path === "string" ? path : JSON.stringify(path)}</code></li>)}</ul></div> : null)}</div></section>
    <section className="panel truth-section"><h2>{t("phase10.episode.mayAffected")}</h2><p>{t("phase10.episode.mayAffectedCaution")}</p><div className="truth-affect-list">{detail.may_be_affected.map((item) => <article key={String(item.behavior_id)}><strong>{String(item.behavior_name)}</strong><small>{t("phase10.episode.provenance", { value: (item.provenance as string[]).join(" · ") })}</small></article>)}</div></section>
    <section className="panel truth-section"><h2>{t("phase10.episode.checked")}</h2>{detail.checks.length ? detail.checks.map((check) => <CheckRow t={t} check={check} key={check.id} />) : <p className="muted">{t("phase10.project.noChecks")}</p>}</section>
    <section className="panel truth-section"><h2>{t("phase10.episode.notChecked")}</h2>{detail.not_checked.length ? <ul>{detail.not_checked.map((item) => <li key={String(item.behavior_id)}><strong>{String(item.behavior_name)}</strong><span>{humanCode(t, String(item.reason_code))}</span><details><summary>{t("common.technicalDetails")}</summary><code dir="ltr">{String(item.reason_code)}</code></details></li>)}</ul> : <p className="muted">{t("phase10.episode.everyRelevantChecked")}</p>}</section>
    <section className="panel truth-result"><div><h2>{t("phase10.episode.result")}</h2><TruthPill t={t} state={String(detail.result.signal)} /></div><p>{t(String(detail.result.signal) === "WATCH" ? "phase10.episode.watchExplanation" : "phase10.episode.signalExplanation")}</p><LimitationList t={t} values={detail.unknowns} /></section>
    <details className="panel truth-technical"><summary>{t("phase10.technicalDetails")}</summary><pre dir="ltr">{JSON.stringify(detail.technical, null, 2)}</pre></details>
  </div>;
}

export function OperationalActivity({ t, projectId, data, detailData, initialEpisodeId }: {
  t: T;
  projectId: string;
  data?: ProjectTruthActivity;
  detailData?: EpisodeTruthDetail;
  initialEpisodeId?: string | null;
}) {
  const [activity, setActivity] = useState<ProjectTruthActivity | null>(data ?? null);
  const [selected, setSelected] = useState<EpisodeTruthDetail | null>(detailData ?? null);
  const [error, setError] = useState("");
  const refresh = useCallback(async () => {
    if (data) return;
    try { setActivity(await getProjectTruthActivity(projectId)); setError(""); }
    catch (reason) { setError(String(reason)); }
  }, [data, projectId]);
  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => {
    if (!initialEpisodeId || detailData) return;
    void getEpisodeTruthDetail(projectId, initialEpisodeId).then(setSelected).catch((reason: unknown) => setError(String(reason)));
  }, [detailData, initialEpisodeId, projectId]);
  useLocalEvents(projectId, () => { void refresh(); });
  const open = async (entityType: string, entityId: string | null) => {
    if (entityType !== "episode" || !entityId || detailData) return;
    try { setSelected(await getEpisodeTruthDetail(projectId, entityId)); }
    catch (reason) { setError(String(reason)); }
  };
  if (selected) return <><button className="secondary truth-back" onClick={() => setSelected(null)}>{t("phase10.action.backToActivity")}</button><EpisodeDetail t={t} detail={selected} /></>;
  if (!activity) return <div className="truth-page"><LoadState t={t} error={error} retry={() => void refresh()} /></div>;
  return <div className="truth-page"><header className="truth-heading"><div><span className="eyebrow">{t("phase10.activity.eyebrow")}</span><h1>{t("phase10.activity.title")}</h1><p>{t("phase10.activity.subtitle")}</p></div><span className="truth-count">{t("phase10.activity.total", { count: activity.total })}</span></header>{error && <LoadState t={t} error={error} retry={() => void refresh()} />}<section className="panel truth-timeline" aria-label={t("phase10.activity.timelineLabel")}>{activity.items.length ? activity.items.map((item) => <ActivityRow key={`${item.entity_type}-${item.id}`} t={t} item={item} open={item.entity_type === "episode" ? () => void open(item.entity_type, item.entity_id) : undefined} />) : <p className="muted">{t("phase10.home.noActivity")}</p>}</section>{activity.has_more && <button className="secondary">{t("phase10.action.loadMore")}</button>}</div>;
}

export function OperationalRegression({ t, projectId, regressionId, data, technicalOpen = false, createRepair, review, dismiss }: {
  t: T;
  projectId: string;
  regressionId: string;
  data?: RegressionTruthDetail;
  technicalOpen?: boolean;
  createRepair?: () => void;
  review?: () => void;
  dismiss?: () => void;
}) {
  const [detail, setDetail] = useState<RegressionTruthDetail | null>(data ?? null);
  const [error, setError] = useState("");
  const refresh = useCallback(async () => {
    if (data) return;
    try { setDetail(await getRegressionTruthDetail(projectId, regressionId)); setError(""); }
    catch (reason) { setError(String(reason)); }
  }, [data, projectId, regressionId]);
  useEffect(() => { void refresh(); }, [refresh]);
  useLocalEvents(projectId, () => { void refresh(); });
  if (!detail) return <div className="truth-page"><LoadState t={t} error={error} retry={() => void refresh()} /></div>;
  return <div className="truth-page truth-detail"><header className="truth-heading"><div><span className="eyebrow">{t("phase10.regression.eyebrow")}</span><h1>{t("phase10.regression.title")}</h1><p>{String(detail.behavior.name)}</p></div><TruthPill t={t} state={detail.status} /></header>
    <section className="truth-regression-summary"><div><span>{t("phase10.regression.lastKnownGood")}</span><strong>{String(detail.last_known_good.save_point_name ?? t("phase10.common.noneRecorded"))}</strong><small>{t("phase10.regression.priorResult", { state: humanState(t, String(detail.last_known_good.result ?? "PASS")) })}</small></div><span className="truth-arrow" aria-hidden="true">→</span><div><span>{t("phase10.regression.current")}</span><strong>{humanState(t, detail.current.result)}</strong><small>{t("phase10.check.attempts", { count: detail.current.attempt_count })}</small></div></section>
    <div className="truth-columns"><section className="panel truth-section"><h2>{t("phase10.regression.expected")}</h2><p>{String(detail.behavior.expected_outcome)}</p><h2>{t("phase10.regression.observed")}</h2><pre className="truth-observed" dir="ltr">{JSON.stringify(detail.current.observed, null, 2)}</pre></section><section className="panel truth-section"><h2>{t("phase10.regression.changed")}</h2><ul>{(detail.changed.paths as string[]).map((path) => <li key={path}><code dir="ltr">{path}</code></li>)}</ul><h2>{t("phase10.regression.whySelected")}</h2><p>{String(detail.selection.reason)}</p></section></div>
    <section className="panel truth-section"><div className="section-head"><div><h2>{t("phase10.regression.evidence")}</h2><p>{t("phase10.regression.evidenceBody")}</p></div></div>{detail.evidence_timeline.map((item) => <ActivityRow key={item.id} t={t} item={item} />)}</section>
    <LimitationList t={t} values={detail.unknowns} />
    <div className="button-row truth-actions"><button className="secondary" onClick={() => void refresh()}>{t("phase10.action.runAgain")}</button><button className="secondary">{t("phase10.action.reviewChange")}</button><button className="primary" onClick={createRepair}>{t("phase10.action.createRepair")}</button><button className="secondary" onClick={review}>{t("phase10.action.markReviewed")}</button><button className="secondary" onClick={dismiss}>{t("phase10.action.dismissReason")}</button></div>
    <details open={technicalOpen} className="panel truth-technical"><summary>{t("phase10.technicalDetails")}</summary><div className="truth-code-list">{detail.reason_codes.map((code) => <code dir="ltr" key={code}>{code}</code>)}</div><pre dir="ltr">{JSON.stringify({ source_identity: detail.current.source_identity, selection: detail.selection }, null, 2)}</pre></details>
  </div>;
}

export function OperationalDiagnostics({ t, data, openSelfTest }: { t: T; data?: DiagnosticsTruthOverview; openSelfTest?: () => void }) {
  const [overview, setOverview] = useState<DiagnosticsTruthOverview | null>(data ?? null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const firstLoad = useRef(true);
  const refresh = useCallback(async () => {
    if (data) return;
    const started = performance.now();
    try {
      setOverview(await getDiagnosticsTruthOverview());
      setError("");
      if (firstLoad.current) {
        firstLoad.current = false;
        void recordPerformanceMetric("diagnostics_load", performance.now() - started, "diagnostics");
      }
    }
    catch (reason) { setError(String(reason)); }
  }, [data]);
  useEffect(() => { void refresh(); }, [refresh]);
  const bundle = async () => {
    try {
      const created = await exportSupportBundle();
      const id = String(created.id ?? "");
      setResult(id ? await getSupportBundle(id) : created);
    } catch (reason) { setError(String(reason)); }
  };
  if (!overview) return <div className="truth-page"><LoadState t={t} error={error} retry={() => void refresh()} /></div>;
  return <div className="truth-page"><header className="truth-heading"><div><span className="eyebrow">{t("phase10.diagnostics.eyebrow")}</span><h1>{t("phase10.diagnostics.title")}</h1><p>{t("phase10.diagnostics.subtitle")}</p></div><button className="secondary" onClick={() => void refresh()}>{t("phase10.action.refresh")}</button></header>
    {error && <LoadState t={t} error={error} retry={() => void refresh()} />}
    <section className="truth-diagnostic-grid">{overview.facts.map((fact) => <article className="panel" key={fact.key}><span>{t(`phase10.diagnostic.${fact.key}`)}</span><TruthPill t={t} state={fact.state} /><strong dir={fact.key === "local_api" ? "ltr" : undefined}>{String(fact.value)}</strong></article>)}</section>
    <div className="truth-columns"><section className="panel truth-section"><h2>{t("phase10.diagnostics.storage")}</h2><dl className="truth-dl">{Object.entries(overview.counts).map(([key, value]) => <div key={key}><dt>{t(`phase10.diagnostic.count.${key}`)}</dt><dd>{value}</dd></div>)}</dl></section><section className="panel truth-section"><h2>{t("phase10.diagnostics.privacy")}</h2><dl className="truth-dl">{Object.entries(overview.privacy).map(([key, value]) => <div key={key}><dt>{t(`phase10.diagnostic.privacy.${key}`)}</dt><dd>{String(value)}</dd></div>)}</dl></section></div>
    <LimitationList t={t} values={overview.limitations} />
    <div className="button-row truth-actions"><button className="primary" onClick={openSelfTest}>{t("phase10.action.selfTest")}</button><button className="secondary" onClick={() => void bundle()}>{t("phase10.action.supportBundle")}</button><button className="secondary" onClick={() => void navigator.clipboard.writeText(JSON.stringify(overview, null, 2))}>{t("phase10.action.copyRedacted")}</button></div>
    {result && <SupportManifest t={t} manifest={result} />}
  </div>;
}

export function SelfTestSurface({ t, capture }: { t: T; capture?: "running" | "passed" }) {
  const [run, setRun] = useState<ProductSelfTestRun | null>(capture ? syntheticSelfTest(capture) : null);
  const [running, setRunning] = useState(capture === "running");
  const [error, setError] = useState("");
  const execute = async () => {
    setRunning(true); setError("");
    try { setRun(await runProductSelfTest()); }
    catch (reason) { setError(String(reason)); }
    finally { setRunning(false); }
  };
  return <div className="truth-page"><header className="truth-heading"><div><span className="eyebrow">{t("phase10.selfTest.eyebrow")}</span><h1>{t("phase10.selfTest.title")}</h1><p>{t("phase10.selfTest.subtitle")}</p></div>{run && <TruthPill t={t} state={running ? "ACTIVE" : run.status === "PASS" ? "PASS" : run.status} />}</header>
    {error && <LoadState t={t} error={error} retry={() => void execute()} />}
    {!run && !running && <section className="panel truth-section"><h2>{t("phase10.selfTest.waiting")}</h2><p>{t("phase10.selfTest.waitingBody")}</p><button className="primary" onClick={() => void execute()}>{t("phase10.action.runSelfTest")}</button></section>}
    {(run || running) && <section className="panel truth-section" aria-live="polite"><div className="section-head"><div><h2>{t(running ? "phase10.selfTest.running" : "phase10.selfTest.result")}</h2><p>{t("phase10.selfTest.noNetwork")}</p></div><span>{run ? t("phase10.selfTest.progress", { complete: run.steps.filter((step) => step.status !== "WAITING").length, total: run.steps.length }) : t("phase10.selfTest.starting")}</span></div><div className="truth-step-list">{(run?.steps ?? []).map((step, index) => { const stepName = String(step.step ?? step.id ?? "unknown"); return <div key={`${stepName}-${index}`}><TruthPill t={t} state={String(step.status ?? step.result ?? "NOT_RUN")} /><strong>{t(`phase10.selfTest.step.${stepName}`)}</strong><small>{String(step.duration_ms ?? 0)} ms</small></div>; })}</div><div className="button-row">{running && run && <button className="secondary" onClick={() => void cancelProductSelfTest(run.id)}>{t("phase10.action.cancel")}</button>}{run && !running && <button className="secondary" onClick={() => void exportProductSelfTest(run.id)}>{t("phase10.action.export")}</button>}</div></section>}
  </div>;
}

function SupportManifest({ t, manifest }: { t: T; manifest: Record<string, unknown> }) {
  const included = (manifest.included as unknown[] | undefined) ?? (manifest.manifest as unknown[] | undefined) ?? [];
  const excluded = (manifest.excluded as unknown[] | undefined) ?? [];
  return <section className="panel truth-section"><div className="section-head"><div><h2>{t("phase10.support.title")}</h2><p>{t("phase10.support.subtitle")}</p></div><TruthPill t={t} state="VERIFIED" /></div><div className="truth-columns"><div><h3>{t("phase10.support.included")}</h3><ul>{included.map((item, index) => <li key={index}><code dir="ltr">{String(item)}</code></li>)}</ul></div><div><h3>{t("phase10.support.excluded")}</h3><ul>{excluded.map((item, index) => <li key={index}><code dir="ltr">{String(item)}</code></li>)}</ul></div></div><p>{t("phase10.support.redacted")}</p><details><summary>{t("phase10.technicalDetails")}</summary><pre dir="ltr">{JSON.stringify(manifest, null, 2)}</pre></details></section>;
}

export function ActivityModeSettings({ t, capture }: { t: T; capture?: ActivityPreferences }) {
  const [preferences, setPreferences] = useState<ActivityPreferences | null>(capture ?? null);
  const [error, setError] = useState("");
  useEffect(() => { if (!capture) void getActivityPreferences().then(setPreferences).catch((reason: unknown) => setError(String(reason))); }, [capture]);
  const choose = async (mode: ActivityPreferences["activity_mode"]) => {
    if (capture) { setPreferences({ ...capture, activity_mode: mode }); return; }
    try { setPreferences(await setActivityMode(mode)); } catch (reason) { setError(String(reason)); }
  };
  return <section className="panel truth-settings-group"><div><h2>{t("phase10.activityMode.title")}</h2><p>{t("phase10.activityMode.subtitle")}</p></div>{error && <p role="alert">{t("phase10.load.failedBody")}</p>}<div className="truth-mode-grid" role="radiogroup" aria-label={t("phase10.activityMode.title")}>{(["normal", "reduced", "battery_saver"] as const).map((mode) => <label className={preferences?.activity_mode === mode ? "selected" : ""} key={mode}><input type="radio" name="activity-mode" checked={preferences?.activity_mode === mode} onChange={() => void choose(mode)} /><strong>{t(`phase10.activityMode.${mode}`)}</strong><span>{t(`phase10.activityMode.${mode}.body`)}</span></label>)}</div><div className="truth-columns"><div><h3>{t("phase10.activityMode.always")}</h3><ul>{["files", "episodes", "snapshots", "alerts", "recovery"].map((item) => <li key={item}>{t(`phase10.activityMode.always.${item}`)}</li>)}</ul></div><div><h3>{t("phase10.activityMode.deferred")}</h3><ul>{["probes", "traces", "runtime", "updates"].map((item) => <li key={item}>{t(`phase10.activityMode.deferred.${item}`)}</li>)}</ul></div></div></section>;
}

function WorkflowSurface({ t, state }: { t: T; state: Phase10CaptureState }) {
  const type = state.startsWith("candidate") ? "candidate" : state.startsWith("apply") || state === "applied-and-verified" ? "apply" : state.includes("rollback") ? "rollback" : state.startsWith("repair") ? "repair" : state.startsWith("behavior") || state.startsWith("check") ? "behavior" : "location";
  const steps = type === "apply" ? ["preflight", "safety", "journal", "prepare", "apply", "capture", "verify", "commit"] : type === "candidate" ? ["manifest", "diff", "runtime", "checks", "freshness"] : type === "repair" ? ["snapshot", "workspace", "changes", "validation"] : ["identity", "evidence", "result"];
  const progress = state === "apply-transaction-progress" || state === "candidate-validation-progress" ? Math.ceil(steps.length / 2) : steps.length;
  const workflowId = `demo-${type}-181`;
  const workflowFiles = ["src/checkout.ts", "tests/checkout.test.ts"];
  return <div className="truth-page"><header className="truth-heading"><div><span className="eyebrow">{t(`phase10.workflow.${type}.eyebrow`)}</span><h1>{t(`phase10.capture.${state}.title`)}</h1><p>{t(`phase10.capture.${state}.body`)}</p></div><TruthPill t={t} state={state === "rolled-back-safely" ? "ROLLED_BACK" : state === "applied-and-verified" || state === "candidate-validated" ? "VERIFIED" : state.includes("progress") ? "ACTIVE" : "READY"} /></header><section className="panel truth-section"><div className="section-head"><div><h2>{t(`phase10.workflow.${type}.summary`)}</h2><p>{t(`phase10.workflow.${type}.summaryBody`)}</p></div><code dir="ltr">{workflowId}</code></div><div className="truth-step-list">{steps.map((step, index) => <div key={step}><TruthPill t={t} state={index < progress ? "VERIFIED" : index === progress ? "ACTIVE" : "NOT_RUN"} /><strong>{t(`phase10.workflow.step.${step}`)}</strong><small>{t(index < progress ? "phase10.workflow.complete" : "phase10.workflow.pending")}</small></div>)}</div></section><div className="truth-columns"><section className="panel truth-section"><h2>{t("phase10.workflow.files")}</h2><ul>{workflowFiles.map((path) => <li key={path}><code dir="ltr">{path}</code></li>)}</ul></section><section className="panel truth-section"><h2>{t("phase10.workflow.safety")}</h2><ul><li>{t("phase10.workflow.sourceBound")}</li><li>{t("phase10.workflow.liveNotVerified")}</li><li>{t("phase10.workflow.explicitOnly")}</li></ul></section></div><div className="button-row truth-actions"><button className="secondary">{t("phase10.action.technical")}</button><button className="primary">{t(`phase10.workflow.${type}.primary`)}</button></div></div>;
}

function TrayPreview({ t }: { t: T }) {
  return <div className="truth-page"><header className="truth-heading"><div><span className="eyebrow">{t("phase10.tray.previewLabel")}</span><h1>{t("phase10.tray.title")}</h1><p>{t("phase10.tray.subtitle")}</p></div></header><section className="truth-native-preview"><div className="truth-tray-head"><strong>{t("brand.name")}</strong><TruthPill t={t} state="NEEDS_ATTENTION" /></div><button>{t("phase10.tray.show")}</button><button>{t("phase10.tray.project", { name: "MellowYak Demo" })}</button><div className="truth-tray-sub"><button>{t("phase10.action.open")}</button><button>{t("phase10.action.pause")}</button><button>{t("phase10.tray.mute")}</button></div><button>{t("phase10.tray.quiet")}</button><button>{t("phase10.diagnostics.title")}</button><button>{t("phase10.tray.quit")}</button></section><p className="truth-preview-warning">{t("phase10.tray.previewWarning")}</p></div>;
}

function LocationSurface({ t, state }: { t: T; state: Phase10CaptureState }) {
  const mismatch = state === "project-mismatch-alert";
  const preview = state === "reconnect-identity-preview";
  const identity = "8e7a44c9b1f2";
  return <div className="truth-page"><header className="truth-heading"><div><span className="eyebrow">{t("phase10.location.eyebrow")}</span><h1>{t(`phase10.capture.${state}.title`)}</h1><p>{t(`phase10.capture.${state}.body`)}</p></div><TruthPill t={t} state={mismatch ? "NEEDS_REVIEW" : "DISCONNECTED"} /></header><article className="panel truth-location"><div><h2>{t("phase10.demo.projectName")}</h2><span>{t("phase10.location.retained", { behaviors: 3, regressions: 1, size: "1.4 MiB" })}</span></div>{preview && <dl className="truth-dl"><div><dt>{t("phase10.location.previousIdentity")}</dt><dd dir="ltr">{identity}</dd></div><div><dt>{t("phase10.location.selectedIdentity")}</dt><dd dir="ltr">{identity}</dd></div><div><dt>{t("phase10.location.match")}</dt><dd>{t("phase10.common.yes")}</dd></div></dl>}{mismatch && <div className="truth-mismatch" role="alert"><strong>{t("phase10.location.mismatchTitle")}</strong><p>{t("phase10.location.mismatchBody")}</p></div>}<div className="button-row"><button className="primary">{t("phase10.location.chooseFolder")}</button><button className="secondary">{t("phase10.location.reconnect")}</button>{mismatch && <button className="secondary">{t("phase10.location.addNew")}</button>}</div></article></div>;
}

function UpdateStatusSurface({ t, capture = true }: { t: T; capture?: boolean }) {
  const [status, setStatus] = useState<Record<string, unknown> | null>(capture ? { state: "NO_UPDATE", current_version: "0.4.0-preview.1", last_check_at: "2026-08-26T08:45:00Z", signature_required: true } : null);
  const [acceptance, setAcceptance] = useState<Record<string, unknown> | null>(capture ? { status: "VERIFIED_WORKING", platform: "macOS x86_64" } : null);
  useEffect(() => { if (!capture) void Promise.all([getUpdaterStatus(), getPackageAcceptance()]).then(([next, packageResult]) => { setStatus(next); setAcceptance(packageResult); }); }, [capture]);
  return <div className="truth-page"><header className="truth-heading"><div><span className="eyebrow">{t("phase10.update.eyebrow")}</span><h1>{t("phase10.update.title")}</h1><p>{t("phase10.update.subtitle")}</p></div><TruthPill t={t} state={String(status?.state ?? "NOT_RUN")} /></header><section className="panel truth-section"><dl className="truth-dl"><div><dt>{t("phase10.update.current")}</dt><dd dir="ltr">{String(status?.current_version ?? "—")}</dd></div><div><dt>{t("phase10.update.lastCheck")}</dt><dd>{dateTime(String(status?.last_check_at ?? ""))}</dd></div><div><dt>{t("phase10.update.signature")}</dt><dd>{String(status?.signature_required ?? true)}</dd></div><div><dt>{t("phase10.update.package")}</dt><dd>{String(acceptance?.status ?? "—")}</dd></div></dl><button className="secondary">{t("phase10.update.check")}</button></section></div>;
}

const syntheticHome = (attention = false): HomeSummary => ({
  state: attention ? "NEEDS_ATTENTION" : "EVERYTHING_LOOKS_OKAY",
  counts: { monitored: 2, paused: 1, disconnected: 0, needs_setup: 0, confirmed_regressions: attention ? 1 : 0, needs_review: attention ? 1 : 0, blocked_or_recovery: 0, unread_alerts: attention ? 2 : 0 },
  projects: [syntheticProjectSummary(attention), { ...syntheticProjectSummary(false), id: "demo-api", display_name: "Demo API", runtime_state: "READY", protected_behavior_count: 2 }],
  attention: attention ? [syntheticProjectSummary(true)] : [],
  recent_activity: syntheticActivity(attention).items.slice(0, 5),
  known: ["LOCAL_DATABASE", "REGISTERED_PROJECTS", "RECORDED_CHECKS"],
  unknowns: attention ? ["ROOT_CAUSE_NOT_PROVEN"] : [],
});

function syntheticProjectSummary(attention: boolean): HomeSummary["projects"][number] {
  return {
    id: "demo-project",
    display_name: "MellowYak Demo",
    state: attention ? "NEEDS_ATTENTION" : "NO_CONFIRMED_ISSUE",
    monitoring_state: "active",
    source_available: true,
    runtime_state: "READY",
    last_episode: { id: "episode-181", changed_count: 4, started_at: "2026-08-25T08:39:00Z", ended_at: "2026-08-25T08:42:00Z", signal: attention ? "CONFIRMED" : "WATCH" },
    last_save_point: { id: "snapshot-181", creation_reason: "EPISODE_STABILIZED", integrity_status: "VERIFIED", created_at: "2026-08-25T08:42:00Z" },
    protected_behavior_count: 3,
    latest_check: syntheticCheck(attention ? "FAIL" : "PASS"),
    open_regression_count: attention ? 1 : 0,
    recovery_required_count: 0,
    last_activity_at: "2026-08-25T08:42:00Z",
    limitations: attention ? ["ROOT_CAUSE_NOT_PROVEN"] : [],
  };
}

function syntheticCheck(result: string): NonNullable<HomeSummary["projects"][number]["latest_check"]> {
  return { id: "probe-run-181", name: "Checkout check", behavior_id: "checkout", behavior_name: "Checkout", result, status: "COMPLETED", source_identity: { snapshot_id: "snapshot-181" }, runtime_profile_version_id: "runtime-v3", duration_ms: 842, attempt_count: result === "FAIL" ? 2 : 1, expected: { outcome: "Order confirmation appears" }, observed: result === "FAIL" ? { outcome: "Payment request returned 500" } : { outcome: "Order confirmation appeared" }, evidence: { artifact_count: 2 }, limitations: [], completed_at: "2026-08-25T08:42:00Z" };
}

function syntheticActivity(attention = false): ProjectTruthActivity {
  const base = { project_id: "demo-project" };
  return { project_id: "demo-project", offset: 0, limit: 25, total: 5, has_more: false, items: [
    { ...base, id: "episode-181", event_type: "EPISODE_STABILIZED", created_at: "2026-08-25T08:42:00Z", entity_type: "episode", entity_id: "episode-181", state: attention ? "CONFIRMED" : "WATCH", facts: { changed_count: 4, checks_run: 1, checks_passed: attention ? 0 : 1, checks_failed: attention ? 1 : 0 } },
    { ...base, id: "check-181", event_type: "CHECK_COMPLETED", created_at: "2026-08-25T08:41:30Z", entity_type: "check", entity_id: "check-181", state: attention ? "FAIL" : "PASS", facts: { check_name: "Checkout check", attempt_count: attention ? 2 : 1 } },
    { ...base, id: "snapshot-181", event_type: "SNAPSHOT_CREATED", created_at: "2026-08-25T08:40:00Z", entity_type: "snapshot", entity_id: "snapshot-181", state: "VERIFIED", facts: {} },
    { ...base, id: "episode-180", event_type: "EPISODE_STABILIZED", created_at: "2026-08-25T07:55:00Z", entity_type: "episode", entity_id: "episode-180", state: "WATCH", facts: { changed_count: 1 } },
    { ...base, id: "check-180", event_type: "CHECK_COMPLETED", created_at: "2026-08-25T07:54:30Z", entity_type: "check", entity_id: "check-180", state: "PASS", facts: {} },
  ] };
}

function syntheticEpisode(result = "WATCH"): EpisodeTruthDetail {
  return { project_id: "demo-project", episode: { id: "episode-181", started_at: "2026-08-25T08:39:00Z", ended_at: "2026-08-25T08:42:00Z", status: "STABILIZED", changed_count: 4, signal: result }, changed: { added: ["src/checkout/discount.ts"], modified: ["src/checkout/checkout.ts", "tests/checkout.test.ts"], deleted: [], renamed: [], dependencies: ["package-lock.json"] }, may_be_affected: [{ behavior_id: "checkout", behavior_name: "Checkout", provenance: ["STATIC_RELATION", "TEST_RELATION"] }], checks: [syntheticCheck(result === "CONFIRMED" ? "FAIL" : "PASS")], not_checked: [{ behavior_id: "profile", behavior_name: "Profile update", reason_code: "NOT_RELATED_TO_CHANGE" }], result: { signal: result, reason_codes: result === "CONFIRMED" ? ["BASELINE_PASS_CURRENT_REPEATED_FAIL"] : ["FILES_CHANGED_ONLY"], friendly_key: "episode.result" }, technical: { base_snapshot_id: "snapshot-180", resulting_snapshot_id: "snapshot-181", git_anchor: { head_sha: "8e7a44c9b1f2" }, runtime_events: [], truncated: false }, unknowns: ["ROOT_CAUSE_NOT_PROVEN"] };
}

function syntheticOverview(limited = false): ProjectTruthOverview {
  return { project: { ...syntheticProjectSummary(false), state: limited ? "READY_WITH_LIMITS" : "NO_CONFIRMED_ISSUE", runtime_state: limited ? "RUNTIME_UNAVAILABLE" : "READY", limitations: limited ? ["RUNTIME_NOT_CONFIGURED", "ONE_UNKNOWN_BOUNDARY"] : [] }, source_identity: { branch: "product/demo", head_sha: "8e7a44c9b1f2", worktree_fingerprint: "demo-fingerprint-181" }, last_known_good: { id: "milestone-181", snapshot_id: "snapshot-181", display_name: "Checkout known good", status: "ACCEPTED", human_attested: false, created_at: "2026-08-25T08:00:00Z" }, latest_checks: [syntheticCheck("PASS")], storage: { snapshot_count: 18, logical_bytes: 1482752, integrity_state: "VERIFIED", retention_days: 30, soft_cap_bytes: 5368709120 }, recent_activity: syntheticActivity(false).items.slice(0, 3), known: ["SOURCE_IDENTITY", "RECORDED_EPISODES", "RECORDED_CHECKS"], unknowns: limited ? ["RUNTIME_NOT_CONFIGURED", "ONE_UNKNOWN_BOUNDARY"] : [] };
}

function syntheticRegression(): RegressionTruthDetail {
  return { id: "regression-181", project_id: "demo-project", status: "CONFIRMED", behavior: { id: "checkout", name: "Checkout", expected_outcome: "Order confirmation appears after payment" }, last_known_good: { baseline_id: "baseline-180", status: "ACCEPTED", snapshot_id: "snapshot-180", save_point_name: "Checkout known good", source_identity: { snapshot_id: "snapshot-180" }, created_at: "2026-08-25T07:50:00Z" }, current: syntheticCheck("FAIL"), changed: { change_id: "change-181", paths: ["src/checkout/checkout.ts", "src/checkout/discount.ts"] }, selection: { reason: "Checkout is explicitly linked to the changed route and has an accepted baseline.", relation_provenance: ["STATIC_RELATION", "TEST_RELATION"] }, reason_codes: ["BASELINE_ACCEPTED_PASS", "CURRENT_FAIL", "RETRY_FAIL", "SOURCE_IDENTITY_MATCH"], evidence_timeline: [syntheticActivity(true).items[1], syntheticActivity(true).items[0]], unknowns: ["ROOT_CAUSE_NOT_PROVEN", "BLAST_RADIUS_MAY_BE_INCOMPLETE"] };
}

function syntheticDiagnostics(): DiagnosticsTruthOverview {
  return { facts: [{ key: "local_api", state: "AUTHENTICATED_LOOPBACK", value: "127.0.0.1:<ephemeral>" }, { key: "database", state: "READY", value: "0009_technical_preview_readiness" }, { key: "storage", state: "READY", value: 1482752 }, { key: "browser_runtime", state: "AVAILABLE", value: true }, { key: "runtime_adapter", state: "AVAILABLE", value: true }, { key: "updater", state: "PRODUCTION_CHANNEL_UNPUBLISHED", value: "LOCAL_E2E_PASS" }, { key: "signing", state: "AD_HOC_SIGNED", value: "AD_HOC_SIGNED" }, { key: "developer_id", state: "NO", value: false }, { key: "notarized", state: "NO", value: false }, { key: "public_distribution", state: "NOT_READY", value: false }, { key: "updater_fixture", state: "PASS", value: "PASS" }, { key: "production_updater", state: "PRODUCTION_CHANNEL_UNPUBLISHED", value: false }], counts: { projects: 1, snapshot_objects: 48, incomplete_transactions: 0, recovery_required: 0 }, privacy: { bearer_token_exposed: false, outbound_product_network: false, cloud_connected: false, copy_redacted: true }, platform: { name: "Darwin", architecture: "x86_64", signing: "AD_HOC_SIGNED" }, last_self_test: "PASS", limitations: ["PUBLIC_DISTRIBUTION_NOT_READY"] };
}

function syntheticSelfTest(state: "running" | "passed"): ProductSelfTestRun {
  const ids = ["database", "snapshot", "probe", "regression", "candidate", "apply", "rollback", "cleanup"];
  return { id: "self-test-181", status: state === "passed" ? "PASS" : "RUNNING", steps: ids.map((id, index) => ({ id, status: state === "passed" || index < 4 ? "PASS" : index === 4 ? "ACTIVE" : "NOT_RUN", duration_ms: state === "passed" || index < 4 ? 120 + index * 21 : 0 })), duration_ms: state === "passed" ? 1884 : 741, report_relative_path: null, created_at: "2026-08-25T08:30:00Z", completed_at: state === "passed" ? "2026-08-25T08:30:02Z" : null };
}

export function Phase10Capture({ state, t }: { state: Phase10CaptureState; t: T }) {
  const firstRunStep = state === "first-run-welcome" ? "welcome" : state.includes("choice") || state.includes("selected") ? "choice" : state.includes("background") ? "privacy" : "complete";
  if (state.startsWith("first-run")) return <FirstRunExperience state={{ completed: false, current_step: firstRunStep, replay_active: false, selected_path: state.includes("selected") || state.includes("complete") ? "demo_lab" : null, completed_at: null, requires_first_run: true, source_modified: false }} t={t as never} onAddProject={() => undefined} onDemo={() => undefined} onComplete={() => undefined} />;
  if (["home-no-confirmed-issue", "home-needs-attention", "hebrew-home"].includes(state)) return <OperationalHome t={t} data={syntheticHome(state === "home-needs-attention")} openProject={() => undefined} />;
  if (["project-overview-healthy", "project-overview-ready-with-limits", "hebrew-project-overview"].includes(state)) return <OperationalProjectOverview t={t} projectId="demo-project" data={syntheticOverview(state === "project-overview-ready-with-limits")} />;
  if (state === "project-activity-timeline") return <OperationalActivity t={t} projectId="demo-project" data={syntheticActivity()} />;
  if (["episode-detail", "check-passed-no-regression"].includes(state)) return <EpisodeDetail t={t} detail={syntheticEpisode()} />;
  if (["regression-friendly", "regression-technical", "hebrew-regression"].includes(state)) return <OperationalRegression t={t} projectId="demo-project" regressionId="regression-181" data={syntheticRegression()} technicalOpen={state === "regression-technical"} />;
  if (["disconnected-projects", "reconnect-identity-preview", "project-mismatch-alert"].includes(state)) return <LocationSurface t={t} state={state} />;
  if (["diagnostics-real-data", "hebrew-diagnostics"].includes(state)) return <OperationalDiagnostics t={t} data={syntheticDiagnostics()} />;
  if (state === "self-test-running") return <SelfTestSurface t={t} capture="running" />;
  if (state === "self-test-passed") return <SelfTestSurface t={t} capture="passed" />;
  if (state === "support-bundle-manifest") return <div className="truth-page"><SupportManifest t={t} manifest={{ id: "support-181", included: ["diagnostics.json", "engine.log.redacted", "manifest.json"], excluded: ["source", "snapshots", "evidence", "tokens", "full_paths"], redaction_state: "VERIFIED", checksum: "d9f60e…" }} /></div>;
  if (state === "update-status") return <UpdateStatusSurface t={t} />;
  if (state === "activity-mode-settings") return <div className="truth-page"><ActivityModeSettings t={t} capture={{ activity_mode: "battery_saver", notification_permission: "AUTHORIZED", updater_state: "NO_UPDATE", last_update_check_at: null, core_file_observation: true, snapshot_correctness: true, critical_alerts: true, deferred: ["noncritical_probes", "deep_traces", "optional_runtime_observation", "update_checks"] }} /></div>;
  if (state === "native-tray-preview") return <TrayPreview t={t} />;
  return <WorkflowSurface t={t} state={state} />;
}
