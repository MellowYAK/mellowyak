# Phase 10 Product UX Sources

Accessed: 2026-08-25

Research was intentionally bounded to primary documentation and translated into concrete implementation decisions.

| Source | Official URL | Exact implementation decision |
|---|---|---|
| Apple Human Interface Guidelines — Menus | https://developer.apple.com/design/human-interface-guidelines/menus | Keep the actual native tray/menu compact, use familiar command naming, allow at most one project submenu level, and show current command state without exposing full paths. |
| Apple Human Interface Guidelines — Disclosure Controls | https://developer.apple.com/design/human-interface-guidelines/disclosure-controls | Keep status, evidence summary and next action visible; place paths, hashes, IDs, provenance and deterministic reason codes under a clearly named technical-details disclosure. |
| WAI-ARIA Authoring Practices — Radio Group Pattern | https://www.w3.org/WAI/ARIA/apg/patterns/radio/ | Implement First Run choices as a true single-selection group with checked state, keyboard focus, arrow/Space behavior and a disabled Continue action until selection. |
| WCAG 2.2 Understanding Success Criterion 2.4.3 — Focus Order | https://www.w3.org/WAI/WCAG22/Understanding/focus-order.html | Match DOM/focus order to the operational reading sequence: status, known facts, limitations, next action, then technical detail. |
| WCAG 2.2 Understanding Success Criterion 1.4.10 — Reflow | https://www.w3.org/WAI/WCAG22/Understanding/reflow.html | Support single-column reflow and 200% text zoom without clipped controls or sticky content obscuring focus. |
| Web Content Accessibility Guidelines (WCAG) 2.2 | https://www.w3.org/TR/wcag/ | Preserve logical headings, text alternatives, keyboard access, visible focus, non-color status cues and appropriately named controls throughout operational screens. |
| WCAG Failure F103 — Status Messages | https://www.w3.org/WAI/WCAG22/Techniques/failures/F103 | Announce check, Self-Test, Apply and rollback progress using status/live-region semantics without forcibly moving focus. |
| Tauri 2 — Calling the Frontend from Rust | https://v2.tauri.app/develop/calling-frontend/ | Reuse local Tauri events to invalidate visible operational state instead of creating duplicate refresh intervals. |
| Tauri 2 — System Tray | https://v2.tauri.app/learn/system-tray/ | Keep the real tray implementation native in Rust/Tauri; expose the web rendering only as a clearly labeled deterministic Diagnostics preview. |
| React — `useCallback` | https://react.dev/reference/react/useCallback | Keep translation and refresh callbacks stable so effects do not recreate requests or regress the Phase 9 duplicate-polling fix. |

No repository content, local paths, screenshots, evidence, databases, or user data was sent to any research source.
