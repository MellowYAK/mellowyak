import { useCallback, useEffect, useMemo, useState } from "react";
import {
  cancelProbe,
  createProbe,
  listProbes,
  runProbe,
  type ProbeDefinition,
  type ProbeRun,
  type ProbeType,
  type RuntimeProfile,
} from "./api";
import type { TranslationKey } from "./i18n";
import { SignalExplanation, type Phase7Translator } from "./Phase7Details";
import { useLocalEvents } from "./useLocalEvents";

const probeTypes: ProbeType[] = ["BROWSER", "HTTP", "CLI", "PROCESS", "TEST", "MANUAL"];

function probeTypeKey(value: string): TranslationKey {
  const keys: Record<string, TranslationKey> = {
    BROWSER: "probe.type.browser",
    HTTP: "probe.type.httpApi",
    CLI: "probe.type.cli",
    PROCESS: "probe.type.processHealth",
    TEST: "probe.type.testRunner",
    MANUAL: "probe.type.manual",
  };
  return keys[value] ?? "probe.type.unknown";
}

function resultKey(value: string): TranslationKey {
  const keys: Record<string, TranslationKey> = {
    NOT_RUN: "probe.result.notRun",
    QUEUED: "probe.result.queued",
    RUNNING: "probe.result.running",
    PASS: "probe.result.passed",
    PASSED: "probe.result.passed",
    FAIL: "probe.result.failed",
    FAILED: "probe.result.failed",
    INCONCLUSIVE: "probe.result.inconclusive",
    CANCELLED: "probe.result.cancelled",
  };
  return keys[value] ?? "probe.result.unknown";
}

function splitArguments(value: string): string[] {
  return value.split("\n").map((item) => item.trim()).filter(Boolean);
}

export function ProbePanel({ projectId, behaviorId = null, profiles = [], t, onError }: {
  projectId: string;
  behaviorId?: string | null;
  profiles?: RuntimeProfile[];
  t: Phase7Translator;
  onError: (code: string) => void;
}) {
  const [probes, setProbes] = useState<ProbeDefinition[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("");
  const [probeType, setProbeType] = useState<ProbeType>("HTTP");
  const [runtimeVersionId, setRuntimeVersionId] = useState("");
  const [target, setTarget] = useState("");
  const [argumentsText, setArgumentsText] = useState("");
  const [expected, setExpected] = useState("");
  const [timeout, setTimeoutValue] = useState(30);
  const [latestRun, setLatestRun] = useState<ProbeRun | null>(null);

  const refresh = useCallback(async () => {
    const items = await listProbes(projectId);
    const scoped = behaviorId ? items.filter((item) => item.behavior_id === behaviorId) : items;
    setProbes(scoped);
    setSelectedId((current) => current ?? scoped[0]?.id ?? null);
  }, [behaviorId, projectId]);

  useEffect(() => { void refresh().catch((reason) => onError(reason instanceof Error ? reason.message : "PROBE_LOAD_FAILED")); }, [refresh, onError]);
  useLocalEvents(projectId, (event) => { if (event.type.startsWith("probe_") || event.type === "signal_classified") void refresh().catch(() => undefined); });

  const selected = useMemo(() => probes.find((item) => item.id === selectedId) ?? null, [probes, selectedId]);
  const selectedLastRun = latestRun?.probe_id === selected?.id ? latestRun : selected?.last_run ?? null;

  const execute = async (operation: () => Promise<void>) => {
    setBusy(true); onError("");
    try { await operation(); }
    catch (reason) { onError(reason instanceof Error ? reason.message : "PROBE_OPERATION_FAILED"); }
    finally { setBusy(false); }
  };

  const save = () => void execute(async () => {
    const argv = splitArguments(argumentsText);
    const definition: Record<string, unknown> = probeType === "HTTP"
      ? { url: target, method: "GET" }
      : probeType === "PROCESS"
        ? { executable: target, argv }
      : probeType === "MANUAL"
          ? { confirmed: true, note: target }
          : probeType === "BROWSER"
            ? { entry_url: target }
            : { executable: target, argv };
    const expectedResult = probeType === "HTTP"
      ? { status: Number(expected) || 200 }
      : probeType === "CLI" || probeType === "TEST"
        ? { exit_code: Number(expected) || 0 }
        : probeType === "PROCESS"
          ? { alive_seconds: Number(expected) || 1 }
        : { outcome: expected || "PASS" };
    const saved = await createProbe(projectId, {
      display_name: name,
      probe_type: probeType,
      behavior_id: behaviorId,
      runtime_profile_version_id: runtimeVersionId || null,
      definition,
      timeout_seconds: timeout,
      retry_policy: { max_attempts: 2 },
      expected_result: expectedResult,
      approved: true,
    });
    setCreating(false); setName(""); setTarget(""); setArgumentsText(""); setExpected("");
    await refresh(); setSelectedId(saved.id);
  });

  const runSelected = () => void execute(async () => {
    if (!selected) return;
    setLatestRun(await runProbe(projectId, selected.id));
    await refresh();
  });

  return <section className="panel probe-panel">
    <div className="section-head">
      <div><h2>{behaviorId ? t("probe.thisWorksTitle") : t("probe.title")}</h2><p className="muted">{behaviorId ? t("probe.thisWorksBody") : t("probe.description")}</p></div>
      <button className="primary" onClick={() => setCreating((value) => !value)}>{creating ? t("common.cancel") : t("probe.add")}</button>
    </div>
    {creating && <div className="probe-builder">
      <label className="field"><span>{t("probe.name")}</span><input value={name} onChange={(event) => setName(event.target.value)} /></label>
      <label className="field"><span>{t("probe.type")}</span><select value={probeType} onChange={(event) => setProbeType(event.target.value as ProbeType)}>{probeTypes.map((item) => <option key={item} value={item}>{t(probeTypeKey(item))}</option>)}</select></label>
      {profiles.length > 0 && <label className="field"><span>{t("probe.runtime")}</span><select value={runtimeVersionId} onChange={(event) => setRuntimeVersionId(event.target.value)}><option value="">{t("probe.runtimeOptional")}</option>{profiles.map((profile) => <option key={profile.id} value={profile.current_version_id}>{profile.display_name}</option>)}</select></label>}
      <label className="field probe-wide"><span>{t(probeType === "HTTP" ? "probe.targetUrl" : probeType === "MANUAL" ? "probe.instructions" : probeType === "BROWSER" ? "probe.startUrl" : "probe.executable")}</span><input dir={probeType === "MANUAL" ? undefined : "ltr"} value={target} onChange={(event) => setTarget(event.target.value)} /></label>
      {(probeType === "CLI" || probeType === "PROCESS" || probeType === "TEST") && <label className="field probe-wide"><span>{t("probe.arguments")}</span><textarea dir="ltr" value={argumentsText} placeholder={t("probe.argumentsHint")} onChange={(event) => setArgumentsText(event.target.value)} /></label>}
      <label className="field"><span>{t("probe.expected")}</span><input value={expected} onChange={(event) => setExpected(event.target.value)} /></label>
      <label className="field"><span>{t("probe.timeout")}</span><input type="number" min={1} max={300} value={timeout} onChange={(event) => setTimeoutValue(Number(event.target.value))} /></label>
      <div className="probe-wide privacy-note"><strong>{t("probe.executionSafety")}</strong><span>{t("probe.executionSafetyBody")}</span></div>
      <div className="probe-wide button-row"><button className="primary" disabled={busy || !name.trim() || !target.trim()} onClick={save}>{busy ? t("common.working") : t("probe.save")}</button></div>
    </div>}
    {probes.length ? <div className="probe-layout">
      <nav className="probe-list" aria-label={t("probe.list")}>{probes.map((probe) => <button key={probe.id} className={probe.id === selectedId ? "active" : ""} onClick={() => { setSelectedId(probe.id); setLatestRun(null); }}><strong>{probe.display_name}</strong><small>{t(probeTypeKey(probe.probe_type))}</small></button>)}</nav>
      {selected && <article className="probe-detail">
        <div className="section-head"><div><h3>{selected.display_name}</h3><span className="local-badge">{t(probeTypeKey(selected.probe_type))}</span></div><button className="primary" disabled={busy} onClick={runSelected}>{busy ? t("common.working") : t("probe.run")}</button></div>
        <div className="status-row"><span>{t("probe.runtime")}</span><strong>{selected.current_version.runtime_profile_version_id ? t("probe.runtimeBound") : t("probe.runtimeIndependent")}</strong></div>
        <div className="status-row"><span>{t("probe.lastResult")}</span><strong>{t(resultKey(selectedLastRun?.result ?? "NOT_RUN"))}</strong></div>
        <div className="status-row"><span>{t("probe.automaticEligibility")}</span><strong>{selected.current_version.approved_at ? t("probe.eligible") : t("probe.needsApproval")}</strong></div>
        {selectedLastRun && ["QUEUED", "RUNNING"].includes(selectedLastRun.status) && <button className="secondary danger" disabled={busy} onClick={() => void execute(async () => { await cancelProbe(projectId, selected.id); await refresh(); })}>{t("probe.cancel")}</button>}
        {selectedLastRun?.signal && <SignalExplanation state={String(selectedLastRun.signal.state ?? "WATCH")} reasonCodes={Array.isArray(selectedLastRun.signal.reason_codes) ? selectedLastRun.signal.reason_codes.map(String) : []} technical={selectedLastRun.signal} t={t} />}
        <details><summary>{t("common.technicalDetails")}</summary><pre dir="ltr">{JSON.stringify({ version: selected.current_version.version_number, definition: selected.current_version.definition, expected: selected.current_version.expected_result, source_links: selected.current_version.source_links }, null, 2)}</pre></details>
      </article>}
    </div> : !creating && <div className="empty-state"><strong>{t("probe.empty")}</strong><p className="muted">{t("probe.emptyBody")}</p></div>}
  </section>;
}
