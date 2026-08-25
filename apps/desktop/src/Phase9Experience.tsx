import { open } from "@tauri-apps/plugin-dialog";
import { useEffect, useState } from "react";
import {
  exportSupportBundle,
  getActivityPreferences,
  getBackgroundStatus,
  getDesktopStartAtLogin,
  getDiagnostics,
  getNotificationSettings,
  listDisconnectedProjects,
  previewProjectIdentity,
  reconnectProject,
  relocateProject,
  putBackgroundStatus,
  putNotificationSettings,
  setActivityMode,
  setDesktopCloseBehavior,
  setDesktopStartAtLogin,
  updateOnboarding,
  verifyStorageIntegrity,
  type ActivityPreferences,
  type Diagnostics,
  type DisconnectedProject,
  type OnboardingState,
} from "./api";
import type { TranslationKey } from "./i18n";
import { mascotAssets } from "./mascots";
import "./phase9.css";

type Translator = (key: TranslationKey, values?: Record<string, string | number>) => string;

export const phase9CaptureStates = [
  "first-run-welcome",
  "first-run-choose-project-or-demo",
  "first-run-background-and-privacy",
  "first-run-complete",
  "disconnected-projects",
  "reconnect-project",
  "relocate-project",
  "relocate-mismatch",
  "dynamic-tray-monitoring",
  "dynamic-tray-attention",
  "dynamic-tray-project-menu",
  "notification-opened-context",
  "diagnostics",
  "support-bundle",
  "product-self-test",
  "update-check",
  "update-signature-rejected",
  "package-acceptance",
  "battery-saver",
  "technical-preview-readiness",
  "hebrew-first-run",
  "hebrew-disconnected-projects",
  "hebrew-diagnostics",
  "hebrew-notification-context",
] as const;

export type Phase9CaptureState = (typeof phase9CaptureStates)[number];

const syntheticDisconnected: DisconnectedProject = {
  project_id: "synthetic-project",
  project_name: "MellowYak Demo Project",
  state: "DISCONNECTED",
  last_known_safe_path: "<PROJECT>/mellowyak-demo",
  last_source_identity: { head_sha: "8e7a44c9b1f2", worktree_fingerprint: "synthetic-fingerprint" },
  disconnect_time: "2026-08-25T07:00:00Z",
  data_retained: true,
  data_size_bytes: 1482752,
  behavior_count: 3,
  regression_count: 1,
  last_activity: "2026-08-25T07:01:00Z",
  source_modified: false,
};

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KiB`;
  return `${(value / 1024 / 1024).toFixed(1)} MiB`;
}

export function FirstRunExperience({
  state,
  t,
  onAddProject,
  onDemo,
  onComplete,
}: {
  state: OnboardingState;
  t: Translator;
  onAddProject: () => void;
  onDemo: () => void;
  onComplete: (state: OnboardingState) => void;
}) {
  const [step, setStep] = useState(state.current_step);
  const [selectedPath, setSelectedPath] = useState<OnboardingState["selected_path"]>(state.selected_path);
  const [busy, setBusy] = useState(false);
  const [keepRunning, setKeepRunning] = useState(true);
  const [notifications, setNotifications] = useState(true);
  const [startAtLogin, setStartAtLogin] = useState(false);

  useEffect(() => {
    if (step !== "privacy") return;
    void Promise.all([
      getBackgroundStatus(),
      getNotificationSettings(),
      getDesktopStartAtLogin().catch(() => false),
    ]).then(([background, notificationSettings, login]) => {
      setKeepRunning(Boolean(background.keep_running_on_close));
      setNotifications(notificationSettings.native_enabled);
      setStartAtLogin(login);
    }).catch(() => undefined);
  }, [step]);

  const persist = async (next: string, complete = false) => {
    setBusy(true);
    try {
      const updated = await updateOnboarding(next, selectedPath, complete);
      if (complete) onComplete(updated);
      else setStep(next);
    } finally {
      setBusy(false);
    }
  };

  const saveBackground = async () => {
    setBusy(true);
    try {
      await Promise.all([
        setDesktopCloseBehavior(keepRunning).catch(() => undefined),
        putBackgroundStatus({ keep_running_on_close: keepRunning, start_at_login: startAtLogin }),
        putNotificationSettings({ native_enabled: notifications }),
        setDesktopStartAtLogin(startAtLogin).catch(() => startAtLogin),
      ]);
      await persist("complete");
    } finally {
      setBusy(false);
    }
  };

  const finish = async () => {
    setBusy(true);
    try {
      const updated = await updateOnboarding("complete", selectedPath, true);
      onComplete(updated);
      if (selectedPath === "real_project") onAddProject();
      else onDemo();
    } finally {
      setBusy(false);
    }
  };

  return <section className="phase9-flow" aria-labelledby="phase9-onboarding-title">
    <img src={mascotAssets["yak-wave"].src} alt={t("phase9.mascot.guideAlt")} />
    <div className="eyebrow">{t("phase9.preview.eyebrow")}</div>
    <h1 id="phase9-onboarding-title">{t(`phase9.onboarding.${step}.title` as TranslationKey)}</h1>
    <p>{t(`phase9.onboarding.${step}.body` as TranslationKey)}</p>
    {step === "welcome" && <div className="phase9-facts" role="list">
      <span role="listitem">{t("phase9.onboarding.fact.local")}</span>
      <span role="listitem">{t("phase9.onboarding.fact.noAccount")}</span>
      <span role="listitem">{t("phase9.onboarding.fact.noModel")}</span>
    </div>}
    {step === "choice" && <fieldset className="phase9-choice-grid"><legend className="sr-only">{t("phase10.firstRun.choiceLegend")}</legend>
      <label className={selectedPath === "real_project" ? "selected" : ""}><input type="radio" name="first-run-path" value="real_project" checked={selectedPath === "real_project"} onChange={() => setSelectedPath("real_project")} /><span className="choice-indicator" aria-hidden="true" /><span><strong>{t("phase9.onboarding.real.title")}</strong><span>{t("phase9.onboarding.real.body")}</span></span></label>
      <label className={selectedPath === "demo_lab" ? "selected" : ""}><input type="radio" name="first-run-path" value="demo_lab" checked={selectedPath === "demo_lab"} onChange={() => setSelectedPath("demo_lab")} /><span className="choice-indicator" aria-hidden="true" /><span><strong>{t("phase9.onboarding.demo.title")}</strong><span>{t("phase9.onboarding.demo.body")}</span></span></label>
    </fieldset>}
    {step === "privacy" && <div className="phase9-check-list">
      <label className="toggle-row"><span><strong>{t("phase10.firstRun.keepWatching")}</strong><small>{t("phase10.firstRun.keepWatchingBody")}</small></span><input type="checkbox" checked={keepRunning} onChange={(event) => setKeepRunning(event.target.checked)} /></label>
      <label className="toggle-row"><span><strong>{t("phase10.firstRun.notifications")}</strong><small>{t("phase10.firstRun.notificationsBody")}</small></span><input type="checkbox" checked={notifications} onChange={(event) => setNotifications(event.target.checked)} /></label>
      <label className="toggle-row"><span><strong>{t("phase10.firstRun.startAtLogin")}</strong><small>{t("phase10.firstRun.startAtLoginBody")}</small></span><input type="checkbox" checked={startAtLogin} onChange={(event) => setStartAtLogin(event.target.checked)} /></label>
      <details><summary>{t("phase10.firstRun.privacyDetails")}</summary><p>{t("phase10.firstRun.privacyDetailsBody")}</p></details>
    </div>}
    {step === "complete" && <div className="phase9-complete" role="status"><strong>{t(selectedPath === "real_project" ? "phase10.firstRun.completeProject" : "phase10.firstRun.completeDemo")}</strong><span>{t(selectedPath === "real_project" ? "phase10.firstRun.completeProjectBody" : "phase10.firstRun.completeDemoBody")}</span></div>}
    <div className="button-row">
      {step === "welcome" && <button className="primary" disabled={busy} onClick={() => void persist("choice")}>{t("phase9.action.continue")}</button>}
      {step === "choice" && <button className="primary" disabled={busy || !selectedPath} onClick={() => void persist("privacy")}>{t("phase9.action.continue")}</button>}
      {step === "privacy" && <button className="primary" disabled={busy} onClick={() => void saveBackground()}>{t("phase9.action.continue")}</button>}
      {step === "complete" && <button className="primary" disabled={busy} onClick={() => void finish()}>{t(selectedPath === "real_project" ? "phase10.firstRun.openProjectSetup" : "phase10.firstRun.openDemoLab")}</button>}
    </div>
  </section>;
}

export function DisconnectedProjectsManager({ t }: { t: Translator }) {
  const [items, setItems] = useState<DisconnectedProject[]>([]);
  const [message, setMessage] = useState("");
  const reload = () => listDisconnectedProjects().then(setItems).catch((error: unknown) => setMessage(String(error)));
  useEffect(() => { void reload(); }, []);

  const locate = async (item: DisconnectedProject, action: "reconnect" | "relocate") => {
    const selected = await open({ directory: true, multiple: false, title: t("phase9.location.dialog") });
    if (typeof selected !== "string") return;
    try {
      const preview = await previewProjectIdentity(item.project_id, selected);
      if (!preview.matched) {
        setMessage(t("phase9.location.mismatch"));
        return;
      }
      if (action === "reconnect") await reconnectProject(item.project_id, selected);
      else await relocateProject(item.project_id, selected);
      setMessage(t("phase9.location.success"));
      reload();
    } catch (error) {
      setMessage(String(error).includes("PROJECT_IDENTITY_MISMATCH") ? t("phase9.location.mismatch") : String(error));
    }
  };

  return <section className="phase9-page">
    <div className="page-head"><div><div className="eyebrow">{t("phase9.disconnected.eyebrow")}</div><h1>{t("phase9.disconnected.title")}</h1><p>{t("phase9.disconnected.body")}</p></div></div>
    <div className="phase9-filter-row" role="group" aria-label={t("phase9.disconnected.filters")}>
      {["connected", "disconnected", "missing", "paused", "attention"].map((value) => <button key={value}>{t(`phase9.filter.${value}` as TranslationKey)}</button>)}
    </div>
    {message && <p className="phase9-message" role="status">{message}</p>}
    {!items.length ? <section className="panel phase9-empty"><h2>{t("phase9.disconnected.empty.title")}</h2><p>{t("phase9.disconnected.empty.body")}</p></section> : items.map((item) => <article className="panel phase9-project" key={item.project_id}>
      <div className="section-head"><div><h2>{item.project_name}</h2><span className="readiness warn">{t(`phase9.state.${item.state}` as TranslationKey)}</span></div><code dir="ltr">{item.last_known_safe_path}</code></div>
      <dl><div><dt>{t("phase9.disconnected.identity")}</dt><dd dir="ltr">{item.last_source_identity.head_sha?.slice(0, 12) ?? t("common.unknown")}</dd></div><div><dt>{t("phase9.disconnected.retained")}</dt><dd>{item.data_retained ? t("phase9.common.yes") : t("phase9.common.no")}</dd></div><div><dt>{t("phase9.disconnected.size")}</dt><dd>{formatBytes(item.data_size_bytes)}</dd></div><div><dt>{t("phase9.disconnected.behaviors")}</dt><dd>{item.behavior_count}</dd></div><div><dt>{t("phase9.disconnected.regressions")}</dt><dd>{item.regression_count}</dd></div></dl>
      <div className="button-row"><button className="primary" onClick={() => void locate(item, "reconnect")}>{t("phase9.action.reconnect")}</button><button className="secondary" onClick={() => void locate(item, "relocate")}>{t("phase9.action.locate")}</button><button className="secondary">{t("phase9.action.history")}</button><button className="secondary danger">{t("phase9.action.deleteData")}</button></div>
    </article>)}
  </section>;
}

export function DiagnosticsCenter({ t, runSelfTest }: { t: Translator; runSelfTest: () => void }) {
  const [diagnostics, setDiagnostics] = useState<Diagnostics | null>(null);
  const [activity, setActivity] = useState<ActivityPreferences | null>(null);
  const [result, setResult] = useState("");
  useEffect(() => { void Promise.all([getDiagnostics(), getActivityPreferences()]).then(([nextDiagnostics, nextActivity]) => { setDiagnostics(nextDiagnostics); setActivity(nextActivity); }).catch((error: unknown) => setResult(String(error))); }, []);
  const act = async (action: "bundle" | "storage") => {
    const value = action === "bundle" ? await exportSupportBundle() : await verifyStorageIntegrity();
    setResult(JSON.stringify(value, null, 2));
  };
  const changeMode = async (mode: ActivityPreferences["activity_mode"]) => setActivity(await setActivityMode(mode));
  return <section className="phase9-page">
    <div className="page-head"><div><div className="eyebrow">{t("phase9.diagnostics.eyebrow")}</div><h1>{t("phase9.diagnostics.title")}</h1><p>{t("phase9.diagnostics.body")}</p></div></div>
    {!diagnostics ? <section className="panel loading">{t("phase9.diagnostics.loading")}</section> : <>
      <div className="phase9-diagnostic-grid">
        {(["desktop_version", "engine_version", "schema_migration", "local_api_state", "loopback_address", "platform", "architecture", "signing_state", "self_test_last_result"] as const).map((key) => <div className="panel" key={key}><span>{t(`phase9.diagnostics.${key}` as TranslationKey)}</span><strong dir={key === "loopback_address" ? "ltr" : undefined}>{String(diagnostics[key])}</strong></div>)}
      </div>
      <section className="panel"><div className="section-head"><h2>{t("phase9.activity.title")}</h2><strong>{activity ? t(`phase9.activity.${activity.activity_mode}` as TranslationKey) : t("common.unknown")}</strong></div><p>{t("phase9.activity.body")}</p><div className="button-row"><button onClick={() => void changeMode("normal")}>{t("phase9.activity.normal")}</button><button onClick={() => void changeMode("reduced")}>{t("phase9.activity.reduced")}</button><button onClick={() => void changeMode("battery_saver")}>{t("phase9.activity.battery_saver")}</button></div>{activity?.deferred.length ? <p className="muted">{t("phase9.activity.deferred", { count: activity.deferred.length })}</p> : null}</section>
      <div className="button-row phase9-actions"><button className="primary" onClick={runSelfTest}>{t("phase9.action.selfTest")}</button><button className="secondary" onClick={() => void act("storage")}>{t("phase9.action.storage")}</button><button className="secondary" onClick={() => void act("bundle")}>{t("phase9.action.bundle")}</button><button className="secondary" onClick={() => void navigator.clipboard.writeText(JSON.stringify(diagnostics, null, 2))}>{t("phase9.action.copy")}</button></div>
      {result && <pre className="panel phase9-result" dir="ltr">{result}</pre>}
    </>}
  </section>;
}

function CaptureTray({ t, attention, submenu }: { t: Translator; attention?: boolean; submenu?: boolean }) {
  return <section className="phase9-tray panel"><h2>{t("phase9.tray.title")}</h2><strong className={attention ? "warn" : "good"}>{attention ? t("phase9.tray.attention") : t("phase9.tray.monitoring")}</strong><dl><div><dt>{t("phase9.tray.unread")}</dt><dd>{attention ? 3 : 0}</dd></div><div><dt>{t("phase9.tray.critical")}</dt><dd>{attention ? 1 : 0}</dd></div><div><dt>{t("phase9.tray.active")}</dt><dd>2</dd></div><div><dt>{t("phase9.tray.paused")}</dt><dd>1</dd></div></dl>{submenu && <div className="phase9-tray-menu"><strong>{t("phase9.synthetic.project")}</strong><button>{t("phase9.tray.openProject")}</button><button>{t("phase9.tray.pause")}</button><button>{t("phase9.tray.mute")}</button></div>}</section>;
}

export function Phase9Capture({ state, t }: { state: Phase9CaptureState; t: Translator }) {
  const syntheticOnboarding: OnboardingState = { completed: false, current_step: state.includes("choose") ? "choice" : state.includes("background") ? "privacy" : state.includes("complete") ? "complete" : "welcome", replay_active: false, selected_path: state.includes("complete") ? "demo_lab" : null, completed_at: null, requires_first_run: true, source_modified: false };
  if (state.includes("first-run")) return <FirstRunExperience state={syntheticOnboarding} t={t} onAddProject={() => undefined} onDemo={() => undefined} onComplete={() => undefined} />;
  if (state.includes("disconnected") || state.includes("reconnect") || state.includes("relocate")) return <section className="phase9-page"><div className="page-head"><div><div className="eyebrow">{t("phase9.disconnected.eyebrow")}</div><h1>{state.includes("mismatch") ? t("phase9.location.mismatch") : t("phase9.disconnected.title")}</h1><p>{t("phase9.disconnected.body")}</p></div></div><article className="panel phase9-project"><h2>{t("phase9.synthetic.project")}</h2><code dir="ltr">{syntheticDisconnected.last_known_safe_path}</code><p className={state.includes("mismatch") ? "phase9-message" : "muted"}>{state.includes("mismatch") ? t("phase9.location.mismatch") : t("phase9.disconnected.retained")}</p><div className="button-row"><button className="primary">{t("phase9.action.reconnect")}</button><button className="secondary">{t("phase9.action.locate")}</button></div></article></section>;
  if (state.includes("dynamic-tray")) return <CaptureTray t={t} attention={state.includes("attention")} submenu={state.includes("project-menu")} />;
  const stateKey = `phase9.capture.${state}` as TranslationKey;
  return <section className="phase9-capture panel"><img src={mascotAssets["yak-security-shield"].src} alt={t("phase9.mascot.guideAlt")} /><div className="eyebrow">{t("phase9.preview.eyebrow")}</div><h1>{t(stateKey)}</h1><p>{t(`${stateKey}.body` as TranslationKey)}</p><div className="phase9-check-list"><div><strong>{t("phase9.capture.local")}</strong><span>{t("phase9.capture.local.body")}</span></div><div><strong>{t("phase9.capture.safe")}</strong><span>{t("phase9.capture.safe.body")}</span></div><div><strong>{t("phase9.capture.verified")}</strong><span>{t("phase9.capture.verified.body")}</span></div></div></section>;
}
