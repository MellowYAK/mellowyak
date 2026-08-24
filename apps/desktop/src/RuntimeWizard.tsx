import { open } from "@tauri-apps/plugin-dialog";
import { useEffect, useMemo, useState } from "react";
import {
  createProject,
  createRuntimeProfile,
  createSnapshot,
  detectProject,
  detectProjectRuntimes,
  type ExecutionMode,
  type Project,
  type ProjectDetection,
  type ProjectType,
  type RuntimeCandidate,
  type RuntimeProfileInput,
  type RuntimeType,
  type SourceSnapshot,
} from "./api";
import type { TranslationKey } from "./i18n";
import { mascotAssets } from "./mascots";
import type { Phase7Translator } from "./Phase7Details";
import { runtimeTypeKey } from "./RuntimeScreen";

const projectTypes: ProjectType[] = ["WEB_APP", "API_SERVICE", "DESKTOP_APP", "CLI_TOOL", "MOBILE_APP", "BACKGROUND_WORKER", "LIBRARY", "MIXED_POLYGLOT", "OTHER"];

const projectTypeKeys: Record<ProjectType, TranslationKey> = {
  WEB_APP: "projectType.webApp",
  API_SERVICE: "projectType.apiService",
  DESKTOP_APP: "projectType.desktopApp",
  CLI_TOOL: "projectType.cliTool",
  MOBILE_APP: "projectType.mobileApp",
  BACKGROUND_WORKER: "projectType.backgroundWorker",
  LIBRARY: "projectType.library",
  MIXED_POLYGLOT: "projectType.mixedPolyglot",
  OTHER: "projectType.other",
};

interface ProfileDraft {
  runtimeType: RuntimeType;
  name: string;
  mode: ExecutionMode;
  executable: string;
  argv: string;
  workingDirectory: string;
  ports: string;
  healthUrl: string;
  testCommand: string;
  stopBehavior: string;
  runtimeVersion: string;
  manifests: string;
  environmentNames: string;
}

function inferredProjectType(detection: ProjectDetection | null): ProjectType {
  const facts = [...(detection?.frameworks ?? []), ...(detection?.runtime_hints ?? []), ...(detection?.languages ?? [])].join(" ").toLowerCase();
  if (facts.includes("tauri") || facts.includes("electron")) return "DESKTOP_APP";
  if (facts.includes("react") || facts.includes("vue") || facts.includes("next")) return "WEB_APP";
  if (facts.includes("fastapi") || facts.includes("django") || facts.includes("express")) return "API_SERVICE";
  if ((detection?.languages.length ?? 0) > 2) return "MIXED_POLYGLOT";
  return "OTHER";
}

function normalizeRuntime(value: string): RuntimeType {
  const normalized = value.toLowerCase();
  if (normalized.includes("node") || normalized.includes("typescript") || normalized.includes("javascript")) return "NODE";
  if (normalized.includes("python")) return "PYTHON";
  if (normalized.includes("php")) return "PHP";
  if (normalized.includes("tauri") || normalized.includes("rust")) return "TAURI_RUST";
  if (normalized.includes("ruby")) return "RUBY";
  if (normalized.includes("java")) return "JAVA";
  return "GENERIC";
}

function inferredCandidates(detection: ProjectDetection | null): RuntimeCandidate[] {
  const values = [...(detection?.runtime_hints ?? []), ...(detection?.languages ?? [])];
  const types = [...new Set(values.map(normalizeRuntime))];
  return (types.length ? types : ["GENERIC"]).map((runtime_type) => ({ runtime_type, detected: true }));
}

function emptyProfile(runtimeType: RuntimeType, t: Phase7Translator): ProfileDraft {
  return { runtimeType, name: t(runtimeTypeKey(runtimeType)), mode: "MANAGED", executable: "", argv: "", workingDirectory: ".", ports: "", healthUrl: "", testCommand: "", stopBehavior: "", runtimeVersion: "", manifests: "", environmentNames: "" };
}

function lines(value: string): string[] { return value.split("\n").map((item) => item.trim()).filter(Boolean); }

export function RuntimeWizard({ existingProject = null, t, onCancel, onComplete, onError }: {
  existingProject?: Project | null;
  t: Phase7Translator;
  onCancel: () => void;
  onComplete: (project: Project) => void;
  onError: (code: string) => void;
}) {
  const [step, setStep] = useState(existingProject ? 2 : 1);
  const [busy, setBusy] = useState(false);
  const [detection, setDetection] = useState<ProjectDetection | null>(null);
  const [createdProject, setCreatedProject] = useState<Project | null>(existingProject);
  const [displayName, setDisplayName] = useState(existingProject?.display_name ?? "");
  const [projectType, setProjectType] = useState<ProjectType>(existingProject?.project_type ?? "OTHER");
  const [candidates, setCandidates] = useState<RuntimeCandidate[]>([]);
  const [selectedRuntimes, setSelectedRuntimes] = useState<RuntimeType[]>([]);
  const [primaryRuntime, setPrimaryRuntime] = useState<RuntimeType | null>(null);
  const [profiles, setProfiles] = useState<Record<string, ProfileDraft>>({});
  const [selectedTests, setSelectedTests] = useState<string[]>([]);
  const [monitoring, setMonitoring] = useState<"passive" | "paused">(existingProject?.monitoring_mode ?? "passive");
  const [observation, setObservation] = useState<"LIGHT" | "DEEP">(existingProject?.observation_level ?? "LIGHT");
  const [retention, setRetention] = useState(existingProject?.snapshot_retention_days ?? 30);
  const [storageGiB, setStorageGiB] = useState(Math.round((existingProject?.snapshot_soft_cap_bytes ?? 5 * 1024 ** 3) / 1024 ** 3));
  const [snapshot, setSnapshot] = useState<SourceSnapshot | null>(null);
  const [limitations, setLimitations] = useState<string[]>([]);

  useEffect(() => {
    if (!detection || projectType !== "OTHER") return;
    setProjectType(inferredProjectType(detection));
  }, [detection, projectType]);

  const availableTests = useMemo(() => detection?.tests ?? [], [detection]);
  const canContinue = step === 1 ? Boolean(detection && displayName.trim()) : step === 3 ? selectedRuntimes.length > 0 && Boolean(primaryRuntime) : step === 4 ? selectedRuntimes.every((value) => profiles[value]?.name.trim()) : true;

  const chooseFolder = async () => {
    setBusy(true); onError("");
    try {
      const chosen = await open({ directory: true, multiple: false, title: t("wizard.chooseFolderDialog") });
      const path = Array.isArray(chosen) ? chosen[0] : chosen;
      if (!path) return;
      const result = await detectProject(path);
      setDetection(result); setDisplayName(result.suggested_name); setProjectType(inferredProjectType(result));
    } catch (reason) { onError(reason instanceof Error ? reason.message : "PROJECT_DETECTION_FAILED"); }
    finally { setBusy(false); }
  };

  const loadRuntimes = async () => {
    setBusy(true); onError("");
    try {
      const detected = createdProject ? (await detectProjectRuntimes(createdProject.id)).candidates : inferredCandidates(detection);
      setCandidates(detected);
      const types = [...new Set(detected.map((item) => normalizeRuntime(String(item.runtime_type))))];
      setSelectedRuntimes((current) => current.length ? current : types);
      setPrimaryRuntime((current) => current ?? types[0] ?? "GENERIC");
      setProfiles((current) => {
        const next = { ...current };
        types.forEach((runtimeType) => { if (!next[runtimeType]) next[runtimeType] = emptyProfile(runtimeType, t); });
        return next;
      });
    } catch (reason) { onError(reason instanceof Error ? reason.message : "RUNTIME_DETECTION_FAILED"); }
    finally { setBusy(false); }
  };

  useEffect(() => { if (step === 3 && !candidates.length) void loadRuntimes(); }, [step]);

  const toggleRuntime = (runtimeType: RuntimeType) => {
    setSelectedRuntimes((current) => {
      if (current.includes(runtimeType)) {
        const next = current.filter((item) => item !== runtimeType);
        if (primaryRuntime === runtimeType) setPrimaryRuntime(next[0] ?? null);
        return next;
      }
      setProfiles((drafts) => ({ ...drafts, [runtimeType]: drafts[runtimeType] ?? emptyProfile(runtimeType, t) }));
      if (!primaryRuntime) setPrimaryRuntime(runtimeType);
      return [...current, runtimeType];
    });
  };

  const updateProfile = (runtimeType: RuntimeType, value: Partial<ProfileDraft>) => setProfiles((current) => ({ ...current, [runtimeType]: { ...current[runtimeType], ...value } }));

  const provision = async () => {
    setBusy(true); onError("");
    try {
      let project = createdProject;
      if (!project) {
        if (!detection) throw new Error("PROJECT_DETECTION_REQUIRED");
        project = await createProject(detection.selected_path, displayName, monitoring, { project_type: projectType, observation_level: observation, snapshot_retention_days: retention, snapshot_soft_cap_bytes: storageGiB * 1024 ** 3 });
        setCreatedProject(project);
      }
      const failed: string[] = [];
      for (const runtimeType of selectedRuntimes) {
        const draft = profiles[runtimeType];
        const input: RuntimeProfileInput = {
          display_name: draft.name,
          runtime_type: draft.runtimeType,
          primary: runtimeType === primaryRuntime,
          execution_mode: draft.mode,
          executable_reference: draft.executable || null,
          argv: lines(draft.argv),
          relative_working_directory: draft.workingDirectory || ".",
          runtime_version: draft.runtimeVersion || null,
          health_definition: {
            ...(draft.healthUrl ? { url: draft.healthUrl } : {}),
            ...(draft.stopBehavior ? { stop_behavior: draft.stopBehavior } : {}),
            ...(draft.manifests ? { dependency_manifests: draft.manifests.split(",").map((item) => item.trim()).filter(Boolean) } : {}),
          },
          expected_ports: draft.ports.split(",").map((item) => Number(item.trim())).filter((item) => Number.isInteger(item) && item > 0 && item < 65536),
          test_definitions: [
            ...selectedTests.map((name) => ({ name, approved: true })),
            ...(draft.testCommand ? [{ executable: draft.testCommand, approved: true }] : []),
          ],
          environment_schema: draft.environmentNames.split(",").map((item) => item.trim()).filter(Boolean),
          network_policy: "LOOPBACK_ONLY",
          limitations: draft.executable ? [] : ["EXECUTABLE_NOT_RESOLVED"],
          approved: true,
        };
        try { await createRuntimeProfile(project.id, input); } catch { failed.push(runtimeType); }
      }
      const saved = await createSnapshot(project.id, "INITIAL_SAVE_POINT");
      setSnapshot(saved);
      setLimitations([
        ...(failed.length ? ["RUNTIME_UNAVAILABLE"] : []),
        ...(saved.unsupported_count ? ["UNSUPPORTED_FILES"] : []),
        ...(selectedRuntimes.length ? [] : ["RUNTIME_SETUP_INCOMPLETE"]),
      ]);
      setStep(7);
    } catch (reason) { onError(reason instanceof Error ? reason.message : "RUNTIME_SETUP_FAILED"); }
    finally { setBusy(false); }
  };

  const next = () => {
    if (step === 6) { void provision(); return; }
    if (step === 7) { setStep(8); return; }
    setStep((value) => Math.min(8, value + 1));
  };

  const stepKey = `wizard.step.${step}` as TranslationKey;
  return <div className="runtime-wizard">
    <section className="page-head wizard-head"><div><div className="eyebrow">{t("wizard.eyebrow")}</div><h1>{t("wizard.title")}</h1><p>{t("wizard.subtitle")}</p></div><button className="secondary" onClick={onCancel}>{t("common.cancel")}</button></section>
    <div className="wizard-progress" role="progressbar" aria-label={t("wizard.progress")} aria-valuemin={1} aria-valuemax={8} aria-valuenow={step}><span style={{ inlineSize: `${step * 12.5}%` }} /></div>
    <div className="wizard-layout">
      <aside className="wizard-guide"><img src={mascotAssets[step === 8 ? "yak-success-check" : step === 7 ? "yak-working-laptop" : "yak-teaching-map"].src} alt={t("wizard.mascotAlt")} /><strong>{t("wizard.stepCount", { step, total: 8 })}</strong><span>{t(stepKey)}</span><p>{t(`wizard.guide.${step}` as TranslationKey)}</p></aside>
      <section className="panel wizard-card">
        {step === 1 && <div className="wizard-step"><h2>{t("wizard.project.title")}</h2><p className="muted">{t("wizard.project.body")}</p>{!detection ? <button className="primary" disabled={busy} onClick={() => void chooseFolder()}>{busy ? t("add.inspecting") : t("wizard.project.choose")}</button> : <><label className="field"><span>{t("add.projectName")}</span><input value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label><div className="status-row"><span>{t("wizard.project.canonicalRoot")}</span><code dir="ltr">{detection.repository_path}</code></div><div className="status-row"><span>{t("project.git")}</span><strong>{detection.git.available ? t("wizard.project.gitDetected") : t("wizard.project.gitOptional")}</strong></div><p className="privacy-note"><strong>{t("add.sourceLocalTitle")}</strong><span>{t("wizard.project.localBody")}</span></p><button className="secondary" onClick={() => setDetection(null)}>{t("add.chooseAnother")}</button></>}</div>}
        {step === 2 && <div className="wizard-step"><h2>{t("wizard.projectType.title")}</h2><p className="muted">{t("wizard.projectType.body")}</p><div className="choice-grid">{projectTypes.map((value) => <button key={value} className={projectType === value ? "selected" : ""} onClick={() => setProjectType(value)}><strong>{t(projectTypeKeys[value])}</strong>{value === inferredProjectType(detection) && <small>{t("wizard.suggested")}</small>}</button>)}</div></div>}
        {step === 3 && <div className="wizard-step"><div className="section-head"><div><h2>{t("wizard.runtimes.title")}</h2><p className="muted">{t("wizard.runtimes.body")}</p></div><button className="secondary" disabled={busy} onClick={() => void loadRuntimes()}>{busy ? t("runtimeProfile.detecting") : t("runtimeProfile.detect")}</button></div><div className="runtime-choice-list">{candidates.map((candidate, index) => { const type = normalizeRuntime(String(candidate.runtime_type)); const checked = selectedRuntimes.includes(type); return <article key={`${type}-${index}`} className={checked ? "selected" : ""}><label><input type="checkbox" checked={checked} onChange={() => toggleRuntime(type)} /><span><strong>{t(runtimeTypeKey(type))}</strong><small>{candidate.runtime_version || t("common.versionUnknown")}</small></span></label>{checked && <label><span>{t("wizard.runtimes.primary")}</span><input type="radio" name="primary-runtime" checked={primaryRuntime === type} onChange={() => setPrimaryRuntime(type)} /></label>}</article>; })}</div><p className="privacy-note">{t("wizard.runtimes.noAssumption")}</p></div>}
        {step === 4 && <div className="wizard-step"><h2>{t("wizard.howItRuns.title")}</h2><p className="muted">{t("wizard.howItRuns.body")}</p><div className="wizard-profile-stack">{selectedRuntimes.map((runtimeType) => { const draft = profiles[runtimeType] ?? emptyProfile(runtimeType, t); return <details key={runtimeType} open><summary>{t(runtimeTypeKey(runtimeType))}</summary><div className="runtime-profile-form"><label className="field"><span>{t("runtimeProfile.name")}</span><input value={draft.name} onChange={(event) => updateProfile(runtimeType, { name: event.target.value })} /></label><label className="field"><span>{t("runtimeProfile.mode")}</span><select value={draft.mode} onChange={(event) => updateProfile(runtimeType, { mode: event.target.value as ExecutionMode })}><option value="MANAGED">{t("runtimeProfile.mode.managed")}</option><option value="EXTERNAL">{t("runtimeProfile.mode.external")}</option><option value="MANUAL">{t("runtimeProfile.mode.manual")}</option></select></label><label className="field"><span>{t("runtimeProfile.executable")}</span><input dir="ltr" value={draft.executable} onChange={(event) => updateProfile(runtimeType, { executable: event.target.value })} /></label><label className="field"><span>{t("runtimeProfile.arguments")}</span><textarea dir="ltr" value={draft.argv} placeholder={t("runtimeProfile.argumentsHint")} onChange={(event) => updateProfile(runtimeType, { argv: event.target.value })} /></label><label className="field"><span>{t("runtimeProfile.workingDirectory")}</span><input dir="ltr" value={draft.workingDirectory} onChange={(event) => updateProfile(runtimeType, { workingDirectory: event.target.value })} /></label><label className="field"><span>{t("runtimeProfile.ports")}</span><input dir="ltr" value={draft.ports} onChange={(event) => updateProfile(runtimeType, { ports: event.target.value })} /></label><label className="field"><span>{t("runtimeProfile.healthUrl")}</span><input dir="ltr" value={draft.healthUrl} onChange={(event) => updateProfile(runtimeType, { healthUrl: event.target.value })} /></label><label className="field"><span>{t("wizard.howItRuns.testCommand")}</span><input dir="ltr" value={draft.testCommand} onChange={(event) => updateProfile(runtimeType, { testCommand: event.target.value })} /></label><label className="field"><span>{t("wizard.howItRuns.stopBehavior")}</span><input value={draft.stopBehavior} onChange={(event) => updateProfile(runtimeType, { stopBehavior: event.target.value })} /></label><label className="field"><span>{t("wizard.howItRuns.runtimeVersion")}</span><input dir="ltr" value={draft.runtimeVersion} onChange={(event) => updateProfile(runtimeType, { runtimeVersion: event.target.value })} /></label><label className="field"><span>{t("wizard.howItRuns.manifests")}</span><input dir="ltr" value={draft.manifests} onChange={(event) => updateProfile(runtimeType, { manifests: event.target.value })} /></label><label className="field"><span>{t("wizard.howItRuns.environmentNames")}</span><input dir="ltr" value={draft.environmentNames} onChange={(event) => updateProfile(runtimeType, { environmentNames: event.target.value })} /></label><div className="runtime-form-wide privacy-note"><strong>{t("runtimeProfile.noShell")}</strong><span>{t("wizard.howItRuns.localNetwork")}</span></div></div></details>; })}</div></div>}
        {step === 5 && <div className="wizard-step"><h2>{t("wizard.tests.title")}</h2><p className="muted">{t("wizard.tests.body")}</p>{availableTests.length ? <div className="test-choice-list">{availableTests.map((test) => <label key={test}><input type="checkbox" checked={selectedTests.includes(test)} onChange={() => setSelectedTests((current) => current.includes(test) ? current.filter((item) => item !== test) : [...current, test])} /><span><strong>{test}</strong><small>{selectedTests.includes(test) ? t("wizard.tests.willRun") : t("wizard.tests.notEnabled")}</small></span></label>)}</div> : <div className="empty-state"><strong>{t("wizard.tests.none")}</strong><p className="muted">{t("wizard.tests.noneBody")}</p></div>}<p className="privacy-note">{t("wizard.tests.confirmation")}</p></div>}
        {step === 6 && <div className="wizard-step"><h2>{t("wizard.monitoring.title")}</h2><p className="muted">{t("wizard.monitoring.body")}</p><div className="monitoring-options"><label className="field"><span>{t("wizard.monitoring.mode")}</span><select value={monitoring} onChange={(event) => setMonitoring(event.target.value as "passive" | "paused")}><option value="passive">{t("wizard.monitoring.passive")}</option><option value="paused">{t("common.paused")}</option></select></label><label className="field"><span>{t("wizard.monitoring.observation")}</span><select value={observation} onChange={(event) => setObservation(event.target.value as "LIGHT" | "DEEP")}><option value="LIGHT">{t("wizard.monitoring.light")}</option><option value="DEEP">{t("wizard.monitoring.deep")}</option></select></label><label className="field"><span>{t("wizard.monitoring.retention")}</span><input type="number" min={1} max={3650} value={retention} onChange={(event) => setRetention(Number(event.target.value))} /></label><label className="field"><span>{t("wizard.monitoring.storage")}</span><input type="number" min={1} max={1024} value={storageGiB} onChange={(event) => setStorageGiB(Number(event.target.value))} /></label></div><div className="privacy-note"><strong>{t("wizard.monitoring.privacy")}</strong><span>{t("wizard.monitoring.privacyBody")}</span></div></div>}
        {step === 7 && snapshot && <div className="wizard-step"><h2>{t("wizard.savePoint.title")}</h2><p className="muted">{t("wizard.savePoint.body")}</p><div className="snapshot-metrics"><div><span>{t("snapshot.included")}</span><strong>{snapshot.included_count}</strong></div><div><span>{t("snapshot.excluded")}</span><strong>{snapshot.excluded_count}</strong></div><div><span>{t("snapshot.sensitive")}</span><strong>{snapshot.sensitive_count}</strong></div><div><span>{t("snapshot.unsupported")}</span><strong>{snapshot.unsupported_count}</strong></div><div><span>{t("memory.physicalAdded")}</span><strong>{snapshot.physical_bytes_added}</strong></div><div><span>{t("memory.reused")}</span><strong>{snapshot.reused_bytes}</strong></div></div><div className="status-row"><span>{t("snapshot.gitAnchor")}</span><strong>{typeof snapshot.git_anchor.head_sha === "string" ? snapshot.git_anchor.head_sha.slice(0, 12) : t("memory.gitNotRequired")}</strong></div><div className="status-row"><span>{t("wizard.savePoint.identity")}</span><code dir="ltr">{snapshot.id}</code></div></div>}
        {step === 8 && createdProject && <div className="wizard-step wizard-done"><img src={mascotAssets["yak-success-check"].src} alt={t("wizard.mascotAlt")} /><h2>{limitations.length ? t("wizard.done.limitsTitle") : t("wizard.done.readyTitle")}</h2><p>{limitations.length ? t("wizard.done.limitsBody") : t("wizard.done.readyBody")}</p><div className="done-summary"><div><span>{t("wizard.done.monitoring")}</span><strong>{monitoring === "passive" ? t("wizard.monitoring.passive") : t("common.paused")}</strong></div><div><span>{t("wizard.done.runtime")}</span><strong>{selectedRuntimes.length ? t("wizard.done.configuredCount", { count: selectedRuntimes.length }) : t("runtimeProfile.setupIncomplete")}</strong></div><div><span>{t("wizard.done.probes")}</span><strong>{t("wizard.done.probesAvailable")}</strong></div><div><span>{t("wizard.done.automatic")}</span><strong>{selectedTests.length ? t("wizard.done.configuredCount", { count: selectedTests.length }) : t("wizard.done.notConfigured")}</strong></div></div>{limitations.length > 0 && <ul className="boundary-list">{limitations.map((_, index) => <li key={index}>{t("wizard.done.limitItem")}</li>)}</ul>}<button className="primary" onClick={() => onComplete(createdProject)}>{t("wizard.done.openProject")}</button></div>}
        {step < 8 && <footer className="wizard-actions"><button className="secondary" disabled={busy || step === (existingProject ? 2 : 1)} onClick={() => setStep((value) => Math.max(existingProject ? 2 : 1, value - 1))}>{t("common.back")}</button><button className="primary" disabled={busy || !canContinue || (step === 7 && !snapshot)} onClick={next}>{busy ? t("common.working") : step === 6 ? t("wizard.createSavePoint") : t("common.continue")}</button></footer>}
      </section>
    </div>
  </div>;
}
