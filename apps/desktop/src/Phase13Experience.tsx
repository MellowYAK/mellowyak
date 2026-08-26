import "./phase13.css";

type T = (key: string, parameters?: Record<string, string | number>) => string;

export const phase13CaptureStates = [
  "00-monitoring-policy-default", "01-project-auto-check-policy", "02-behavior-auto-check-policy",
  "03-passive-monitoring-idle", "04-filesystem-burst-observed", "05-episode-settling",
  "06-episode-stabilized", "07-impact-plan-created", "08-checks-selected-and-omitted",
  "09-automatic-check-queued", "10-runtime-starting", "11-automatic-check-running",
  "12-automatic-check-passed", "13-no-regression-result", "14-controlled-regression-running",
  "15-retry-in-progress", "16-confirmed-regression-deduplicated", "17-tray-needs-attention",
  "18-flaky-check-detected", "19-runtime-unavailable", "20-rapid-writes-one-episode",
  "21-large-fanout-sentinel-selection", "22-lockfile-change-plan", "23-job-superseded-stale",
  "24-scheduler-recovered", "25-battery-saver-deferred", "26-normal-mode-resumed",
  "27-quiet-mode-alert-persisted", "28-home-background-monitoring",
  "29-project-overview-background-result", "30-activity-orchestration-timeline",
  "31-advanced-queue", "32-impact-memory", "33-monitoring-settings",
  "34-hebrew-home-background", "35-hebrew-impact-plan", "36-hebrew-flaky-state",
  "37-hebrew-monitoring-settings",
] as const;

export type Phase13CaptureState = typeof phase13CaptureStates[number];
type Tone = "calm" | "active" | "warn" | "bad" | "good";

const stateTruth: Record<Phase13CaptureState, { current: string; previous: string; tone: Tone; selected: number; omitted: number; policy: string }> = {
  "00-monitoring-policy-default": { current: "ASK_BEFORE_CHECKS", previous: "INSTALLATION_DEFAULT", tone: "calm", selected: 0, omitted: 0, policy: "ASK_BEFORE_CHECKS" },
  "01-project-auto-check-policy": { current: "AUTO_SAFE", previous: "ASK_BEFORE_CHECKS", tone: "good", selected: 0, omitted: 0, policy: "AUTO_SAFE" },
  "02-behavior-auto-check-policy": { current: "AUTOMATIC", previous: "ASK", tone: "good", selected: 1, omitted: 0, policy: "AUTOMATIC" },
  "03-passive-monitoring-idle": { current: "OBSERVING", previous: "IDLE", tone: "calm", selected: 0, omitted: 0, policy: "AUTO_SAFE" },
  "04-filesystem-burst-observed": { current: "DEBOUNCING", previous: "OBSERVING", tone: "active", selected: 0, omitted: 0, policy: "AUTO_SAFE" },
  "05-episode-settling": { current: "SETTLING", previous: "DEBOUNCING", tone: "active", selected: 0, omitted: 0, policy: "AUTO_SAFE" },
  "06-episode-stabilized": { current: "SNAPSHOTTING", previous: "SETTLING", tone: "active", selected: 0, omitted: 0, policy: "AUTO_SAFE" },
  "07-impact-plan-created": { current: "ANALYZING_IMPACT", previous: "SNAPSHOTTING", tone: "active", selected: 2, omitted: 2, policy: "AUTO_SAFE" },
  "08-checks-selected-and-omitted": { current: "BUILDING_PLAN", previous: "ANALYZING_IMPACT", tone: "active", selected: 2, omitted: 5, policy: "AUTO_SAFE" },
  "09-automatic-check-queued": { current: "QUEUED", previous: "WAITING_FOR_POLICY", tone: "active", selected: 2, omitted: 2, policy: "AUTO_SAFE" },
  "10-runtime-starting": { current: "STARTING_RUNTIME", previous: "QUEUED", tone: "active", selected: 2, omitted: 2, policy: "AUTO_SAFE" },
  "11-automatic-check-running": { current: "RUNNING_CHECKS", previous: "STARTING_RUNTIME", tone: "active", selected: 2, omitted: 2, policy: "AUTO_SAFE" },
  "12-automatic-check-passed": { current: "PERSISTING_RESULT", previous: "RUNNING_CHECKS", tone: "good", selected: 2, omitted: 2, policy: "AUTO_SAFE" },
  "13-no-regression-result": { current: "COMPLETE", previous: "CLASSIFYING", tone: "good", selected: 1, omitted: 3, policy: "AUTO_SAFE" },
  "14-controlled-regression-running": { current: "RUNNING_CHECKS", previous: "QUEUED", tone: "active", selected: 2, omitted: 2, policy: "AUTO_SAFE" },
  "15-retry-in-progress": { current: "RETRYING", previous: "RUNNING_CHECKS", tone: "warn", selected: 2, omitted: 2, policy: "AUTO_SAFE" },
  "16-confirmed-regression-deduplicated": { current: "NOTIFYING", previous: "CLASSIFYING", tone: "bad", selected: 2, omitted: 2, policy: "AUTO_SAFE" },
  "17-tray-needs-attention": { current: "NEEDS_ATTENTION", previous: "MONITORING", tone: "bad", selected: 2, omitted: 2, policy: "AUTO_SAFE" },
  "18-flaky-check-detected": { current: "FLAKY", previous: "RETRYING", tone: "warn", selected: 1, omitted: 3, policy: "AUTO_SAFE" },
  "19-runtime-unavailable": { current: "RUNTIME_UNAVAILABLE", previous: "STARTING_RUNTIME", tone: "warn", selected: 1, omitted: 3, policy: "AUTO_SAFE" },
  "20-rapid-writes-one-episode": { current: "STABILIZED", previous: "DEBOUNCING", tone: "good", selected: 1, omitted: 3, policy: "AUTO_SAFE" },
  "21-large-fanout-sentinel-selection": { current: "BUILDING_PLAN", previous: "ANALYZING_IMPACT", tone: "active", selected: 10, omitted: 990, policy: "AUTO_SAFE" },
  "22-lockfile-change-plan": { current: "BUILDING_PLAN", previous: "SNAPSHOTTING", tone: "warn", selected: 2, omitted: 2, policy: "AUTO_SAFE" },
  "23-job-superseded-stale": { current: "STALE", previous: "QUEUED", tone: "warn", selected: 1, omitted: 3, policy: "AUTO_SAFE" },
  "24-scheduler-recovered": { current: "RECOVERING", previous: "QUEUED", tone: "good", selected: 1, omitted: 3, policy: "AUTO_SAFE" },
  "25-battery-saver-deferred": { current: "DEFERRED", previous: "QUEUED", tone: "warn", selected: 1, omitted: 3, policy: "AUTO_SAFE" },
  "26-normal-mode-resumed": { current: "QUEUED", previous: "DEFERRED", tone: "good", selected: 1, omitted: 3, policy: "AUTO_SAFE" },
  "27-quiet-mode-alert-persisted": { current: "QUIET_MODE", previous: "NOTIFYING", tone: "calm", selected: 2, omitted: 2, policy: "AUTO_SAFE" },
  "28-home-background-monitoring": { current: "MONITORING", previous: "IDLE", tone: "good", selected: 4, omitted: 0, policy: "AUTO_SAFE" },
  "29-project-overview-background-result": { current: "COMPLETE", previous: "RUNNING_CHECKS", tone: "good", selected: 2, omitted: 2, policy: "AUTO_SAFE" },
  "30-activity-orchestration-timeline": { current: "COMPLETE", previous: "PERSISTING_RESULT", tone: "good", selected: 2, omitted: 2, policy: "AUTO_SAFE" },
  "31-advanced-queue": { current: "QUEUED", previous: "BUILDING_PLAN", tone: "active", selected: 5, omitted: 7, policy: "AUTO_SAFE" },
  "32-impact-memory": { current: "STATIC_RELATION", previous: "EXPLICIT_BEHAVIOR_LINK", tone: "calm", selected: 2, omitted: 2, policy: "AUTO_SAFE" },
  "33-monitoring-settings": { current: "AUTO_SAFE", previous: "ASK_BEFORE_CHECKS", tone: "calm", selected: 0, omitted: 0, policy: "AUTO_SAFE" },
  "34-hebrew-home-background": { current: "MONITORING", previous: "IDLE", tone: "good", selected: 4, omitted: 0, policy: "AUTO_SAFE" },
  "35-hebrew-impact-plan": { current: "BUILDING_PLAN", previous: "ANALYZING_IMPACT", tone: "active", selected: 2, omitted: 5, policy: "AUTO_SAFE" },
  "36-hebrew-flaky-state": { current: "FLAKY", previous: "RETRYING", tone: "warn", selected: 1, omitted: 3, policy: "AUTO_SAFE" },
  "37-hebrew-monitoring-settings": { current: "AUTO_SAFE", previous: "ASK_BEFORE_CHECKS", tone: "calm", selected: 0, omitted: 0, policy: "AUTO_SAFE" },
};

const behaviorKeys = ["nearestRide", "driverAvailable", "cancelRide", "farePreview"];
const timelineKeys = ["burst", "opened", "settling", "snapshot", "impact", "selected", "queued", "result"];

export function Phase13Capture({ state, t }: { state: Phase13CaptureState; t: T }) {
  const truth = stateTruth[state];
  const isHebrew = /^3[4-7]-hebrew-/.test(state);
  const progress = Math.min(100, Math.max(8, (phase13CaptureStates.indexOf(state) + 1) * 3));
  return <div className={`phase13-surface phase13-${truth.tone}`} dir={isHebrew ? "rtl" : undefined} data-phase13-fixture="mellowyak.phase13.screenshots.v1" data-phase13-state={state} data-ready="true">
    <header className="phase13-heading"><div><span className="eyebrow">{t("phase13.eyebrow")}</span><h1>{t(`phase13.screen.${state}.title`)}</h1><p>{t(`phase13.screen.${state}.body`)}</p></div><div className={`phase13-orb ${truth.tone}`} role="status" aria-live="polite"><span aria-hidden="true" /><small>{t("phase13.currentState")}</small><strong>{t(`phase13.state.${truth.current}`)}</strong><code dir="ltr">{truth.current}</code></div></header>
    <section className="phase13-metrics" aria-label={t("phase13.metrics")}><article><span>{t("phase13.monitoredProjects")}</span><strong>1</strong></article><article><span>{t("phase13.selectedChecks")}</span><strong>{truth.selected}</strong></article><article><span>{t("phase13.omittedChecks")}</span><strong>{truth.omitted}</strong></article><article><span>{t("phase13.activityMode")}</span><strong>{t(state.includes("battery") ? "phase13.mode.battery" : state.includes("quiet") ? "phase13.mode.quiet" : "phase13.mode.normal")}</strong></article></section>
    <section className="panel phase13-progress-card"><div className="section-head"><div><h2>{t("phase13.sentinel.title")}</h2><p>{t("phase13.sentinel.body")}</p></div><span className={`phase13-pill ${truth.tone}`}>{t(`phase13.state.${truth.current}`)}</span></div><div className="phase13-progress" role="progressbar" aria-label={t("phase13.progress")} aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}><span style={{ width: `${progress}%` }} /></div><div className="phase13-state-row"><div><small>{t("phase13.previousState")}</small><code dir="ltr">{truth.previous}</code></div><div><small>{t("phase13.policy")}</small><code dir="ltr">{truth.policy}</code></div><div><small>{t("phase13.sourceIdentity")}</small><code dir="ltr">{t("phase13.fixture.sourceIdentity")}</code></div><div><small>{t("phase13.safeNextAction")}</small><strong>{t(truth.tone === "bad" ? "phase13.action.review" : truth.tone === "warn" ? "phase13.action.inspect" : "phase13.action.continue")}</strong></div></div></section>
    <div className="phase13-grid"><section className="panel phase13-behaviors"><div className="section-head"><div><h2>{t("phase13.behaviors")}</h2><p>{t("phase13.behaviors.body")}</p></div><span>{truth.selected}/{truth.selected + truth.omitted}</span></div>{behaviorKeys.map((key, index) => <article key={key} className={index < truth.selected ? "selected" : "omitted"}><span className="phase13-check" aria-hidden="true">{index < truth.selected ? "✓" : "○"}</span><div><strong>{t(`phase13.behavior.${key}`)}</strong><small>{t(index < truth.selected ? "phase13.selection.explicit" : "phase13.selection.omitted")}</small></div><span>{t(index < truth.selected ? "phase13.selected" : "phase13.unknown")}</span></article>)}</section><section className="panel phase13-queue"><h2>{t("phase13.queue")}</h2>{["critical", "browser", "runtime", "maintenance"].map((key, index) => <div key={key} className={index === 0 ? "running" : index === 1 && state.includes("battery") ? "deferred" : "queued"}><span>{t(`phase13.job.${key}`)}</span><strong>{t(index === 0 ? "phase13.job.running" : index === 1 && state.includes("battery") ? "phase13.job.deferred" : "phase13.job.queued")}</strong></div>)}</section></div>
    <section className="panel phase13-timeline"><div className="section-head"><div><h2>{t("phase13.timeline")}</h2><p>{t("phase13.timeline.body")}</p></div><code dir="ltr">{t("phase13.fixture.runId")}</code></div><ol>{timelineKeys.map((key, index) => <li key={key} className={index < 6 ? "complete" : index === 6 ? "current" : "pending"}><span aria-hidden="true">{index < 6 ? "✓" : index === 6 ? "●" : "○"}</span><strong>{t(`phase13.timeline.${key}`)}</strong></li>)}</ol></section>
    <div className="phase13-grid"><section className="panel"><h2>{t("phase13.knownFacts")}</h2><ul><li>{t("phase13.fact.local")}</li><li>{t("phase13.fact.bound")}</li><li>{t("phase13.fact.noApply")}</li></ul></section><section className="panel"><h2>{t("phase13.unknowns")}</h2><ul><li>{t("phase13.unknown.omitted")}</li><li>{t("phase13.unknown.causation")}</li></ul></section></div>
  </div>;
}
