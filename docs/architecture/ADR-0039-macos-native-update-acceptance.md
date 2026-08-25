# ADR-0039: macOS native update acceptance

Status: accepted for Intel local acceptance on 2026-08-25.

## Decision

The production updater remains Tauri's signature-enforced HTTPS updater. Local acceptance uses two
disposable copies of the actual `.app` bundle, lower and higher test-only versions, the real macOS
`.app.tar.gz` shape, an ephemeral private key, detached signature and a loopback-only server. It must
reject tampering, a wrong key, an incomplete response and a downgrade while preserving external app
data, settings and synthetic source.

The fixture never changes the production endpoint or public key and never persists the private key.
A passing fixture is not a claim that a public GitHub Release or production update channel ran.
