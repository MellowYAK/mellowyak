# macOS update guide

Phase 11M uses two disposable copies of the real Intel `.app`: lower
`0.2.0-preview.1` and higher `0.2.0-preview.2-update-test`. The test creates an ephemeral updater key,
serves metadata and the immutable artifact only on loopback, verifies the Tauri signature, performs
an atomic disposable replacement and deletes the temporary root.

The validator must accept the correct signature and reject a changed artifact, a wrong public key,
an interrupted download and a downgrade. Synthetic settings and source digests must remain equal.

This is not a production-channel result. No `latest.json` was published, no production private key
was used, and production updater configuration remains unchanged. Production updater delivery is
therefore `IMPLEMENTED_NOT_RUNTIME_VERIFIED`.
