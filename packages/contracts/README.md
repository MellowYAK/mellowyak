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

All routes remain loopback-authenticated and project-scoped. The contract has no source-content response, connector delivery, test execution, behavior verification or Completion Gate endpoint.
