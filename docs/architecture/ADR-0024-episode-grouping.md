# ADR-0024 — Settle-window Episode grouping

Status: Accepted — 2026-08-24

## Context

Editors, formatters, package managers, and coding tools often emit many filesystem writes for one
meaningful edit. One snapshot per write would create noise and unnecessary hashing. Conversely,
waiting indefinitely for a quiet tree would prevent useful history from stabilizing.

## Decision

Phase 7 groups project-scoped file hints into a `source_episode`. The grouping service uses a bounded
queue, normalized relative paths, event coalescing, ignore rules, a debounce/settle window, and a
maximum Episode duration. Watcher events are hints; a stable capture is the authoritative resulting
source state.

An Episode records:

- start/end and state;
- bounded event count;
- added, modified, deleted, and renamed paths;
- dependency and relevant runtime events;
- base and resulting snapshot IDs;
- an optional Git anchor;
- exact failure code when stabilization or capture fails.

A stable Episode creates at most one normal snapshot. An unchanged resulting manifest reuses the
previous snapshot while preserving the Episode record. The resulting snapshot maps back into the
existing Change, Impact, Protection Plan, verification, regression, and gate architecture; Episodes
do not create a second change engine.

After stabilization, Impact-based probe selection may run as bounded background work. A file event,
Episode, or impact path is only a `WATCH` signal. None is evidence that behavior regressed.

The grouping service is fail-open. Queue pressure may drop low-value duplicate runtime events, but
must not block editor writes. A watcher, adapter, selection, or snapshot failure is reported and
source monitoring can fall back to reconciliation/polling without crashing the desktop app.

## Consequences

Episode boundaries are deterministic operational grouping, not authorship attribution. MellowYak
does not infer which person, model, editor, or prompt caused an Episode. Very long or continuously
changing operations may be split at the maximum duration, which is preferable to an unbounded open
Episode.
