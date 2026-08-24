# Phase 5 UI screens

> Historical Phase 5 map. The current Phase 7 Runtime/Memory/Probe screen contract is documented in
> [`PHASE_7_UI_SCREENS.md`](PHASE_7_UI_SCREENS.md).

The Change Detail surface now contains a translation-key-only Change Cockpit in English and Hebrew RTL.

## Screen map

1. **Changed Files** — current bounded Change identity; it never claims a complete diff cause.
2. **Impact Summary** — shows whether a fresh impact analysis exists.
3. **Protection Plan** — counts REQUIRED, SUGGESTED, SKIPPED, NEEDS_REVIEW, and UNKNOWN items.
4. **Required Checks** — behavior, criticality, verification method, and translated selection semantics.
5. **Suggested Checks** — visible but never run automatically.
6. **Skipped Behaviors** — wording means no current known relation, not unaffected.
7. **Unknown / Stale Boundaries** — unresolved selection boundaries remain visible.
8. **Verification Runner** — run all required, view states/durations, retry, and explicit manual results.
9. **Regression Detail** — supported regression state and exact source identity; no invented root cause.
10. **Repair Context** — create, copy, save local JSON, and open local project files.
11. **Evidence Timeline** — states that Last Known Good and current evidence are separate.
12. **Gate Decision** — local authoritative decision plus translated scope limitation.

Mascots are limited to working, alert, and success contexts. Failure language is direct. All visible product copy and accessible labels resolve through `apps/desktop/src/i18n.ts`; the Hebrew document direction is RTL. The UI does not expose Send to Codex/Claude, connector, automatic repair, or deployment-safety actions.

Automated UI coverage is in `apps/desktop/src/App.test.tsx`. No new screenshots were committed because generated screenshots and test output are excluded from source history; the executable UI and translation-key checks are the authoritative Phase 5 evidence.
