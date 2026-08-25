# Product Truth and Technical Preview troubleshooting

## Home or Project Overview looks incomplete

Refresh the exact project and inspect limitations. A partial response must keep missing facts unknown;
do not infer health from an absent check or regression. Open Diagnostics if the local engine, database,
source identity or runtime is unavailable.

## Status says no confirmed issue

This means no confirmed regression exists in the available comparable evidence. It does not mean all
behaviors are covered. Review skipped, unknown, stale and unavailable checks before completion.

## App is still running after the window closes

This is expected close-to-tray behavior. Use the tray's Show action to reopen it or
Quit to terminate MellowYak and its owned engine.

## Project is disconnected

Use Reconnect if the same project identity exists at a reachable location. Use
Relocate only to update MellowYak's stored location. Neither action moves source.
If identity differs, stop and select the correct project; never force the mismatch.

## Diagnostics reports storage failure

Stop source-writing operations. Copy the redacted diagnostic summary, retain the
application-data directory and any pending journal, and do not delete recovery state.
Use the support bundle only after inspecting it for private data.

## Apply is blocked

Common causes are stale source identity, changed path hashes, expired/used
confirmation nonce, failed candidate validation, or pending recovery. Revalidate the
candidate against the exact current source. Never bypass the Safety Snapshot,
journal, deliberate confirmation, or fresh live verification.

## Updater rejects an artifact

Do not bypass signature verification. Wrong-key, tampered, incomplete, lower-version,
or malformed metadata should be rejected. Keep the current installation and obtain a
same-platform artifact from the official immutable release once public distribution
is enabled.

## macOS refuses to open the local build

The Phase 9 local artifact is unsigned and unnotarized, so Gatekeeper rejection is an
expected limitation. This report does not recommend disabling platform protection.
Use a future signed/notarized release for ordinary installation.

## Notification did not open context

The in-app alert remains authoritative. Stale, forged, unavailable, or malformed
native routes are intentionally rejected. Open MellowYak and navigate to the local
project/episode manually.

## Support bundle includes unexpected private material

Do not share it. Preserve the local file for investigation, record the application
version and reproduction using synthetic data where possible, and report the issue
privately according to `SECURITY.md`.
