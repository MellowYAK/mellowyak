import "./phase14.css";

type T = (key: string, parameters?: Record<string, string | number>) => string;

export const phase14CaptureStates = [
  "00-phase13-verified-closure", "01-public-project-corpus", "02-python-project-compatibility",
  "03-node-project-compatibility", "04-polyglot-project-compatibility", "05-large-project-compatibility",
  "06-runtime-detection-python", "07-runtime-detection-node", "08-monorepo-runtime-ownership",
  "09-gitless-project-ready", "10-observe-only-project", "11-generated-files-excluded",
  "12-sensitive-files-redacted", "13-initial-scan-complete", "14-known-good-browser",
  "15-known-good-api", "16-known-good-cli-test", "17-passive-monitoring-public-project",
  "18-harmless-change-no-regression", "19-impact-selected-real-project", "20-controlled-regression-real-project",
  "21-confirmed-incident-real-project", "22-flaky-real-project", "23-runtime-unavailable-real-project",
  "24-lockfile-change-real-project", "25-large-fanout-bounded", "26-symlink-boundary-blocked",
  "27-watcher-gap-rescan", "28-stale-job-real-project", "29-scheduler-recovery-real-project",
  "30-daily-budget-exhausted", "31-outside-allowed-hours", "32-budget-run-now-override",
  "33-repair-workspace-public-project", "34-candidate-validated-public-project",
  "35-apply-confirmation-public-project", "36-applied-verified-public-project",
  "37-rollback-byte-identical-public-project", "38-soak-test-summary", "39-package-acceptance",
  "40-intel-mac-rc-readiness",
] as const;

export type Phase14CaptureState = typeof phase14CaptureStates[number];
type Tone = "good" | "active" | "warn" | "bad" | "calm";
type Category = "closure" | "corpus" | "runtime" | "evidence" | "orchestration" | "repair" | "release";

type Truth = {
  category: Category;
  project: string;
  revision: string;
  current: string;
  tone: Tone;
  included: number;
  excluded: number;
  unsupported: number;
  selected: number;
  omitted: number;
};

function truthFor(state: Phase14CaptureState): Truth {
  const index = phase14CaptureStates.indexOf(state);
  const isRelease = index >= 38;
  const isRepair = index >= 33 && index <= 37;
  const isOrchestration = index >= 24 && index <= 32;
  const isEvidence = index >= 13 && index <= 23;
  const isRuntime = index >= 6 && index <= 12;
  const category: Category = isRelease ? "release" : isRepair ? "repair" : isOrchestration ? "orchestration" : isEvidence ? "evidence" : isRuntime ? "runtime" : index === 0 ? "closure" : "corpus";
  const project = state.includes("python") || state.includes("api") || state.includes("process") || isRepair || isEvidence ? "datasette" : state.includes("node") ? "excalidraw" : state.includes("polyglot") || state.includes("monorepo") ? "tauri" : state.includes("large") || state.includes("fanout") || state.includes("lockfile") || isOrchestration ? "vite" : state.includes("gitless") ? "datasette-gitless" : isRelease || index === 0 ? "mellowyak" : isRuntime ? "tauri" : "public-corpus";
  const revision = project === "datasette" || project === "datasette-gitless" ? "0337fba234bf" : project === "excalidraw" ? "e1bb9ff8f893" : project === "vite" ? "493cc7d43269" : project === "tauri" ? "5e2856e3209d" : "7e750c1619cb";
  const bad = state.includes("incident");
  const warn = /observe|flaky|unavailable|budget-exhausted|outside-allowed|symlink|stale/.test(state);
  const active = /detection|scan|browser|api|cli|impact|regression|rescan|recovery|run-now|workspace|candidate|confirmation|soak/.test(state);
  const tone: Tone = bad ? "bad" : warn ? "warn" : active ? "active" : "good";
  const current = state.includes("observe-only") ? "OBSERVE_ONLY" : state.includes("unavailable") ? "NEEDS_SETUP" : state.includes("detection") || state.includes("ownership") ? "NEEDS_RUNTIME_APPROVAL" : state.includes("symlink") || state.includes("fanout") || state.includes("flaky") ? "SUPPORTED_WITH_LIMITS" : state.includes("runtime") ? "READY_FOR_AUTOMATIC_CHECKS" : "READY_FOR_PASSIVE_MONITORING";
  const base = project === "vite" ? [2790, 29, 325] : project === "tauri" ? [1109, 24, 295] : project === "excalidraw" ? [1271, 6, 353] : [327, 4, 52];
  return { category, project, revision, current, tone, included: base[0], excluded: base[1], unsupported: base[2], selected: isEvidence || isOrchestration || isRepair ? 3 : 0, omitted: state.includes("fanout") ? 997 : isEvidence || isOrchestration ? 2 : 0 };
}

const behaviorKeys = ["browserPrimary", "browserSecondary", "httpApi", "cliTest", "processHealth"];
const fileKeys = ["SOURCE", "TEST", "DEPENDENCY_MANIFEST", "DEPENDENCY_LOCK", "GENERATED", "SENSITIVE"];

export function Phase14Capture({ state, t }: { state: Phase14CaptureState; t: T }) {
  const truth = truthFor(state);
  const index = phase14CaptureStates.indexOf(state);
  const progress = Math.round(((index + 1) / phase14CaptureStates.length) * 100);
  return <div className={`phase14-surface phase14-${truth.tone}`} data-phase14-fixture="mellowyak.phase14.screenshots.v1" data-phase14-state={state} data-ready="true">
    <header className="phase14-heading">
      <div><span className="eyebrow">{t("phase14.capture.eyebrow")}</span><h1>{t(`phase14.capture.category.${truth.category}`)}</h1><p>{t("phase14.capture.body")}</p></div>
      <div className={`phase14-verdict ${truth.tone}`} role="status"><span aria-hidden="true" /><small>{t("phase14.capture.compatibilityState")}</small><strong>{t(`phase14.state.${truth.current}`)}</strong><code dir="ltr">{truth.current}</code></div>
    </header>
    <section className="phase14-record panel">
      <div className="section-head"><div><h2>{t("phase14.capture.acceptanceRecord")}</h2><p>{t("phase14.capture.recordBody")}</p></div><span className="phase14-step">{t("phase14.capture.step", { current: index + 1, total: phase14CaptureStates.length })}</span></div>
      <div className="phase14-record-grid"><div><small>{t("phase14.capture.project")}</small><strong>{truth.project}</strong></div><div><small>{t("phase14.capture.revision")}</small><code dir="ltr">{truth.revision}</code></div><div><small>{t("phase14.capture.scenario")}</small><code dir="ltr">{state}</code></div><div><small>{t("phase14.capture.boundary")}</small><strong>{t("phase14.capture.localOnly")}</strong></div></div>
      <div className="phase14-progress" role="progressbar" aria-label={t("phase14.capture.progress")} aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}><span style={{ width: `${progress}%` }} /></div>
    </section>
    <section className="phase14-metrics" aria-label={t("phase14.capture.metrics")}><article><span>{t("phase14.compatibility.included")}</span><strong>{truth.included}</strong></article><article><span>{t("phase14.compatibility.excluded")}</span><strong>{truth.excluded}</strong></article><article><span>{t("phase14.compatibility.unsupported")}</span><strong>{truth.unsupported}</strong></article><article><span>{t("phase14.capture.selectedChecks")}</span><strong>{truth.selected}</strong></article><article><span>{t("phase14.capture.omittedChecks")}</span><strong>{truth.omitted}</strong></article></section>
    <div className="phase14-grid">
      <section className="panel"><div className="section-head"><div><h2>{t("phase14.capture.behaviors")}</h2><p>{t("phase14.capture.behaviorsBody")}</p></div><span className="phase14-badge">{t("phase14.capture.sourceBound")}</span></div><div className="phase14-behaviors">{behaviorKeys.map((key, behaviorIndex) => { const selected = behaviorIndex < Math.max(1, truth.selected); return <article key={key} className={selected ? "selected" : "omitted"}><span aria-hidden="true">{selected ? "✓" : "○"}</span><div><strong>{t(`phase14.capture.behavior.${key}`)}</strong><small>{t(selected ? "phase14.capture.selected" : "phase14.capture.unknown")}</small></div></article>; })}</div></section>
      <section className="panel"><h2>{t("phase14.compatibility.classification")}</h2><p className="muted">{t("phase14.capture.classificationBody")}</p><div className="phase14-classifications">{fileKeys.map((key, fileIndex) => <div key={key}><span>{t(`phase14.classification.${key}`)}</span><strong>{Math.max(1, Math.round((truth.included + truth.excluded) / ((fileIndex + 2) * 7)))}</strong></div>)}</div></section>
    </div>
    <div className="phase14-grid phase14-bottom"><section className="panel"><h2>{t("phase14.capture.knownFacts")}</h2><ul><li>{t("phase14.capture.fact.publicPinned")}</li><li>{t("phase14.capture.fact.noMigration")}</li><li>{t("phase14.capture.fact.noSecrets")}</li></ul></section><section className="panel"><h2>{t("phase14.compatibility.unknowns")}</h2><ul><li>{t("compatibility.unknown.omitted_behaviors")}</li><li>{t("compatibility.unknown.external_service_requirements")}</li></ul></section></div>
  </div>;
}
