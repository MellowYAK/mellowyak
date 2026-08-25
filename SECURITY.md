# Security policy

## Phase 9 Technical Preview boundary

Reconnect and relocate require matching stable project identity and change only local metadata; they
never move or write source. Tray content contains privacy-safe aliases/status, and notification
activation accepts only allowlisted route kinds plus existing local identifiers. Forged, stale,
malformed, unavailable, and cross-project routes fail closed. A second application launch reuses the
existing process; close-to-tray retains supervision; explicit Quit terminates owned children.

Diagnostics and support bundles are bounded/redacted and must exclude source/evidence bytes, full
home paths, tokens, cookies, credentials, private keys, and arbitrary environment data. Updater
signature verification remains mandatory. The Phase 9 loopback signer is disposable, uses an
ephemeral unpersisted key, and cannot change production configuration. Activity modes may reduce
refresh or animation but cannot bypass storage integrity, project/source identity, recovery,
verification, or Apply safeguards.

The local Intel macOS package is unsigned and unnotarized and has no public publisher trust. Other
platform workflows are not runtime evidence. Public release remains blocked on native build/install,
signing/notarization, updater, and operator acceptance evidence.

## Phase 8 validated repair and transaction boundary

Candidate scanning rejects traversal, absolute/noncanonical paths, symlink escape, hard links,
special files, case collisions, sensitive/provider-private paths, excessive files, and excessive
bytes. Validation is workspace-confined, no-shell, sanitized, time/output bounded, and loopback-only
by default. Completed validation and Apply records are immutable and exact-identity-bound.

Live writes require a validated candidate, fresh source and per-path hash preflight, explicit
deliberate confirmation, and a short-lived one-time nonce bound to transaction, project, candidate,
and source manifest. A fresh pinned Safety Snapshot and durable mode-0600 fsynced journal precede the
first write. Atomic same-filesystem replacement is used where supported; deletes run last. A write or
fresh live-verification failure triggers transaction-scoped rollback. Unprovable byte identity stops
writes and creates a redacted Recovery Bundle. No general historical restore, automatic merge,
automatic Apply, model/provider access, or remote upload is present.

## Phase 7 runtime, snapshot, probe, and workspace boundary

Runtime and Probe execution is explicit, project-scoped, and represented as an executable plus argv.
The engine never invokes a shell, rejects shell executables/command strings, confines working
directories to the selected project, uses a minimal allow-listed environment, bounds time/output,
supports cancellation, and cleans up owned child processes. It does not inspect arbitrary processes,
read process memory, attach system-wide, or persist a complete environment. Runtime adapter failure
is fail-open and cannot stop source monitoring or editor writes.

The source snapshot store resolves beneath the MellowYak application-data root. Capture remains
confined to the project root; escaping symlinks, MellowYak-owned data, sensitive files,
provider-private directories, ignored artifacts, and oversized objects are excluded/reported.
Objects and canonical manifests use atomic local publication and SHA-256 verification. SQLite stores
metadata/references rather than source blobs. Reference-safe retention cannot collect an object still
reachable from retained snapshots, milestones, baselines, incidents, or Repair Workspaces.

Browser/API probes default to exact loopback targets. External network access, authorization/cookie
headers, and secret fields are denied by the Phase 7 policy. CLI/Test/Process probes require approval
and no-shell argv. One source change or one failed run cannot become `CONFIRMED`; comparable accepted
prior PASS plus reproducible current FAIL (or the existing supported regression engine) is required.

Snapshot materialization and Repair Workspace creation use new confined paths outside live source and
never apply changes back. Cross-project access is rejected. Workspace metadata is bounded/redacted
and uses relative references. No coding-agent SDK, prompt reader, provider credential access, cloud
snapshot/evidence upload, analytics SDK, account, deployment, or rollback path is added.

## Phase 5 verification boundary

Protection Plans and results are project-scoped and bound to Change ID, HEAD, worktree fingerprint, scan revision, impact analysis, behavior version, and baseline. Browser Replay uses a new context, enforces one configured loopback HTTP origin, blocks downloads and external navigation, stores no headers/bodies/cookies/storage/input values, and closes browser resources. Automatic PASS requires deterministic assertions and intact CURRENT_VERIFICATION evidence. Stale, unavailable, unresolved, unsupported, timed-out, or crashed execution is never PASS and cannot become a regression claim. Repair Context remains below the local data root, uses relative paths, excludes source content, and is never transmitted by the engine.

## Phase 4 browser boundary

The browser arm starts only after explicit action, accepts only exact explicit-port `http://127.0.0.1` or `http://localhost` origins, aborts other origins, disables downloads and persistent profiles, and is terminated with its engine owner. Evidence objects are project-scoped, size-bounded, content-addressed, atomically written, symlink/traversal checked, and hash-verified. API access remains loopback-only with the per-launch bearer token. Trace is disabled unless separately package-verified; video is disabled by default.

MellowYak Phase 4 is a local foundation, not a production-security certification.

## Reporting

Do not publish a suspected vulnerability or private project evidence in a public issue. Use GitHub's private vulnerability reporting for this repository when available. Include version, platform, reproduction steps and impact; omit real source code, credentials and personal evidence.

## Implemented boundary

- The engine accepts loopback hosts only and selects a dynamic port.
- Every non-handshake API requires a random per-launch Bearer token.
- The token is process-memory-only and is redacted from application logs.
- Origin access is restricted to the desktop shell/development origins.
- The engine is supervised and stopped with its parent desktop process.
- Project/change/impact APIs are scoped by project identity and reject cross-project records.
- Source traversal is confined to the selected repository; ignored, sensitive, binary, oversized and escaping-symlink inputs are excluded or reported.
- Reverse impact uses bounded deterministic traversal. Unknown and stale edges terminate authoritative traversal.
- Context Receipts persist metadata only, include zero source bytes, exclude sensitive content and open no network connection.
- Behavior candidates are explicitly unverified and not protected.
- Desktop setup starts the packaged engine asynchronously. Slow cold starts return `ENGINE_STARTING` to the UI instead of blocking AppKit setup or aborting the desktop process.
- The desktop updater accepts metadata only from the HTTPS MellowYak GitHub Releases endpoint and refuses update bundles that do not match the embedded public signing key. The private updater key is prohibited from source history and build logs.
- Phase 8 has no remote account, cloud synchronization, telemetry uploader, model call, connector, or
  external gate enforcement. Approved runtime/CLI/Test execution is bounded, argv-only, no-shell, and
  project-confined; it is not arbitrary shell execution. Browser/API probes remain restricted to
  approved loopback runtimes. The release update check remains the only configured non-loopback
  product request.

Local development packages remain unsigned and unnotarized and are not release artifacts. The updater minisign key does not replace required macOS notarization or Windows code signing. A public production release remains blocked until the platform signing credentials and updater private key are configured as repository secrets. Future connectors, execution arms and team services require separate threat models and explicit user consent.

## Prohibited legacy sources

APC `_codex_read.php`, `model_context.php`, and installation-wide authorization semantics from `api/model.php` and `api/ingest.php` are security blocked. They must not be introduced into MellowYak.
