# ADR-0036: Project activity timeline

Status: accepted for Phase 10
Date: 2026-08-25

Project activity is a bounded chronological projection of existing Episodes, Probe
runs, regression findings, Apply transactions and project lifecycle events. It does not
persist a parallel event history.

- Results are always filtered by project before pagination.
- The default page is 25 rows; the API caps a page at 50.
- Episode rows summarize file counts, snapshot reuse, executed checks and final signal.
- Exact entity identifiers support navigation to Episode, regression and Apply context.
- File changes alone remain `WATCH`; they do not imply a regression.
- Advanced facts remain nested and bounded. Source contents are not returned.
- Local events invalidate the current view. The UI does not start a second timer per
  translation or render.

This design keeps Home recent activity and Project Activity consistent while preserving
the normalized evidence model as the authority.
