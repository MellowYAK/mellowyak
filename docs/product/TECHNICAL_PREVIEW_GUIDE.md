# Technical Preview guide

MellowYak `0.2.0-preview.1` is ready for local Intel macOS operator review. It is not
a signed public release. Start with the synthetic Demo Lab or a disposable project
copy and follow the delivery folder's Real Project Acceptance Guide before selecting
important source.

## First run

The first-run flow explains local behavior and privacy, lets the user select a
project or Demo Lab, and stores completion locally. Existing upgraded installations
skip it. The flow can be replayed from Technical Preview settings.

## Background behavior

Closing the window keeps MellowYak available through the tray. The tray summarizes
monitoring and attention states without source or full paths. Show reopens the UI;
Quit stops the desktop and its owned engine. A second launch reuses the existing
instance.

## Disconnected source

Missing roots remain visible with history. Reconnect selects the same identity at a
reachable location. Relocate changes MellowYak's stored root only; it never moves
source. Identity mismatch stops both flows.

## Diagnostics and support

Diagnostics checks schema, storage, runtime, package, and updater state. A support
bundle is a redacted local export; inspect it before sharing. It must not contain
source/evidence bytes, credentials, tokens, cookies, private keys, or full home paths.

## Updates

Signature enforcement is mandatory. The current local package is unsigned and the
production update path has not yet been runtime verified. Do not bypass verification
or treat the local updater fixture as a public release service.

## Activity modes

Active favors responsiveness, Balanced is the normal setting, and Battery Saver
reduces background refresh/animation. All modes retain identity, recovery, integrity,
and explicit Apply safeguards.
