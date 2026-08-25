# ADR-0040: packaged engine startup strategy on macOS

Status: accepted on 2026-08-25.

## Decision

Intel macOS packages the PyInstaller engine as a private one-directory resource. Tauri starts the
resource executable directly, reads the same memory-only loopback handshake and supervises up to
three unexpected exits. Explicit quit disables restart and terminates the child. Windows and Linux
retain their existing one-file sidecar path.

## Reason

The Phase 10 one-file engine extracted its runtime on every launch. On this Intel host it measured a
19.07 second median handshake. The one-directory build measured 2.02 seconds median after its first
cold-cache launch. Both minimum, median and maximum remain in the evidence because OS scanning can
still dominate the first run.
