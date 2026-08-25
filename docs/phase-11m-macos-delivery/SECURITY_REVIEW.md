# Phase 11M security and privacy review

- All product APIs remain bearer-authenticated and loopback-only.
- The updater fixture is loopback-only and uses temporary keys; no private key is persisted.
- Production updater configuration is unchanged.
- The Acceptance Lab requires a permanent synthetic marker and rejects an unmarked directory.
- Package scanning rejects databases, snapshots, evidence, Repair Workspaces, Apply journals,
  Recovery Bundles, support bundles, browser profiles and local home build paths.
- Notification activation carries only validated entity routes and no source/evidence/token data.
- Apply remains explicit and source-bound; rollback remains transaction-scoped.
- Explicit Quit leaves no owned engine process.
- No analytics, account, cloud sync, model/provider SDK, prompt reading or upload path was added.
- No Apple credential, certificate, private key, private project or APC data is included.
