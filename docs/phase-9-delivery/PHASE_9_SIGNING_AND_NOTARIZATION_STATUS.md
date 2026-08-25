# Phase 9 signing and notarization status

## Current result

**UNSIGNED_AND_UNNOTARIZED — NOT A PUBLIC RELEASE ARTIFACT**

The Phase 9 Intel macOS application and DMG are local Technical Preview evidence.
`codesign` reports that the executable is not signed, and `spctl` rejects the bundle
because no usable Developer ID signature exists. No notarization submission,
acceptance record, or staple exists. This is expected and is recorded as a release
blocker rather than converted into a success claim.

## Prepared configuration

- Hardened Runtime release configuration is present.
- A minimal entitlements file is present without broad speculative exceptions.
- Workflow surfaces are prepared for secret-provided platform credentials.
- The updater public key remains committed; the private updater signing key is never
  committed, printed, copied into the app, or written by the local validation.
- Artifact inventory/manifests are configured for reproducibility and review.

## Required before public macOS distribution

1. supply Developer ID Application credentials through protected CI secrets;
2. build the exact tagged commit with Hardened Runtime;
3. verify every nested executable and sidecar signature;
4. submit with `notarytool` and retain successful service evidence;
5. staple and validate both the application and DMG;
6. run Gatekeeper assessment on a clean machine;
7. execute the installed Technical Preview acceptance suite;
8. publish only the artifacts and updater metadata from that same signed commit.

Windows requires Authenticode signing and timestamp validation. Linux distribution
requires native artifact/runtime inspection and the selected publication trust
policy. None is claimed by this local macOS run.
