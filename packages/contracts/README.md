# API contract

`openapi.json` is generated from the FastAPI application with:

```bash
engine/.venv/bin/python scripts/export_openapi.py
cd apps/desktop && npm run contract:generate
```

The generated TypeScript file is intentionally ignored and must be regenerated before frontend tests or builds. Python response models remain the authoritative response schema.

Phase 3 contract groups include:

- stable current Change and optional local task intent;
- bounded reverse-impact analysis, paths and unknown/stale boundaries;
- deterministic `mellowyak.context_receipt.v1` generation and retrieval;
- non-verified behavior-candidate actions;
- Impact Explorer search with incoming/outgoing provenance and scan revision.

Phase 4 contract groups include:

- protected behavior drafts, immutable versions, archive and baseline revoke;
- project runtime configurations and explicit runtime testing;
- browser capture start/list/detail/pause/resume/stop/cancel;
- mandatory capture review and explicit baseline acceptance;
- evidence artifact/bundle listing, content retrieval, local opening and reference-safe deletion.

Phase 5 contract groups include:

- source-bound Protection Plan create/read;
- required selective verification run/read/cancel/retry and explicit human result;
- assertion results and separate CURRENT_VERIFICATION evidence bundles;
- immutable Completion Gate evaluation/read;
- regression list/detail and deterministic Repair Context create/read/copy/save-local.

All routes remain loopback-authenticated and project-scoped. The contract has no source-content response, connector delivery, model call, arbitrary local-command execution, automatic repair, external gate enforcement, or upload endpoint.
