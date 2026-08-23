# Privacy

## Current implemented behavior (Phase 1)

MellowYak runs a desktop shell and local engine on the same machine. It stores an installation identity, application settings, engine-run records and local audit events in SQLite. Evidence folders are created but no project source, Git history, screenshot, trace, video or regression evidence is collected in Phase 1.

There is no account, cloud synchronization, analytics endpoint, telemetry upload or configured MellowYak remote API. Startup performs no outbound network operation. The local API binds to loopback and requires a per-launch token that is not persisted.

Local data is placed under the platform application-data location:

- macOS: `~/Library/Application Support/MellowYak`
- Windows: `%LOCALAPPDATA%\MellowYak`
- Linux: `$XDG_DATA_HOME/mellowyak` or `~/.local/share/mellowyak`

Opening the data folder is a local operating-system action. Uninstalling the app may not delete that folder; users control its retention and backup.

## Future boundary

Source code, Git history, project maps, protected behaviors, screenshots, traces, videos, evidence, regression history and repair context must stay local by default. Data may leave only through a connector explicitly enabled by the user, with a visible destination and consent. No connector is implemented in Phase 1.
