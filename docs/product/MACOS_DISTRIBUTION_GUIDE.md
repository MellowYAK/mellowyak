# macOS distribution guide

The local Intel package is suitable for development acceptance only. Phase 11M performs ad-hoc
inside-bundle structural signing with Hardened Runtime and minimal entitlements, verifies nested code
structure, signs the DMG, mounts it read-only, compares the contained executable hash and detaches it.

Public distribution requires protected Developer ID Application credentials, correct inside-out
signing of every nested executable/framework/browser helper, `notarytool` acceptance, stapling and a
successful Gatekeeper assessment. Secrets must come only from a protected keychain or CI secret
store, must never be printed, and must never enter the repository.

No real distribution credential was found during Phase 11M. Ad-hoc signing is not Developer ID
signing, notarization is absent, and public distribution remains blocked.
