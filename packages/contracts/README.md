# API contract

`openapi.json` is generated from the FastAPI application with:

```bash
engine/.venv/bin/python scripts/export_openapi.py
cd apps/desktop && npm run contract:generate
```

The generated TypeScript file is intentionally ignored and must be regenerated before frontend tests or builds. Python response models remain the authoritative response schema.
