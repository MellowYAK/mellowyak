import { open } from "@tauri-apps/plugin-dialog";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  cancelProjectScan,
  createProject,
  detectProject,
  getImpactSummary,
  getProject,
  listProjects,
  loadSetupSnapshot,
  openDataFolder,
  openProjectFolder,
  setProjectMonitoring,
  startProjectScan,
  type ImpactSummary,
  type Project,
  type ProjectDetection,
  type SetupSnapshot,
} from "./api";

type Screen = "home" | "add" | "project";
type Tone = "good" | "warn" | "neutral";

function StatusRow({ label, value, tone = "neutral" }: { label: string; value: string; tone?: Tone }) {
  return <div className="status-row"><span>{label}</span><strong className={tone}>{value}</strong></div>;
}

function Tags({ values, empty }: { values: string[]; empty: string }) {
  return values.length
    ? <div className="tags">{values.map((value) => <span key={value}>{value}</span>)}</div>
    : <p className="muted">{empty}</p>;
}

function readiness(project: Project): { label: string; tone: Tone } {
  if (!project.git.available) return { label: "Git unavailable", tone: "warn" };
  if (!project.scan || project.scan.status === "running") return { label: "Scan incomplete", tone: "neutral" };
  if (project.scan.status !== "completed") return { label: "Scan incomplete", tone: "warn" };
  if (project.scan.failed_files || project.scan.unknown_items || project.scan.unsupported_files) {
    return { label: "Ready with limits", tone: "warn" };
  }
  return { label: "Ready", tone: "good" };
}

function Header({ home }: { home: () => void }) {
  return <header className="brand-bar">
    <button className="brand-button" onClick={home} aria-label="MellowYak home"><span className="mark">MY</span></button>
    <div><div className="brand-name">MellowYak</div><div className="tagline">Protect what already works.</div></div>
    <div className="principle">Passive by default. Active when it matters.</div>
  </header>;
}

export function App() {
  const [snapshot, setSnapshot] = useState<SetupSnapshot | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selected, setSelected] = useState<Project | null>(null);
  const [impact, setImpact] = useState<ImpactSummary | null>(null);
  const [detection, setDetection] = useState<ProjectDetection | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [monitoring, setMonitoring] = useState<"passive" | "paused">("passive");
  const [screen, setScreen] = useState<Screen>("home");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const reloadProjects = useCallback(async () => setProjects(await listProjects()), []);

  useEffect(() => {
    let active = true;
    Promise.all([loadSetupSnapshot(), listProjects()])
      .then(([setup, saved]) => { if (active) { setSnapshot(setup); setProjects(saved); } })
      .catch((reason: unknown) => active && setError(reason instanceof Error ? reason.message : "LOCAL_ENGINE_UNAVAILABLE"));
    return () => { active = false; };
  }, []);

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

  const home = () => {
    setScreen("home"); setDetection(null); setError("");
    void reloadProjects().catch(() => undefined);
  };

  const chooseFolder = async () => {
    setBusy(true); setError("");
    try {
      const chosen = await open({ directory: true, multiple: false, title: "Choose a project folder" });
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

  if (screen === "add") return <main className="app-shell"><Header home={home} />
    <section className="page-head"><div><div className="eyebrow">Project foundation</div><h1>Add a local project.</h1><p>Choose a folder. MellowYak observes Git and scans source locally.</p></div><button className="secondary" onClick={home}>Back</button></section>
    {error && <section className="panel error" role="alert">{error}</section>}
    {!detection ? <section className="panel folder-picker"><div className="folder-icon">⌁</div><h2>Choose the project you want to understand</h2><p>Only the selected folder and its repository root are inspected. Nothing is uploaded.</p><button className="primary" disabled={busy} onClick={() => void chooseFolder()}>{busy ? "Inspecting…" : "Choose project folder"}</button></section>
      : <div className="content-grid add-grid">
        <section className="panel"><div className="section-head"><h2>Detected project</h2><span className="local-badge">Local only</span></div>
          <label className="field"><span>Project name</span><input value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
          <StatusRow label="Selected folder" value={detection.selected_path} /><StatusRow label="Repository root" value={detection.repository_path} />
          <StatusRow label="Candidate files" value={String(detection.candidate_files)} /><StatusRow label="Ignored paths" value={String(detection.ignored_paths)} />
          <h3>Languages</h3><Tags values={detection.languages} empty="No supported language detected yet." />
          <h3>Frameworks and runtime</h3><Tags values={[...detection.frameworks, ...detection.runtime_hints]} empty="No framework manifest detected." />
          <h3>Tests</h3><Tags values={detection.tests} empty="No test runner detected yet." />
        </section>
        <section className="panel"><h2>Git observation</h2>
          <StatusRow label="Status" value={detection.git.available ? "Available" : "Git unavailable"} tone={detection.git.available ? "good" : "warn"} />
          <StatusRow label="Branch" value={detection.git.branch || (detection.git.is_detached ? "Detached HEAD" : "Unknown")} />
          <StatusRow label="HEAD" value={detection.git.head_sha?.slice(0, 12) || "Unknown"} />
          <StatusRow label="Worktree" value={detection.git.is_dirty ? "Changes present" : "Clean"} tone={detection.git.is_dirty ? "warn" : "good"} />
          <StatusRow label="Changes" value={`${detection.git.staged.length} staged · ${detection.git.unstaged.length} unstaged · ${detection.git.untracked.length} untracked`} />
          <label className="field"><span>Passive monitoring</span><select value={monitoring} onChange={(event) => setMonitoring(event.target.value as "passive" | "paused")}><option value="passive">On — observe local changes</option><option value="paused">Paused</option></select></label>
          <div className="privacy-note"><strong>Your source remains local.</strong><span>The first real scan starts after connection. Unsupported and unknown coverage is reported honestly.</span></div>
          <div className="button-row"><button className="secondary" onClick={() => setDetection(null)}>Choose another</button><button className="primary" disabled={busy || !displayName.trim()} onClick={() => void connect()}>{busy ? "Connecting…" : "Connect project"}</button></div>
        </section>
      </div>}
  </main>;

  if (screen === "project" && selected) {
    const ready = readiness(selected);
    return <main className="app-shell"><Header home={home} />
      <section className="page-head"><div><div className="eyebrow">Local project</div><h1>{selected.display_name}</h1><p>{selected.repository_path}</p></div><span className={`readiness ${ready.tone}`}>{ready.label}</span></section>
      {error && <section className="panel error" role="alert">{error}</section>}
      <div className="project-grid">
        <section className="panel"><div className="section-head"><h2>Source scan</h2><span>{scanPercent}%</span></div><div className="progress"><span style={{ width: `${scanPercent}%` }} /></div>
          {!selected.scan ? <p className="muted">Preparing initial scan…</p> : <><StatusRow label="Status" value={selected.scan.status} tone={selected.scan.status === "completed" ? "good" : selected.scan.status === "failed" ? "warn" : "neutral"} /><StatusRow label="Progress" value={`${selected.scan.processed_files} / ${selected.scan.total_candidates} files`} /><StatusRow label="Indexed" value={String(selected.scan.included_files)} /><StatusRow label="Excluded" value={String(selected.scan.excluded_files)} /><StatusRow label="Sensitive" value={String(selected.scan.sensitive_files)} /><StatusRow label="Unknown" value={String(selected.scan.unknown_items)} /><StatusRow label="Unsupported" value={String(selected.scan.unsupported_files)} /></>}
          <div className="button-row">{selected.scan?.status === "running" ? <button className="secondary danger" onClick={() => void cancelProjectScan(selected.id)}>Cancel scan</button> : <button className="secondary" onClick={() => void startProjectScan(selected.id)}>Run scan again</button>}</div>
        </section>
        <section className="panel"><div className="section-head"><h2>Git and monitoring</h2><span className={selected.monitoring_status === "active" ? "live-dot" : "muted"}>{selected.monitoring_status}</span></div>
          <StatusRow label="Git" value={selected.git.available ? selected.git.branch || "Detached HEAD" : "Git unavailable"} tone={selected.git.available ? "good" : "warn"} /><StatusRow label="HEAD" value={selected.git.head_sha?.slice(0, 12) || "Unknown"} /><StatusRow label="Worktree" value={selected.git.is_dirty ? "Changes present" : "Clean"} tone={selected.git.is_dirty ? "warn" : "good"} /><StatusRow label="Changes" value={`${selected.git.staged.length} staged · ${selected.git.unstaged.length} unstaged · ${selected.git.untracked.length} untracked`} />
          <div className="button-row"><button className="secondary" onClick={() => void openProjectFolder(selected.id)}>Open folder</button><button className="secondary" onClick={() => void setProjectMonitoring(selected.id, selected.monitoring_status !== "active")}>{selected.monitoring_status === "active" ? "Pause monitoring" : "Resume monitoring"}</button></div>
        </section>
        <section className="panel impact-panel"><h2>Impact foundation</h2><div className="metric-grid"><div><strong>{impact?.files_indexed ?? 0}</strong><span>files indexed</span></div><div><strong>{impact?.direct_relationships ?? 0}</strong><span>direct relationships</span></div><div><strong>{impact?.tests_found ?? 0}</strong><span>tests found</span></div><div><strong>{impact?.languages ?? 0}</strong><span>languages</span></div></div><div className="coverage-note"><strong>Known coverage</strong><span>{impact?.unknown_references ?? 0} unknown references · {impact?.unsupported_files ?? 0} unsupported files · {impact?.stale_relationships ?? 0} stale relationships</span></div><Tags values={selected.languages} empty="Unknown coverage until scanning completes." /></section>
      </div>
    </main>;
  }

  return <main className="app-shell"><Header home={home} />
    <section className="hero"><div className="eyebrow">Local core · Project intelligence</div><h1>{projects.length ? "Your projects, understood locally." : "Your local engine is ready."}</h1><p>Your data stays on this machine.</p><div className="privacy-pills"><span>No Docker.</span><span>No external database.</span><span>No cloud required.</span></div></section>
    {error ? <section className="panel error" role="alert"><h2>Local Engine unavailable</h2><p>{error}</p></section> : !snapshot ? <section className="panel loading">Verifying local engine and storage…</section> : <>
      {projects.length ? <section className="project-list"><div className="section-head"><h2>Connected projects</h2><button className="primary" onClick={() => setScreen("add")}>Add project</button></div>{projects.map((project) => { const ready = readiness(project); return <button className="project-card" key={project.id} onClick={() => { setSelected(project); setImpact(null); setScreen("project"); }}><span><strong>{project.display_name}</strong><small>{project.repository_path}</small></span><span className={`readiness ${ready.tone}`}>{ready.label}</span></button>; })}</section>
        : <div className="content-grid"><section className="panel"><div className="section-head"><h2>Verified local status</h2><span className="live-dot">Live</span></div><StatusRow label="Local Engine" value={snapshot.health.status === "ready" ? "Running" : snapshot.health.status} tone="good" /><StatusRow label="Storage Location" value={snapshot.storage.data_root} /><StatusRow label="Database" value="SQLite — Local" tone="good" /><StatusRow label="Network Mode" value="Local only" tone="good" /><StatusRow label="Cloud" value={snapshot.privacy.cloud_connected ? "Connected" : "Not connected"} /></section><section className="panel privacy-card"><h2>Private by default</h2><ul><li>Your code stays local.</li><li>Your project data stays local.</li><li>Your evidence stays local.</li></ul><p>Data leaves only through connectors you explicitly enable.</p><div className="versions"><span>App <strong>{snapshot.health.app_version}</strong></span><span>Engine <strong>{snapshot.health.engine_version}</strong></span><span>Schema <strong>{snapshot.health.database_schema_version}</strong></span></div></section></div>}
      <footer className="actions">{!projects.length && <button className="primary" onClick={() => setScreen("add")}>Add your first project</button>}<button className="secondary" onClick={() => void openDataFolder()}>Open data folder</button><details><summary>View local diagnostics</summary><pre>{JSON.stringify(snapshot.readiness, null, 2)}</pre></details></footer>
    </>}
  </main>;
}
