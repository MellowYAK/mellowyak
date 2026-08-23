import { useEffect, useState } from "react";
import { loadSetupSnapshot, openDataFolder, type SetupSnapshot } from "./api";

type Screen = "setup" | "add-project";

function StatusRow({ label, value, tone = "neutral" }: { label: string; value: string; tone?: "good" | "neutral" }) {
  return (
    <div className="status-row">
      <span>{label}</span>
      <strong className={tone === "good" ? "good" : ""}>{value}</strong>
    </div>
  );
}

export function App() {
  const [snapshot, setSnapshot] = useState<SetupSnapshot | null>(null);
  const [error, setError] = useState("");
  const [screen, setScreen] = useState<Screen>("setup");

  useEffect(() => {
    let active = true;
    loadSetupSnapshot()
      .then((value) => active && setSnapshot(value))
      .catch((reason: unknown) => active && setError(reason instanceof Error ? reason.message : "LOCAL_ENGINE_UNAVAILABLE"));
    return () => {
      active = false;
    };
  }, []);

  if (screen === "add-project") {
    return (
      <main className="app-shell compact">
        <section className="panel placeholder" aria-labelledby="phase-two-title">
          <div className="phase-label">Phase 2</div>
          <h1 id="phase-two-title">Add your first project</h1>
          <p>Project selection, Git observation, and source scanning are intentionally deferred to Phase 2.</p>
          <button className="secondary" onClick={() => setScreen("setup")}>Back to local setup</button>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="brand-bar">
        <div className="mark" aria-hidden="true">MY</div>
        <div>
          <div className="brand-name">MellowYak</div>
          <div className="tagline">Protect what already works.</div>
        </div>
        <div className="principle">Passive by default. Active when it matters.</div>
      </header>

      <section className="hero" aria-labelledby="setup-title">
        <div className="eyebrow">Local core · First setup</div>
        <h1 id="setup-title">Your local engine is ready.</h1>
        <p>Your data stays on this machine.</p>
        <div className="privacy-pills" aria-label="Local privacy guarantees">
          <span>No Docker.</span><span>No external database.</span><span>No cloud required.</span>
        </div>
      </section>

      {error ? (
        <section className="panel error" role="alert">
          <h2>Local Engine unavailable</h2>
          <p>{error}</p>
        </section>
      ) : !snapshot ? (
        <section className="panel loading" aria-live="polite">Verifying local engine and storage…</section>
      ) : (
        <div className="content-grid">
          <section className="panel" aria-labelledby="status-title">
            <div className="section-head"><h2 id="status-title">Verified local status</h2><span className="live-dot">Live</span></div>
            <StatusRow label="Local Engine" value={snapshot.health.status === "ready" ? "Running" : snapshot.health.status} tone="good" />
            <StatusRow label="Storage Location" value={snapshot.storage.data_root} />
            <StatusRow label="Database" value="SQLite — Local" tone="good" />
            <StatusRow label="Evidence Folder" value={snapshot.storage.evidence} />
            <StatusRow label="Network Mode" value="Local only" tone="good" />
            <StatusRow label="Cloud" value={snapshot.privacy.cloud_connected ? "Connected" : "Not connected"} />
            <StatusRow label="Source Upload" value={snapshot.privacy.source_upload_enabled ? "On" : "Off"} tone="good" />
          </section>

          <section className="panel privacy-card" aria-labelledby="privacy-title">
            <h2 id="privacy-title">Private by default</h2>
            <ul>
              <li>Your code stays local.</li>
              <li>Your project data stays local.</li>
              <li>Your evidence stays local.</li>
            </ul>
            <p>Data leaves only through connectors you explicitly enable.</p>
            <div className="versions">
              <span>App <strong>{snapshot.health.app_version}</strong></span>
              <span>Engine <strong>{snapshot.health.engine_version}</strong></span>
              <span>Schema <strong>{snapshot.health.database_schema_version}</strong></span>
            </div>
          </section>
        </div>
      )}

      <footer className="actions">
        <button className="primary" disabled={!snapshot} onClick={() => setScreen("add-project")}>Add your first project</button>
        <button className="secondary" disabled={!snapshot} onClick={() => void openDataFolder()}>Open data folder</button>
        <details>
          <summary>View local diagnostics</summary>
          <pre>{snapshot ? JSON.stringify(snapshot.readiness, null, 2) : "Waiting for local engine…"}</pre>
        </details>
      </footer>
    </main>
  );
}
