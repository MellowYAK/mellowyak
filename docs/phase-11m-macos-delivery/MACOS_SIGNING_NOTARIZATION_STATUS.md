# macOS signing and notarization status

Status: `IMPLEMENTED_NOT_RUNTIME_VERIFIED`.

No Developer ID code-signing identity or complete protected Apple environment was available. The
local `.app` and DMG were ad-hoc signed only to verify structure, Hardened Runtime configuration and
minimal entitlements. `codesign --verify --deep --strict` succeeds, while Gatekeeper acceptance and a
stapled notarization ticket are absent.

Ad-hoc signing is not Developer ID signing. No credential value was printed or persisted, and public
distribution remains blocked.
