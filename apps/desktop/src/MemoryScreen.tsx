import { useCallback, useEffect, useMemo, useState } from "react";
import {
  createKnownGoodMilestone,
  createYakReceipt,
  createSnapshot,
  getSnapshot,
  listEpisodes,
  listMilestones,
  listSnapshots,
  listYakReceipts,
  materializeSnapshot,
  setSnapshotPinned,
  type Project,
  type SnapshotMilestone,
  type SourceEpisode,
  type SourceSnapshot,
  type YakReceipt,
} from "./api";
import type { TranslationKey } from "./i18n";
import type { Phase7Translator } from "./Phase7Details";
import { useLocalEvents } from "./useLocalEvents";

function byteCount(value: number, t: Phase7Translator): string {
  const units: TranslationKey[] = ["common.unit.bytes", "common.unit.kibibytes", "common.unit.mebibytes", "common.unit.gibibytes"];
  let amount = value;
  let index = 0;
  while (amount >= 1024 && index < units.length - 1) { amount /= 1024; index += 1; }
  return t("common.sizeValue", { value: new Intl.NumberFormat(document.documentElement.lang, { maximumFractionDigits: index ? 1 : 0 }).format(amount), unit: t(units[index]) });
}

function dateTime(value: string): string {
  return new Intl.DateTimeFormat(document.documentElement.lang, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function episodeStatusKey(value: string): TranslationKey {
  const keys: Record<string, TranslationKey> = {
    OPEN: "episode.state.open",
    STABILIZING: "episode.state.stabilizing",
    STABILIZED: "episode.state.stabilized",
    FAILED: "episode.state.failed",
  };
  return keys[value] ?? "episode.state.unknown";
}

function snapshotReasonKey(value: string): TranslationKey {
  const keys: Record<string, TranslationKey> = {
    INITIAL_SAVE_POINT: "snapshot.reason.initial",
    MANUAL_SAVE_POINT: "snapshot.reason.manual",
    EPISODE_STABILIZED: "snapshot.reason.episode",
    KNOWN_GOOD: "snapshot.reason.knownGood",
  };
  return keys[value] ?? "snapshot.reason.other";
}

function gitAnchor(snapshot: SourceSnapshot, t: Phase7Translator): string {
  const head = snapshot.git_anchor.head_sha;
  if (typeof head === "string" && head) return head.slice(0, 12);
  return t("memory.gitNotRequired");
}

export function MemoryScreen({ project, t, onError }: { project: Project; t: Phase7Translator; onError: (code: string) => void }) {
  const [snapshots, setSnapshots] = useState<SourceSnapshot[]>([]);
  const [episodes, setEpisodes] = useState<SourceEpisode[]>([]);
  const [milestones, setMilestones] = useState<SnapshotMilestone[]>([]);
  const [selected, setSelected] = useState<SourceSnapshot | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [milestoneName, setMilestoneName] = useState("");
  const [showMilestone, setShowMilestone] = useState(false);
  const [materializedPath, setMaterializedPath] = useState("");
  const [receipts, setReceipts] = useState<YakReceipt[]>([]);
  const [selectedReceipt, setSelectedReceipt] = useState<YakReceipt | null>(null);

  const refresh = useCallback(async () => {
    const [nextSnapshots, nextEpisodes, nextMilestones, nextReceipts] = await Promise.all([
      listSnapshots(project.id), listEpisodes(project.id), listMilestones(project.id), listYakReceipts(project.id),
    ]);
    setSnapshots(nextSnapshots); setEpisodes(nextEpisodes); setMilestones(nextMilestones); setReceipts(nextReceipts);
    setSelected((current) => current ? nextSnapshots.find((item) => item.id === current.id) ?? current : null);
  }, [project.id]);

  useEffect(() => { void refresh().catch((reason) => onError(reason instanceof Error ? reason.message : "MEMORY_LOAD_FAILED")); }, [refresh, onError]);
  useLocalEvents(project.id, (event) => { if (event.type.startsWith("snapshot_") || event.type.startsWith("episode_") || event.type === "milestone_accepted") void refresh().catch(() => undefined); });

  const metrics = useMemo(() => snapshots.reduce((result, snapshot) => ({
    physical: result.physical + snapshot.physical_bytes_added,
    reused: result.reused + snapshot.reused_bytes,
    logical: result.logical + snapshot.logical_bytes,
  }), { physical: 0, reused: 0, logical: 0 }), [snapshots]);

  const run = async (id: string, operation: () => Promise<void>) => {
    setBusy(id); onError("");
    try { await operation(); await refresh(); }
    catch (reason) { onError(reason instanceof Error ? reason.message : "MEMORY_OPERATION_FAILED"); }
    finally { setBusy(null); }
  };

  const openDetail = () => {
    if (!selected) return;
    void run(selected.id, async () => setSelected(await getSnapshot(project.id, selected.id)));
  };

  const copyReceipt = async (receipt: YakReceipt) => {
    const payload = receipt.payload;
    const lines = [
      t("yakReceipt.title"),
      t("yakReceipt.changeSettled"),
      dateTime(payload.settled_at),
      `${t("yakReceipt.considered")}: ${payload.protected_behaviors_considered}`,
      `${t("yakReceipt.checked")}: ${payload.checked}`,
      `${t("yakReceipt.passed")}: ${payload.passed}`,
      `${t("yakReceipt.confirmed")}: ${payload.confirmed_regressions}`,
      `${t("yakReceipt.deferred")}: ${payload.deferred}`,
      `${t("yakReceipt.runtimeUnavailable")}: ${payload.runtime_unavailable}`,
      `${t("yakReceipt.omitted")}: ${payload.omitted}`,
      `${t("yakReceipt.unknown")}: ${payload.unknown}`,
      `${t("yakReceipt.sourceModified")}: ${payload.source_modified_by_yak ? t("common.yes") : t("common.no")}`,
      `${t("yakReceipt.digest")}: ${receipt.digest}`,
    ];
    await navigator.clipboard.writeText(lines.join("\n"));
  };

  return <div className="phase7-page">
    <section className="page-head"><div><div className="eyebrow">{t("memory.eyebrow")}</div><h1>{t("memory.title")}</h1><p>{t("memory.subtitle")}</p></div><button className="primary" disabled={busy === "create"} onClick={() => void run("create", async () => { const saved = await createSnapshot(project.id); setSelected(saved); })}>{busy === "create" ? t("common.working") : t("memory.createSavePoint")}</button></section>
    <section className="memory-metrics metric-grid">
      <div><strong>{snapshots.length}</strong><span>{t("memory.savePoints")}</span></div>
      <div><strong>{byteCount(metrics.physical, t)}</strong><span>{t("memory.physicalAdded")}</span></div>
      <div><strong>{byteCount(metrics.reused, t)}</strong><span>{t("memory.reused")}</span></div>
      <div><strong>{milestones.length}</strong><span>{t("memory.knownGood")}</span></div>
    </section>
    <div className="memory-layout">
      <section className="panel episode-timeline">
        <div className="section-head"><div><h2>{t("episode.title")}</h2><p className="muted">{t("episode.description")}</p></div><span>{episodes.length}</span></div>
        {episodes.length ? <ol>{episodes.map((episode) => <li key={episode.id}><span className={`timeline-marker ${episode.status.toLowerCase()}`} aria-hidden="true" /><article><div className="section-head"><strong>{t(episodeStatusKey(episode.status))}</strong><time>{dateTime(episode.started_at)}</time></div><p>{t("episode.changeSummary", { added: episode.added_paths.length, modified: episode.modified_paths.length, deleted: episode.deleted_paths.length })}</p><small>{t("episode.events", { count: episode.event_count })}</small>{episode.dependency_changes.length > 0 && <span className="local-badge">{t("episode.dependenciesChanged", { count: episode.dependency_changes.length })}</span>}<div className="button-row">{receipts.find((item) => item.episode_id === episode.id) ? <button className="secondary" onClick={() => setSelectedReceipt(receipts.find((item) => item.episode_id === episode.id) ?? null)}>{t("yakReceipt.open")}</button> : episode.status === "STABILIZED" && <button className="secondary" disabled={busy === episode.id} onClick={() => void run(episode.id, async () => { const receipt = await createYakReceipt(project.id, episode.id); setSelectedReceipt(receipt); })}>{t("yakReceipt.create")}</button>}</div></article></li>)}</ol>
          : <div className="empty-state"><strong>{t("episode.empty")}</strong><p className="muted">{t("episode.emptyBody")}</p></div>}
      </section>
      <section className="panel save-point-history">
        <div className="section-head"><div><h2>{t("snapshot.history")}</h2><p className="muted">{t("snapshot.historyBody")}</p></div><span>{snapshots.length}</span></div>
        {snapshots.length ? <div className="snapshot-list">{snapshots.map((snapshot) => <button key={snapshot.id} className={selected?.id === snapshot.id ? "active" : ""} onClick={() => { setSelected(snapshot); setMaterializedPath(""); }}><span><strong>{t(snapshotReasonKey(snapshot.creation_reason))}</strong><small>{dateTime(snapshot.created_at)}</small></span><span><small>{t("snapshot.addedBytes", { value: byteCount(snapshot.physical_bytes_added, t) })}</small><small>{t("snapshot.reusedBytes", { value: byteCount(snapshot.reused_bytes, t) })}</small></span>{snapshot.pinned && <span className="pin" title={t("snapshot.pinned")}>◆</span>}</button>)}</div>
          : <div className="empty-state"><strong>{t("snapshot.empty")}</strong><p className="muted">{t("snapshot.emptyBody")}</p></div>}
      </section>
    </div>
    {selectedReceipt && <section className="panel yak-receipt" aria-label={t("yakReceipt.title")}>
      <div className="section-head"><div><div className="eyebrow">{t("yakReceipt.localProof")}</div><h2>{t("yakReceipt.title")}</h2><p>{t("yakReceipt.description")}</p></div><button className="secondary" onClick={() => setSelectedReceipt(null)}>{t("common.close")}</button></div>
      <div className="receipt-settled"><strong>{t("yakReceipt.changeSettled")}</strong><time>{dateTime(selectedReceipt.payload.settled_at)}</time></div>
      <div className="metric-grid"><div><strong>{selectedReceipt.payload.protected_behaviors_considered}</strong><span>{t("yakReceipt.considered")}</span></div><div><strong>{selectedReceipt.payload.checked}</strong><span>{t("yakReceipt.checked")}</span></div><div><strong>{selectedReceipt.payload.passed}</strong><span>{t("yakReceipt.passed")}</span></div><div><strong>{selectedReceipt.payload.confirmed_regressions}</strong><span>{t("yakReceipt.confirmed")}</span></div><div><strong>{selectedReceipt.payload.deferred}</strong><span>{t("yakReceipt.deferred")}</span></div><div><strong>{selectedReceipt.payload.unknown}</strong><span>{t("yakReceipt.unknown")}</span></div></div>
      <div className="status-row"><span>{t("yakReceipt.runtimeUnavailable")}</span><strong>{selectedReceipt.payload.runtime_unavailable}</strong></div><div className="status-row"><span>{t("yakReceipt.omitted")}</span><strong>{selectedReceipt.payload.omitted}</strong></div><div className="status-row"><span>{t("yakReceipt.sourceModified")}</span><strong>{selectedReceipt.payload.source_modified_by_yak ? t("common.yes") : t("common.no")}</strong></div>
      <section><h3>{t("yakReceipt.evidence")}</h3>{selectedReceipt.payload.evidence.length ? selectedReceipt.payload.evidence.map((item, index) => <article className="evidence-row" key={`${String(item.run_id)}-${index}`}><strong>{t(`yakReceipt.result.${String(item.result)}` as TranslationKey)}</strong><code dir="ltr">{String(item.probe_id)}</code><span>{Boolean(item.comparable) ? t("yakReceipt.comparableYes") : t("yakReceipt.comparableNo")}</span></article>) : <p className="muted">{t("yakReceipt.noCheckedEvidence")}</p>}</section>
      <p className="privacy-note">{t("yakReceipt.truthNote")}</p><div className="button-row"><button className="primary" onClick={() => void copyReceipt(selectedReceipt)}>{t("yakReceipt.copy")}</button></div><details><summary>{t("common.technicalDetails")}</summary><pre dir="ltr">{JSON.stringify({ digest: selectedReceipt.digest, source_identity: selectedReceipt.source_identity, limitations: selectedReceipt.limitations }, null, 2)}</pre></details>
    </section>}
    {selected && <section className="panel snapshot-detail">
      <div className="section-head"><div><h2>{t("snapshot.detail")}</h2><code dir="ltr">{selected.id}</code></div><span className={selected.integrity_status === "VERIFIED" ? "readiness good" : "readiness warn"}>{selected.integrity_status === "VERIFIED" ? t("snapshot.integrityVerified") : t("snapshot.integrityNeedsAttention")}</span></div>
      <div className="snapshot-metrics">
        <div><span>{t("snapshot.included")}</span><strong>{selected.included_count}</strong></div>
        <div><span>{t("snapshot.excluded")}</span><strong>{selected.excluded_count}</strong></div>
        <div><span>{t("snapshot.sensitive")}</span><strong>{selected.sensitive_count}</strong></div>
        <div><span>{t("snapshot.unsupported")}</span><strong>{selected.unsupported_count}</strong></div>
        <div><span>{t("snapshot.logicalSize")}</span><strong>{byteCount(selected.logical_bytes, t)}</strong></div>
        <div><span>{t("snapshot.gitAnchor")}</span><strong>{gitAnchor(selected, t)}</strong></div>
      </div>
      <p className="privacy-note"><strong>{t("snapshot.liveSafe")}</strong><span>{t("snapshot.liveSafeBody")}</span></p>
      <div className="button-row">
        <button className="secondary" disabled={busy === selected.id} onClick={openDetail}>{t("snapshot.loadManifest")}</button>
        <button className="secondary" disabled={busy === selected.id} onClick={() => void run(selected.id, async () => { await setSnapshotPinned(project.id, selected.id, !selected.pinned); })}>{selected.pinned ? t("snapshot.unpin") : t("snapshot.pin")}</button>
        <button className="secondary" disabled={busy === selected.id} onClick={() => void run(selected.id, async () => { const result = await materializeSnapshot(project.id, selected.id); setMaterializedPath(result.relative_path); })}>{t("snapshot.materialize")}</button>
        <button className="primary" disabled={busy === selected.id} onClick={() => setShowMilestone((value) => !value)}>{t("milestone.markKnownGood")}</button>
      </div>
      {materializedPath && <div className="analysis-banner"><strong>{t("snapshot.materialized")}</strong><code dir="ltr">{materializedPath}</code></div>}
      {showMilestone && <div className="milestone-form"><label className="field"><span>{t("milestone.name")}</span><input value={milestoneName} onChange={(event) => setMilestoneName(event.target.value)} /></label><label className="toggle-row"><span>{t("milestone.humanAttested")}</span><input type="checkbox" checked readOnly /></label><button className="primary" disabled={!milestoneName.trim() || busy === "milestone"} onClick={() => void run("milestone", async () => { await createKnownGoodMilestone(project.id, { snapshot_id: selected.id, display_name: milestoneName, human_attested: true }); setMilestoneName(""); setShowMilestone(false); })}>{t("milestone.save")}</button></div>}
      {selected.entries && <details open><summary>{t("snapshot.entries", { count: selected.entries.length })}</summary><div className="snapshot-entry-list">{selected.entries.slice(0, 200).map((entry, index) => <code dir="ltr" key={`${String(entry.relative_path)}-${index}`}>{String(entry.relative_path)}</code>)}</div></details>}
      <details><summary>{t("common.technicalDetails")}</summary><pre dir="ltr">{JSON.stringify({ manifest_digest: selected.manifest_digest, source_identity: selected.source_identity, git_anchor: selected.git_anchor, runtime_profile_fingerprints: selected.runtime_profile_fingerprints ?? [] }, null, 2)}</pre></details>
    </section>}
    <section className="panel retention-panel"><div className="section-head"><div><h2>{t("memory.retention")}</h2><p className="muted">{t("memory.retentionBody")}</p></div><span className="local-badge">{t("memory.retentionDays", { days: project.snapshot_retention_days ?? 30 })}</span></div><div className="status-row"><span>{t("memory.storageCap")}</span><strong>{byteCount(project.snapshot_soft_cap_bytes ?? 5 * 1024 * 1024 * 1024, t)}</strong></div><div className="status-row"><span>{t("memory.deduplication")}</span><strong>{t("memory.deduplicationActive")}</strong></div></section>
  </div>;
}
