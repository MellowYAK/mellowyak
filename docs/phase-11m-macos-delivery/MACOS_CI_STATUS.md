# macOS CI status

Status: `WORKFLOW_CONFIGURED_NOT_REMOTE_EXECUTED`.

`.github/workflows/macos-acceptance.yml` has separate Intel and arm64 jobs, pinned Python/Node/Rust
inputs, immutable Phase 10 ancestry verification, source gates, architecture-correct resource
staging, package validation, checksums and CI-only artifact upload. It never publishes a release or
updates the production updater channel. Signing variables are protected GitHub secrets only.
