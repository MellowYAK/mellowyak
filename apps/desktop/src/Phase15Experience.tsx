import { mascotAssets } from "./mascots";
import "./phase15.css";

type T = (key: string, parameters?: Record<string, string | number>) => string;

export const phase15CaptureStates = [
  "00-product-lock-overview",
  "01-current-known-good-locked",
  "02-change-decision-required",
  "03-expected-change-reverified",
  "04-promotion-confirmation",
  "05-known-good-promoted",
  "06-repair-verified",
  "07-repair-live-progress",
  "08-repair-rolled-back",
  "09-yak-receipt",
  "10-yak-receipt-unknowns",
  "11-intel-mac-package-status",
] as const;

export type Phase15CaptureState = (typeof phase15CaptureStates)[number];

function isRepair(state: Phase15CaptureState) {
  return state.startsWith("06-") || state.startsWith("07-") || state.startsWith("08-");
}

function isReceipt(state: Phase15CaptureState) {
  return state.startsWith("09-") || state.startsWith("10-");
}

function currentState(state: Phase15CaptureState) {
  if (state.startsWith("00-") || state.startsWith("01-")) return "BASELINE_LOCKED";
  if (state.startsWith("02-")) return "CHANGE_REVIEW_REQUIRED";
  if (state.startsWith("03-")) return "PROMOTION_AWAITING_CONFIRMATION";
  if (state.startsWith("04-")) return "PROMOTION_AWAITING_CONFIRMATION";
  if (state.startsWith("05-")) return "PROMOTED";
  if (state.startsWith("06-")) return "REPAIR_VERIFIED";
  if (state.startsWith("07-")) return "VERIFYING_LIVE";
  if (state.startsWith("08-")) return "ROLLED_BACK";
  if (isReceipt(state)) return "EPISODE_BOUND_RECEIPT";
  return "PUBLIC_DISTRIBUTION_BLOCKED";
}

function tone(state: Phase15CaptureState) {
  if (state.startsWith("08-") || state.startsWith("10-") || state.startsWith("11-")) return "warn";
  if (state.startsWith("02-") || state.startsWith("04-") || state.startsWith("07-")) return "active";
  return "good";
}

function BaselineSurface({ state, t }: { state: Phase15CaptureState; t: T }) {
  const showDecision = state.startsWith("02-");
  const showVerified = state.startsWith("03-");
  const showConfirmation = state.startsWith("04-");
  const promoted = state.startsWith("05-");
  return <>
    <section className="panel phase15-lock">
      <div className="section-head"><div><h2>{t("baselineLock.title")}</h2><p>{t("baselineLock.subtitle")}</p></div><span className="local-badge">{t("common.localOnly")}</span></div>
      <div className="phase15-question"><strong>{t("baselineLock.changedTitle")}</strong><span>{t("baselineLock.changedQuestion")}</span></div>
      {showDecision && <><label className="field"><span>{t("baselineLock.reason")}</span><textarea readOnly value={t("phase15.fixture.expectedReason")} /></label><div className="button-row"><button className="primary">{t("baselineLock.expected")}</button><button className="secondary danger">{t("baselineLock.regression")}</button><button className="secondary">{t("baselineLock.unsure")}</button></div></>}
      {showVerified && <div className="phase15-callout good"><strong>{t("phase15.reverified")}</strong><span>{t("phase15.reverifiedBody")}</span><button className="primary">{t("baselineLock.reverify")}</button></div>}
      {showConfirmation && <section className="phase8-confirmation"><h3>{t("baselineLock.compareTitle")}</h3><div className="phase15-compare"><article><span>{t("baselineLock.old")}</span><code dir="ltr">{t("phase15.fixture.oldProof")}</code></article><article><span>{t("baselineLock.proposed")}</span><code dir="ltr">{t("phase15.fixture.proposedProof")}</code></article></div><p>{t("baselineLock.promotionWarning")}</p><label><input type="checkbox" defaultChecked /> <span>{t("baselineLock.confirm")}</span></label><div className="button-row"><button className="primary">{t("baselineLock.promote")}</button><button className="secondary">{t("common.cancel")}</button></div></section>}
      {!showDecision && !showVerified && !showConfirmation && <p className="privacy-note">{promoted ? t("phase15.promotedBody") : t("phase15.lockedBody")}</p>}
    </section>
    <section className="panel phase15-lineage"><div className="section-head"><h2>{t("baselineLock.lineage")}</h2><span>{promoted ? 2 : 1}</span></div>{promoted && <article className="current"><div><strong>{t("baselineLock.version", { number: 2 })}</strong><span className="readiness good">{t("baselineLock.current")}</span></div><p>{t("phase15.fixture.expectedReason")}</p><code dir="ltr">{t("phase15.fixture.proposedProof")}</code><small>{t("phase15.fixture.currentTime")}</small></article>}<article className={promoted ? "" : "current"}><div><strong>{t("baselineLock.version", { number: 1 })}</strong>{!promoted && <span className="readiness good">{t("baselineLock.current")}</span>}</div><p>{t("baselineLock.legacyRoot")}</p><code dir="ltr">{t("phase15.fixture.immutableProof")}</code><small>{t("phase15.fixture.previousTime")}</small></article></section>
  </>;
}

function RepairSurface({ state, t }: { state: Phase15CaptureState; t: T }) {
  const progress = state.startsWith("07-");
  const rolledBack = state.startsWith("08-");
  return <section className="panel phase15-repair">
    <div className="section-head"><div><h2>{rolledBack ? t("repairContract.restored") : progress ? t("repairContract.progress.rechecking") : t("repairContract.verifiedTitle")}</h2><p>{t("phase15.repairBody")}</p></div><span className={`readiness ${rolledBack ? "warn" : "good"}`}>{t(`phase15.state.${currentState(state)}`)}</span></div>
    <ul className="phase15-checks"><li>{t("repairContract.testedAway")}</li><li>{t("repairContract.behaviorPassed")}</li><li>{t("repairContract.liveMatched")}</li></ul>
    <div className="phase15-transaction"><article className="done"><span>1</span><strong>{t("repairContract.progress.checkingSource")}</strong></article><article className="done"><span>2</span><strong>{t("repairContract.progress.safetySnapshot")}</strong></article><article className={progress || rolledBack ? "done" : "active"}><span>3</span><strong>{t("repairContract.progress.applying")}</strong></article><article className={progress ? "active" : rolledBack ? "done" : "pending"}><span>4</span><strong>{t("repairContract.progress.rechecking")}</strong></article><article className={rolledBack ? "active" : "pending"}><span>5</span><strong>{t("repairContract.progress.restoring")}</strong></article></div>
    {rolledBack ? <div className="phase15-callout warn"><strong>{t("repairContract.restored")}</strong><span>{t("repairContract.nothingElse")}</span><span>{t("repairContract.candidateAvailable")}</span></div> : <div className="phase15-callout good"><strong>{progress ? t("repairContract.progress.rechecking") : t("repairContract.explicit")}</strong><span>{t("repairContract.recheck")}</span><span>{t("repairContract.rollback")}</span></div>}
    <div className="button-row"><button className="secondary">{t("repairContract.review")}</button>{!progress && !rolledBack && <button className="primary">{t("phase8.applyRepair")}</button>}</div>
  </section>;
}

function ReceiptSurface({ state, t }: { state: Phase15CaptureState; t: T }) {
  const unknowns = state.startsWith("10-");
  return <section className="panel phase15-receipt">
    <div className="section-head"><div><span className="eyebrow">{t("yakReceipt.localProof")}</span><h2>{t("yakReceipt.title")}</h2><p>{t("yakReceipt.description")}</p></div><button className="secondary">{t("common.close")}</button></div>
    <div className="phase15-settled"><strong>{t("yakReceipt.changeSettled")}</strong><time>{t("phase15.fixture.currentTime")}</time></div>
    <div className="phase15-receipt-grid"><article><strong>4</strong><span>{t("yakReceipt.considered")}</span></article><article><strong>{unknowns ? 1 : 3}</strong><span>{t("yakReceipt.checked")}</span></article><article><strong>{unknowns ? 1 : 3}</strong><span>{t("yakReceipt.passed")}</span></article><article><strong>0</strong><span>{t("yakReceipt.confirmed")}</span></article><article><strong>{unknowns ? 2 : 0}</strong><span>{t("yakReceipt.deferred")}</span></article><article><strong>{unknowns ? 3 : 1}</strong><span>{t("yakReceipt.unknown")}</span></article></div>
    <div className="status-row"><span>{t("yakReceipt.runtimeUnavailable")}</span><strong>{unknowns ? 1 : 0}</strong></div><div className="status-row"><span>{t("yakReceipt.omitted")}</span><strong>{unknowns ? 2 : 1}</strong></div><div className="status-row"><span>{t("yakReceipt.sourceModified")}</span><strong>{t("common.no")}</strong></div>
    <section className="phase15-evidence"><h3>{t("yakReceipt.evidence")}</h3><article><strong>{t("yakReceipt.result.PASS")}</strong><span>{t("phase15.fixture.behaviorOne")}</span><code dir="ltr">{t("phase15.fixture.runOne")}</code></article>{!unknowns && <><article><strong>{t("yakReceipt.result.PASS")}</strong><span>{t("phase15.fixture.behaviorTwo")}</span><code dir="ltr">{t("phase15.fixture.runTwo")}</code></article><article><strong>{t("yakReceipt.result.PASS")}</strong><span>{t("phase15.fixture.behaviorThree")}</span><code dir="ltr">{t("phase15.fixture.runThree")}</code></article></>}</section>
    <p className="privacy-note">{t("yakReceipt.truthNote")}</p><div className="button-row"><button className="primary">{t("yakReceipt.copy")}</button><button className="secondary">{t("common.technicalDetails")}</button></div><code className="phase15-digest" dir="ltr">{t("phase15.fixture.digest")}</code>
  </section>;
}

function PackageSurface({ t }: { t: T }) {
  return <section className="panel phase15-package"><div className="section-head"><div><h2>{t("phase15.package.title")}</h2><p>{t("phase15.package.body")}</p></div><span className="readiness warn">{t("phase15.package.blocked")}</span></div><div className="phase15-package-grid"><article><span>{t("phase15.package.version")}</span><strong>{t("phase15.fixture.version")}</strong></article><article><span>{t("phase15.package.architecture")}</span><strong>{t("phase15.fixture.architecture")}</strong></article><article><span>{t("phase15.package.schema")}</span><strong>{t("phase15.fixture.schema")}</strong></article><article><span>{t("phase15.package.tests")}</span><strong>{t("phase15.fixture.tests")}</strong></article></div><ul className="phase15-checks"><li>{t("phase15.package.appInstalled")}</li><li>{t("phase15.package.dmgVerified")}</li><li>{t("phase15.package.lifecycle")}</li></ul><div className="phase15-callout warn"><strong>{t("phase15.package.publicBlocked")}</strong><span>{t("phase15.package.publicBlockedBody")}</span></div></section>;
}

export function Phase15Capture({ state, t }: { state: Phase15CaptureState; t: T }) {
  const stateTone = tone(state);
  const mascot = state.startsWith("08-") || state.startsWith("10-") || state.startsWith("11-") ? mascotAssets["yak-warning-stop"] : state.startsWith("05-") || state.startsWith("09-") ? mascotAssets["yak-success-check"] : mascotAssets["yak-security-shield"];
  return <div className={`phase15-surface phase15-${stateTone}`} data-phase15-fixture="mellowyak.phase15.screenshots.v1" data-phase15-state={state} data-ready="true">
    <header className="phase15-heading"><div><span className="eyebrow">{t("phase15.eyebrow")}</span><h1>{t(`phase15.screen.${state}.title`)}</h1><p>{t(`phase15.screen.${state}.body`)}</p></div><img src={mascot.src} alt={t(mascot.altKey)} /></header>
    <div className="phase15-state"><span>{t("phase15.currentState")}</span><strong>{t(`phase15.state.${currentState(state)}`)}</strong><code dir="ltr">{currentState(state)}</code></div>
    {isRepair(state) ? <RepairSurface state={state} t={t} /> : isReceipt(state) ? <ReceiptSurface state={state} t={t} /> : state.startsWith("11-") ? <PackageSurface t={t} /> : <BaselineSurface state={state} t={t} />}
    <div className="phase15-bottom"><section className="panel"><h2>{t("phase15.knownFacts")}</h2><ul><li>{t("phase15.fact.local")}</li><li>{t("phase15.fact.immutable")}</li><li>{t("phase15.fact.explicit")}</li></ul></section><section className="panel"><h2>{t("phase15.unknowns")}</h2><ul><li>{t("phase15.unknown.physical")}</li><li>{t("phase15.unknown.distribution")}</li></ul></section></div>
  </div>;
}
