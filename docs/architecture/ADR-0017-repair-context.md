# ADR-0017 — Deterministic model-neutral Repair Context

Status: Accepted — 2026-08-24

## Decision

`mellowyak.repair_context.v1` is derived locally from a supported regression. It carries exact source identity, KEEP, RESTORE, behavior/baseline/current evidence references, failed assertions, impact path, relative relevant files, related tests, receipt reference, unknown/stale boundaries, required rechecks, forbidden assumptions, budget, generation time, and a canonical SHA-256 digest.

No source content is included by default. Secret-shaped values are redacted. JSON is limited to 256 KiB, clipboard delivery is explicit and local, and saved files remain beneath the MellowYak data root. No connector or model call exists.
