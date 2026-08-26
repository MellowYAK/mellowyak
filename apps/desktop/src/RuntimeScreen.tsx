import { useCallback, useEffect, useMemo, useState } from "react";
import {
  createRuntimeProfile,
  detectProjectRuntimes,
  listRuntimeInstances,
  listRuntimeProfiles,
  startRuntimeProfile,
  stopRuntimeProfile,
  validateRuntimeProfile,
  type ExecutionMode,
  type Project,
  type RuntimeCandidate,
  type RuntimeInstance,
  type RuntimeProfile,
  type RuntimeType,
} from "./api";
import type { TranslationKey } from "./i18n";
import { ProbePanel } from "./ProbePanel";
import { ReadyWithLimitsDetails, type Phase7Translator } from "./Phase7Details";
import { useLocalEvents } from "./useLocalEvents";

const runtimeTypes: RuntimeType[] = ["NODE", "PYTHON", "PHP", "TAURI_RUST", "RUBY", "JAVA", "GENERIC"];
const executionModes: ExecutionMode[] = ["MANAGED", "EXTERNAL", "MANUAL"];

export function runtimeTypeKey(value: string): TranslationKey {
  const keys: Record<string, TranslationKey> = {
    NODE: "runtimeProfile.type.node",
    PYTHON: "runtimeProfile.type.python",
    PHP: "runtimeProfile.type.php",
    TAURI_RUST: "runtimeProfile.type.tauriRust",
    RUBY: "runtimeProfile.type.ruby",
    JAVA: "runtimeProfile.type.java",
    GENERIC: "runtimeProfile.type.generic",
  };
  return keys[value] ?? "runtimeProfile.type.generic";
}

function executionModeKey(value: string): TranslationKey {
  const keys: Record<string, TranslationKey> = {
    MANAGED: "runtimeProfile.mode.managed",
    EXTERNAL: "runtimeProfile.mode.external",
    MANUAL: "runtimeProfile.mode.manual",
  };
  return keys[value] ?? "runtimeProfile.mode.manual";
}

function instanceStatusKey(value: string): TranslationKey {
  const keys: Record<string, TranslationKey> = {
    STARTING: "runtimeProfile.state.starting",
    RUNNING: "runtimeProfile.state.running",
    STOPPING: "runtimeProfile.state.stopping",
    STOPPED: "runtimeProfile.state.stopped",
    FAILED: "runtimeProfile.state.failed",
    EXTERNAL: "runtimeProfile.state.external",
    MANUAL: "runtimeProfile.state.manual",
  };
  return keys[value] ?? "runtimeProfile.state.unknown";
}

function candidateLabel(candidate: RuntimeCandidate, t: Phase7Translator): string {
  return candidate.display_name || t(runtimeTypeKey(String(candidate.runtime_type)));
}

function lastInstance(profile: RuntimeProfile, instances: RuntimeInstance[]): RuntimeInstance | null {
  return instances.find((item) => item.profile_id === profile.id) ?? null;
}

export function RuntimeScreen({ project, t, onError, completeSetup }: {
  project: Project;
  t: Phase7Translator;
  onError: (code: string) => void;
  completeSetup: () => void;
}) {
  const [profiles, setProfiles] = useState<RuntimeProfile[]>([]);
  const [instances, setInstances] = useState<RuntimeInstance[]>([]);
  const [candidates, setCandidates] = useState<RuntimeCandidate[]>([]);
  const [detecting, setDetecting] = useState(false);
  const [creating, setCreating] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [runtimeType, setRuntimeType] = useState<RuntimeType>("NODE");
  const [mode, setMode] = useState<ExecutionMode>("MANAGED");
  const [executable, setExecutable] = useState("");
  const [argumentsText, setArgumentsText] = useState("");
  const [workingDirectory, setWorkingDirectory] = useState(".");
  const [portsText, setPortsText] = useState("");
  const [healthUrl, setHealthUrl] = useState("");
  const [primary, setPrimary] = useState(false);

  const refresh = useCallback(async () => {
    const [nextProfiles, nextInstances] = await Promise.all([
      listRuntimeProfiles(project.id),
      listRuntimeInstances(project.id),
    ]);
    setProfiles(nextProfiles);
    setInstances([...nextInstances].sort((a, b) => b.started_at.localeCompare(a.started_at)));
  }, [project.id]);

  useEffect(() => { void refresh().catch((reason) => onError(reason instanceof Error ? reason.message : "RUNTIME_LOAD_FAILED")); }, [refresh, onError]);
  useLocalEvents(project.id, (event) => { if (event.type.startsWith("runtime_")) void refresh().catch(() => undefined); });

  const limitations = useMemo(() => {
    const values: string[] = [];
    if (!profiles.length) values.push("RUNTIME_SETUP_INCOMPLETE");
    if (profiles.some((profile) => profile.status === "UNAVAILABLE" || profile.current_version.limitations.length)) values.push("RUNTIME_UNAVAILABLE");
    if (project.observation_level === "DEEP" && profiles.some((profile) => profile.current_version.execution_mode !== "MANAGED")) values.push("DEEP_OBSERVATION_UNAVAILABLE");
    return values;
  }, [profiles, project.observation_level]);

  const run = async (id: string, operation: () => Promise<void>) => {
    setBusyId(id); onError("");
    try { await operation(); await refresh(); }
    catch (reason) { onError(reason instanceof Error ? reason.message : "RUNTIME_OPERATION_FAILED"); }
    finally { setBusyId(null); }
  };

  const detect = () => void run("detect", async () => {
    setDetecting(true);
    try { setCandidates((await detectProjectRuntimes(project.id)).candidates); }
    finally { setDetecting(false); }
  });

  const create = () => void run("create", async () => {
    await createRuntimeProfile(project.id, {
      display_name: name,
      runtime_type: runtimeType,
      primary,
      execution_mode: mode,
      executable_reference: executable || null,
      argv: argumentsText.split("\n").map((item) => item.trim()).filter(Boolean),
      relative_working_directory: workingDirectory || ".",
      health_definition: healthUrl ? { url: healthUrl } : {},
      expected_ports: portsText.split(",").map((item) => Number(item.trim())).filter((item) => Number.isInteger(item) && item > 0 && item < 65536),
      network_policy: "LOOPBACK_ONLY",
      approved: true,
    });
    setCreating(false); setName(""); setExecutable(""); setArgumentsText(""); setPortsText(""); setHealthUrl("");
  });

  const approveDetected = (candidate: RuntimeCandidate, index: number) => void run(`detected-${index}`, async () => {
    await createRuntimeProfile(project.id, {
      display_name: candidate.display_name || candidateLabel(candidate, t),
      runtime_type: String(candidate.runtime_type),
      primary: profiles.length === 0,
      execution_mode: candidate.execution_mode || "MANAGED",
      executable_reference: candidate.executable_reference || null,
      argv: candidate.argv || [],
      relative_working_directory: candidate.relative_working_directory || ".",
      runtime_version: candidate.runtime_version || null,
      dependency_fingerprint: candidate.dependency_fingerprint || null,
      health_definition: candidate.health_definition || {},
      expected_ports: candidate.expected_ports || [],
      test_definitions: candidate.test_definitions || [],
      environment_schema: candidate.environment_schema || [],
      network_policy: candidate.network_policy || "LOOPBACK_ONLY",
      limitations: candidate.limitations || [],
      approved: true,
    });
  });

  return <div className="phase7-page">
    <section className="page-head"><div><div className="eyebrow">{t("runtimeProfile.eyebrow")}</div><h1>{t("runtimeProfile.title")}</h1><p>{t("runtimeProfile.subtitle")}</p></div><ReadyWithLimitsDetails limitations={limitations} t={t} /></section>
    {!profiles.length && <section className="analysis-banner setup-incomplete"><div><strong>{t("runtimeProfile.setupIncomplete")}</strong><span>{t("runtimeProfile.setupIncompleteBody")}</span></div><button className="primary" onClick={completeSetup}>{t("runtimeProfile.completeSetup")}</button></section>}
    <section className="panel runtime-detection-panel">
      <div className="section-head"><div><h2>{t("runtimeProfile.detected")}</h2><p className="muted">{t("runtimeProfile.detectedBody")}</p></div><button className="secondary" disabled={busyId === "detect"} onClick={detect}>{detecting ? t("runtimeProfile.detecting") : t("runtimeProfile.detect")}</button></div>
      {candidates.length ? <div className="runtime-candidates">{candidates.map((candidate, index) => <article key={`${candidate.runtime_type}-${index}`}><strong>{candidateLabel(candidate, t)}</strong><span>{candidate.runtime_version || t("common.versionUnknown")}</span><small>{candidate.dependency_manifests?.length ? t("runtimeProfile.manifests", { count: candidate.dependency_manifests.length }) : t("runtimeProfile.noManifest")}</small>{candidate.detected && <button className="secondary" disabled={busyId === `detected-${index}`} onClick={() => approveDetected(candidate, index)}>{t("runtimeProfile.approveDetected")}</button>}</article>)}</div> : <p className="muted">{t("runtimeProfile.detectPrompt")}</p>}
    </section>
    <section className="panel">
      <div className="section-head"><div><h2>{t("runtimeProfile.profiles")}</h2><p className="muted">{t("runtimeProfile.profilesBody")}</p></div><button className="primary" onClick={() => setCreating((value) => !value)}>{creating ? t("common.cancel") : t("runtimeProfile.addProfile")}</button></div>
      {creating && <div className="runtime-profile-form">
        <label className="field"><span>{t("runtimeProfile.name")}</span><input value={name} onChange={(event) => setName(event.target.value)} /></label>
        <label className="field"><span>{t("runtimeProfile.type")}</span><select value={runtimeType} onChange={(event) => setRuntimeType(event.target.value as RuntimeType)}>{runtimeTypes.map((value) => <option value={value} key={value}>{t(runtimeTypeKey(value))}</option>)}</select></label>
        <label className="field"><span>{t("runtimeProfile.mode")}</span><select value={mode} onChange={(event) => setMode(event.target.value as ExecutionMode)}>{executionModes.map((value) => <option value={value} key={value}>{t(executionModeKey(value))}</option>)}</select></label>
        <label className="field"><span>{t("runtimeProfile.workingDirectory")}</span><input dir="ltr" value={workingDirectory} onChange={(event) => setWorkingDirectory(event.target.value)} /></label>
        <label className="field"><span>{t("runtimeProfile.executable")}</span><input dir="ltr" value={executable} onChange={(event) => setExecutable(event.target.value)} /></label>
        <label className="field"><span>{t("runtimeProfile.arguments")}</span><textarea dir="ltr" value={argumentsText} placeholder={t("runtimeProfile.argumentsHint")} onChange={(event) => setArgumentsText(event.target.value)} /></label>
        <label className="field"><span>{t("runtimeProfile.ports")}</span><input dir="ltr" value={portsText} onChange={(event) => setPortsText(event.target.value)} /></label>
        <label className="field"><span>{t("runtimeProfile.healthUrl")}</span><input dir="ltr" value={healthUrl} onChange={(event) => setHealthUrl(event.target.value)} /></label>
        <label className="toggle-row"><span>{t("runtimeProfile.primary")}</span><input type="checkbox" checked={primary} onChange={(event) => setPrimary(event.target.checked)} /></label>
        <div className="runtime-form-wide privacy-note"><strong>{t("runtimeProfile.noShell")}</strong><span>{t("runtimeProfile.noShellBody")}</span></div>
        <div className="runtime-form-wide button-row"><button className="primary" disabled={busyId === "create" || !name.trim()} onClick={create}>{busyId === "create" ? t("common.working") : t("runtimeProfile.save")}</button></div>
      </div>}
      {profiles.length ? <div className="runtime-profile-list">{profiles.map((profile) => {
        const instance = lastInstance(profile, instances);
        const running = instance?.status === "RUNNING" || instance?.status === "STARTING";
        const version = profile.current_version;
        return <article className="runtime-profile-card" key={profile.id}>
          <div className="section-head"><div><h3>{profile.display_name}</h3><div className="tags"><span>{t(runtimeTypeKey(version.runtime_type))}</span><span>{t(executionModeKey(version.execution_mode))}</span>{profile.primary && <span>{t("runtimeProfile.primary")}</span>}</div></div><span className={`readiness ${running ? "good" : profile.status === "UNAVAILABLE" ? "warn" : "neutral"}`}>{instance ? t(instanceStatusKey(instance.status)) : t("runtimeProfile.state.notStarted")}</span></div>
          <div className="runtime-card-grid">
            <div><span>{t("runtimeProfile.health")}</span><strong>{version.health_definition.url ? t("runtimeProfile.healthConfigured") : t("runtimeProfile.healthNotConfigured")}</strong></div>
            <div><span>{t("runtimeProfile.process")}</span><strong>{instance?.process_id ? t("runtimeProfile.processId", { id: instance.process_id }) : t("runtimeProfile.noProcess")}</strong></div>
            <div><span>{t("runtimeProfile.tests")}</span><strong>{t("runtimeProfile.testsCount", { count: version.test_definitions.length })}</strong></div>
            <div><span>{t("runtimeProfile.ports")}</span><strong>{version.expected_ports.length ? version.expected_ports.join(", ") : t("runtimeProfile.noPorts")}</strong></div>
          </div>
          {version.limitations.length > 0 && <div className="runtime-limitations"><strong>{t("runtimeProfile.limitations")}</strong><span>{t("runtimeProfile.limitationsCount", { count: version.limitations.length })}</span></div>}
          <div className="button-row"><button className="secondary" disabled={busyId === profile.id} onClick={() => void run(profile.id, async () => { await validateRuntimeProfile(project.id, profile.id); })}>{t("runtimeProfile.validate")}</button><button className={running ? "secondary danger" : "primary"} disabled={busyId === profile.id} onClick={() => void run(profile.id, async () => { if (running) await stopRuntimeProfile(project.id, profile.id); else await startRuntimeProfile(project.id, profile.id); })}>{running ? t("runtimeProfile.stop") : t("runtimeProfile.start")}</button></div>
          <details><summary>{t("common.technicalDetails")}</summary><pre dir="ltr">{JSON.stringify({ executable_reference: version.executable_reference, argv: version.argv, relative_working_directory: version.relative_working_directory, network_policy: version.network_policy, observation: instance?.observation ?? {} }, null, 2)}</pre></details>
        </article>;
      })}</div> : !creating && <div className="empty-state"><strong>{t("runtimeProfile.empty")}</strong><p className="muted">{t("runtimeProfile.emptyBody")}</p></div>}
    </section>
    <ProbePanel projectId={project.id} profiles={profiles} t={t} onError={onError} />
  </div>;
}
