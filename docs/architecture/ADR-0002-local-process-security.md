# ADR-0002: Local process security

- Status: Accepted
- Date: 2026-08-23

## Decision

The desktop shell creates 256 bits of operating-system randomness for every launch, starts the engine as its child, passes the token and parent PID only in the child environment, and accepts a minimal stdout handshake. The engine binds a dynamically allocated port on `127.0.0.1` (with `::1` allowed by policy), rejects `0.0.0.0`, and requires `Authorization: Bearer` on every application endpoint. Origin middleware and CORS allow only Tauri/local development origins.

The token remains only in Rust and JavaScript process memory. It is not written to SQLite, localStorage, configuration, logs or crash files. The shell kills its child on exit; the engine also supervises the parent PID. Logs are structured, rotating and redact token/path values. Phase 1 has no outbound client, cloud URL, account endpoint or telemetry uploader.

## Future connector boundary

Credentials for explicitly enabled connectors must use operating-system credential storage, never the application database or logs. A connector must declare destination and data classes, receive explicit consent, and be revocable. Source, Git history, maps, evidence and repair context may leave only through such a user-enabled connector. Connector permission does not authorize an execution arm.

## Consequences

Loopback is still an untrusted boundary: authentication and origin validation remain mandatory. Process environment inheritance and frontend memory require careful diagnostics and crash handling. A future remote/team mode needs a separate ADR and threat model; it may not weaken this default.
