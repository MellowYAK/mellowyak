# Phase 10 UX and product-truth audit

## Information hierarchy

The routine path is now Home → Project Overview → Activity/Episode or exact attention item. Settings
contains preferences; Diagnostics contains support and preview readiness; internal Technical Preview
language no longer replaces daily operational content.

## Truth language

- `No confirmed issue` is evidence-bounded and does not promise full coverage.
- Impact is a reason to verify, not a regression.
- `Validated` means the isolated candidate passed; it does not mean live source changed.
- `Applied and verified` requires a committed transaction and fresh live evidence.
- `Rolled back safely` reports restored transaction paths and byte identity, not a general history
  restore.
- Unknown, stale, unavailable, skipped and limited states remain visible.

## Progressive disclosure

Primary views show status, known facts, limitations and next action. Paths, hashes, IDs, reason codes,
manifests and provenance appear under technical disclosure and remain LTR in Hebrew. Bounded queries
and pagination avoid presenting an unbounded history as a usable screen.

## Interaction and accessibility

First Run uses radio semantics and disables Continue until a choice exists. Operational progress uses
status/live semantics. Focus order follows the visible workflow. Controls retain visible focus, text
status does not rely on color, narrow layouts reflow to one column, reduced motion is supported and
Hebrew renders RTL. All visible copy and accessible labels come from translation keys.

## Visual evidence

Thirty-six states cover First Run, Home, Overview, Activity, Episode, checks, behaviors, regression,
repair, candidate validation, Apply, rollback, disconnected projects, Diagnostics, Self-Test, support,
updater, modes, tray preview and four Hebrew screens. The tray preview is test-only and explicitly
classified; native tray behavior is evidenced separately through lifecycle checks.
