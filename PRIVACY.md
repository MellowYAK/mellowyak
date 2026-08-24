# Privacy

## Current implemented behavior (Phase 3)

MellowYak runs a desktop shell and local engine on the same machine. It stores installation settings, selected project paths, Git/scan metadata, relationship facts, Change identities, impact results, Context Receipts, non-verified behavior candidates and local audit events in SQLite. It does not store source contents in the Phase 3 graph, impact or receipt tables. Evidence folders exist, but screenshots, traces, videos, runtime evidence and regression evidence are not collected.

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

Source code, Git history, project maps, future protected behaviors, screenshots, traces, videos, evidence, regression history and repair context must stay local by default. Data may leave only through a future connector explicitly enabled by the user, with a visible destination and consent. No connector is implemented in Phase 3.
