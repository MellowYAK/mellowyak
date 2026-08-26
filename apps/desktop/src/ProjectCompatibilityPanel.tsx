import { useCallback, useEffect, useState } from "react";
import { getProjectCompatibility, type ProjectCompatibility } from "./api";
import "./compatibility.css";

type T = (key: string, parameters?: Record<string, string | number>) => string;

function codeLabel(t: T, group: string, value: string): string {
  return t(`phase14.${group}.${value}`);
}

export function ProjectCompatibilityPanel({
  projectId,
  t,
  data,
}: {
  projectId: string;
  t: T;
  data?: ProjectCompatibility;
}) {
  const [assessment, setAssessment] = useState<ProjectCompatibility | null>(data ?? null);
  const [error, setError] = useState(false);
  const refresh = useCallback(async () => {
    if (data) return;
    try {
      setAssessment(await getProjectCompatibility(projectId));
      setError(false);
    } catch {
      setError(true);
    }
  }, [data, projectId]);
  useEffect(() => { void refresh(); }, [refresh]);
  if (!assessment) {
    return <section className="panel compatibility-panel" role={error ? "alert" : "status"}>
      <strong>{t(error ? "phase14.compatibility.loadFailed" : "phase14.compatibility.loading")}</strong>
      {error && <button className="secondary" onClick={() => void refresh()}>{t("phase10.action.retry")}</button>}
    </section>;
  }
  const counts = assessment.inventory.classification_counts;
  return <section className="panel compatibility-panel" aria-label={t("phase14.compatibility.title")}>
    <div className="section-head"><div><h2>{t("phase14.compatibility.title")}</h2><p>{t("phase14.compatibility.body")}</p></div><span className="truth-pill neutral">{codeLabel(t, "state", assessment.state)}</span></div>
    <div className="compatibility-metrics">
      <div><span>{t("phase14.compatibility.passive")}</span><strong>{t(assessment.passive_monitoring_ready ? "common.yes" : "common.no")}</strong></div>
      <div><span>{t("phase14.compatibility.automatic")}</span><strong>{t(assessment.automatic_checks_eligible ? "common.yes" : "common.no")}</strong></div>
      <div><span>{t("phase14.compatibility.included")}</span><strong>{assessment.inventory.included_files}</strong></div>
      <div><span>{t("phase14.compatibility.excluded")}</span><strong>{assessment.inventory.excluded_items}</strong></div>
      <div><span>{t("phase14.compatibility.unsupported")}</span><strong>{assessment.inventory.unsupported_files}</strong></div>
    </div>
    <div className="compatibility-columns">
      <div><h3>{t("phase14.compatibility.structure")}</h3><ul>{assessment.detected_structure.map((item) => <li key={item}>{codeLabel(t, "structure", item)}</li>)}</ul></div>
      <div><h3>{t("phase14.compatibility.probes")}</h3><ul>{assessment.available_probe_types.map((item) => <li key={item}>{codeLabel(t, "probe", item)}</li>)}</ul></div>
      <div><h3>{t("phase14.compatibility.classification")}</h3><ul>{Object.entries(counts).filter(([, value]) => value > 0).map(([item, value]) => <li key={item}><span>{codeLabel(t, "classification", item)}</span><strong>{value}</strong></li>)}</ul></div>
    </div>
    <div className="compatibility-runtime-list">
      <h3>{t("phase14.compatibility.runtimes")}</h3>
      {assessment.runtimes.map((runtime, index) => <article key={`${runtime.runtime_type}-${runtime.package_root}-${index}`}>
        <div><strong>{runtime.runtime_type}</strong><small>{codeLabel(t, "owner", runtime.runtime_owner)}</small></div>
        <code dir="ltr">{runtime.package_root}</code>
        <span>{runtime.package_manager ?? t("common.unknown")}</span>
        <span>{t(runtime.approved ? "phase14.compatibility.approved" : "phase14.compatibility.approvalRequired")}</span>
      </article>)}
    </div>
    <details><summary>{t("phase14.compatibility.advanced")}</summary>
      <div className="compatibility-columns"><div><h3>{t("phase14.compatibility.knownLimits")}</h3><ul>{assessment.known_limitations.map((item) => <li key={item}><code dir="ltr">{item}</code></li>)}</ul></div><div><h3>{t("phase14.compatibility.unknowns")}</h3><ul>{assessment.unknowns.map((item) => <li key={item}>{t(item)}</li>)}</ul></div></div>
    </details>
    <p className="privacy-note"><strong>{t("phase14.compatibility.safeNextAction")}</strong> {t(assessment.safe_next_action)}</p>
  </section>;
}
