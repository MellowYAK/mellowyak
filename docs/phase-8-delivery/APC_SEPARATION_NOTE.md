# APC separation note

Phase 8 modified only the MellowYak repository. APC remained read-only and was not contacted at
runtime.

No APC source code, server topology, database schema, backup format, PHP endpoint, Bridge transport,
queue, tenant/account system, installation-wide token, provider credential handling, coding-agent
connector, prompt reader, UI asset, or broad source reader was copied.

The only provenance relationship is conceptual: APC's historical evidence, known-good, and
selective-restore experiments helped identify unsafe boundaries. MellowYak independently implements
content-addressed source identities, isolated working copies, candidate manifests, typed local
validation, explicit Apply capabilities, fresh safety snapshots, durable journals, transaction-only
rollback, and local recovery. Arbitrary historical in-place restore remains excluded.
