# Privacy

## Phase 10 Product Truth and daily workflow

Phase 10 adds read-only local aggregates for Home, Project Overview, Activity/Episode Detail,
Regression Detail and Diagnostics. These responses join existing local metadata and remain bounded,
project-scoped and privacy-safe; detailed paths, hashes, IDs and provenance stay behind explicit
technical disclosure. No source bytes are added to SQLite or uploaded.

The 36 delivered screenshots and packaged validators use deterministic synthetic or disposable data.
No registered real project, APC data, user database, provider history, cloud service, analytics
endpoint or model API was used. Diagnostics continues to alias the data root, hides bearer tokens and
reports no outbound product network. Support bundles remain local, bounded and review-before-share.

Same-source platform tooling and artifact manifests add no telemetry. Windows, Linux and Apple
Silicon workflow configuration is not runtime evidence and does not change the local data contract.

## Phase 9 Technical Preview lifecycle and support data

Phase 9 stores onboarding completion, local project-location history, diagnostic run summaries,
support-bundle records, notification activation results, update/package validation summaries, and
activity preferences beneath the platform application-data root. Reconnect and relocate retain only
local identity/location metadata and never move, copy, delete, or edit source. Native tray and
notification payloads use local stable identifiers and translated status aliases, not full paths,
source, evidence, credentials, or tokens.

Diagnostics and support exports are bounded and redacted. They exclude source/evidence bytes,
cookies, authorization values, provider credentials, private signing keys, full home paths, complete
environment dumps, user databases, and repair/snapshot content. The user creates the bundle locally
and must inspect it before an explicit share; MellowYak has no support upload service.

The production updater's ordinary HTTPS metadata check remains the only configured non-loopback
product request. Phase 9's signer validation uses disposable loopback metadata and an ephemeral
private key, makes no external request, persists no key, and does not alter production configuration.
Packaged acceptance used isolated synthetic data and no real project. Phase 9 adds no account, cloud
sync, analytics/usage uploader, model/provider access, APC dependency, or automatic source action.

## Phase 8 repair, Apply, recovery, and synthetic diagnostics

Repair candidate records contain relative paths, operations, hashes, sizes, modes, classification,
eligibility, warnings, and exact identities; source contents remain in the isolated Repair Workspace
or local content-addressed store and never enter SQLite. Workspace validation uses a sanitized
environment, bounded evidence, and no shell or external egress by default. Its PASS evidence remains
separate from fresh live-project verification evidence.

Apply journals, Safety Snapshots, rollback records, and Recovery Bundles stay beneath the local
application-data root. Bundles redact project/data roots and exclude sensitive/provider-private paths.
Portable Repair Packages contain only files explicitly selected by the user, use relative references,
and are never uploaded. Demo Lab uses public synthetic source; Product Self-Test uses a disposable
temporary fixture and removes it. Neither can select or mutate a real project through its test-only
actions. Phase 8 adds no model call, prompt/history reader, provider credential access, connector,
analytics, account, cloud sync, source/evidence/patch upload, or automatic Apply.

## Phase 7 Runtime Profiles, Save Points, and Probes

Phase 7 adds local source snapshots, but source contents still do not enter SQLite. Eligible file
bytes are stored as project-scoped SHA-256 objects beneath the MellowYak application-data root,
outside the live project; deterministic manifests and SQLite records contain relative paths, hashes,
sizes, modes, references, exclusions, and identities. Unchanged content is reused. Retention defaults
to 30 days and a 5 GiB per-project soft cap, both configurable; referenced/pinned content is protected.

Capture respects ignore rules and excludes sensitive files, provider-private directories, oversized
content, MellowYak-owned data, and unsafe symlinks. MellowYak does not read provider prompt histories,
conversations, browser login state, Keychain credentials, SSH keys, or provider tokens. A Save Point
represents only included content and is not a cloud backup.

Runtime Profiles store executable references, argv arrays, relative working directories, safe
environment-variable **names**, dependency fingerprints, bounded health/test definitions, approval,
and limitations. They do not persist the full environment, secret values, registry credentials,
authorization headers, cookies, or raw runtime configuration dumps. Sanitized runtime output/events
are bounded.

API/browser Probes default to explicit loopback targets. HTTP authorization/cookie/secret fields are
rejected, and request/response bodies are not retained by default. CLI/Process/Test Probes require
explicit approval and keep only bounded sanitized evidence. Manual Probes are explicitly marked as
human confirmation.

Snapshot materialization and Repair Workspaces remain below the MellowYak data root and never write
to the live source folder. A Repair Workspace contains only included snapshot files plus bounded,
redacted, relative incident/validation metadata. Opening or copying local information is an explicit
user action. Phase 7 adds no account, analytics, source/evidence upload, cloud synchronization,
coding-agent connector, prompt reader, or provider-token monitor.

## Phase 5 verification and repair

Fresh verification runs in a new ephemeral browser context against the approved loopback origin. Current screenshots, bounded action/network metadata, assertion results, regression records, immutable gate decisions, and Repair Context metadata stay under the local MellowYak data root. They do not replace Last Known Good. Repair Context uses relative paths and evidence identifiers, excludes source contents by default, redacts secret-shaped values, is limited to 256 KiB, and leaves the application only through an explicit local clipboard action. No model, connector, source upload, evidence upload, analytics, account, or cloud synchronization was added.

## Phase 4 browser evidence

Browser capture is opt-in and limited to an explicitly approved local HTTP origin. It uses an ephemeral browser context and does not persist cookies, local/session storage, authorization or cookie headers, query values, request/response bodies, or raw input values. Password/secret/token fields are masked before screenshots. Start/final screenshots, action metadata, runtime metadata, hashes, and attestations remain under the platform-native local data root. Screenshots may still contain project or user data, so review and deletion are available before human acceptance. No source or evidence upload was added.

## Earlier local-core behavior

MellowYak runs a desktop shell and local engine on the same machine. It stores installation settings, selected project paths, Git/scan metadata, relationship facts, Change identities, impact results, Context Receipts, non-verified behavior candidates, versioned behaviors, evidence metadata, attestations, and local audit events in SQLite. It does not store source contents or evidence blobs in SQLite. Opt-in Phase 4 captures may store redacted screenshots and bounded runtime evidence as content-addressed local files; trace and video are disabled in the verified default.

There is no account, cloud synchronization, analytics endpoint, telemetry upload, model call, connector, embedding service or configured MellowYak remote API. Scan, reverse-impact analysis and Context Receipt generation require no outbound network operation. The local API binds to loopback and requires a per-launch token that is not persisted.

The packaged desktop performs one HTTPS update check against the public MellowYak GitHub Releases `latest.json` endpoint at startup. This request discloses ordinary network metadata to GitHub and requests only release metadata; it sends no project path, source, Git content, Context Receipt, local token, analytics identifier or evidence. An available update is shown in the interface and is downloaded only after the user selects the translated install action. Every updater bundle must pass the embedded public-key signature check before installation. A failed or blocked update check does not block local product use.

Source scanning reads eligible files inside the selected repository to derive metadata, hashes and conservative relationships. Ignore rules, binary/oversized checks, sensitive-path rules and symlink confinement apply. A Phase 3 Context Receipt contains relative paths and relationship metadata only: its source/snippet budgets are zero, sensitive content is excluded, and `source_uploaded` is false. Copy JSON is an explicit local clipboard action with no connector destination.

The interface supports English and Hebrew from complete local translation dictionaries. English is the base catalog, Hebrew renders RTL, and application-owned UI copy is forbidden outside translation keys. The initial language follows the operating-system/webview locale and can be changed in the app. Language switching makes no network request and stores no browser-local tracking identifier.

Local data is placed under the platform application-data location:

- macOS: `~/Library/Application Support/MellowYak`
- Windows: `%LOCALAPPDATA%\MellowYak`
- Linux: `$XDG_DATA_HOME/mellowyak` or `~/.local/share/mellowyak`

Opening the data folder is a local operating-system action. Uninstalling the app may not delete that folder; users control its retention and backup.

## Future boundary

Source code, Git history, project maps, source snapshots, protected behaviors, screenshots, traces,
videos, evidence, regression history and repair context must stay local by default. Data may leave
only through a future connector explicitly enabled by the user, with a visible destination and
consent. No connector is implemented in Phase 7.
