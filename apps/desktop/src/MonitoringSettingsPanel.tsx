import { useEffect, useState } from "react";
import {
  getMonitoringPolicy,
  putMonitoringPolicy,
  type MonitoringPolicy,
} from "./api";

type T = (key: string, parameters?: Record<string, string | number>) => string;

export function MonitoringSettingsPanel({ t }: { t: T }) {
  const [policy, setPolicy] = useState<MonitoringPolicy | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "saving" | "error">("loading");

  useEffect(() => {
    void getMonitoringPolicy()
      .then((value) => {
        setPolicy(value);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  const update = async (value: Partial<MonitoringPolicy>) => {
    if (!policy) return;
    setStatus("saving");
    try {
      setPolicy(await putMonitoringPolicy(value));
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  };

  return <section className="panel phase13-live-settings" aria-labelledby="phase13-monitoring-settings-title">
    <div className="section-head">
      <div>
        <span className="eyebrow">{t("phase13.eyebrow")}</span>
        <h2 id="phase13-monitoring-settings-title">{t("phase13.screen.33-monitoring-settings.title")}</h2>
        <p>{t("phase13.screen.33-monitoring-settings.body")}</p>
      </div>
      {policy && <span className="phase13-pill good">{t("phase13.policyVersion", { version: policy.version })}</span>}
    </div>
    {status === "loading" && <p role="status">{t("phase13.loadingPolicy")}</p>}
    {status === "error" && <p className="error" role="alert">{t("phase13.policyUnavailable")}</p>}
    {policy && <div className="settings-grid">
      <label className="toggle-row">
        <span><strong>{t("phase13.observation")}</strong><small>{t("phase13.observationHelp")}</small></span>
        <input type="checkbox" checked={Boolean(policy.source_observation_enabled)} disabled={status === "saving"} onChange={(event) => void update({ source_observation_enabled: event.target.checked })} />
      </label>
      <label className="toggle-row">
        <span><strong>{t("phase13.automaticChecks")}</strong><small>{t("phase13.automaticChecksHelp")}</small></span>
        <input type="checkbox" checked={Boolean(policy.automatic_checking_enabled)} disabled={status === "saving"} onChange={(event) => void update({ automatic_checking_enabled: event.target.checked })} />
      </label>
      <label className="field">
        <span>{t("phase13.globalConcurrency")}</span>
        <input type="number" min={1} max={2} value={policy.max_concurrent_projects ?? 2} disabled={status === "saving"} onChange={(event) => void update({ max_concurrent_projects: Number(event.target.value) })} />
      </label>
      <label className="field">
        <span>{t("phase13.episodeBudget")}</span>
        <input type="number" min={1} max={2} value={policy.max_concurrent_probes ?? 2} disabled={status === "saving"} onChange={(event) => void update({ max_concurrent_probes: Number(event.target.value) })} />
      </label>
    </div>}
    <p className="muted" role="status" aria-live="polite">{t(status === "saving" ? "phase13.savingPolicy" : "phase13.policySafety")}</p>
  </section>;
}
