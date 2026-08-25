# ADR-0035: Product-truth aggregates and daily-workflow surfaces

Status: accepted for Phase 10
Date: 2026-08-25

## Context

The Phase 1–9 engine already persists project identity, Episodes, snapshots, protected
behaviors, checks, regression findings, repair candidates, Apply transactions,
recovery state, alerts, diagnostics and package evidence. The desktop interface still
required users to reconstruct the current state by visiting those technical entities
individually. A product-facing summary must not introduce a competing source of truth
or claim more certainty than the stored evidence supports.

## Decision

- Keep the existing normalized Phase 1–9 records authoritative.
- Add read-only, project-scoped aggregation endpoints for Home, Project Overview,
  Activity, Episode Detail, Regression Detail and Diagnostics.
- Derive every status from persisted facts. Return explicit limitations and unknowns;
  never translate missing evidence into a successful result.
- Keep Project Overview as the daily center. Link activity entities to their exact
  Episode, check, regression or Apply transaction.
- Treat a confirmed regression or recovery requirement as attention. Treat missing
  protected behavior, runtime or check coverage as a visible limitation.
- Keep friendly explanations and technical evidence together through progressive
  disclosure rather than separate, contradictory product modes.
- Add no Phase 10 database migration: the aggregate layer is computed from the
  existing schema and introduces no duplicate persisted state.
- Use translation keys for every UI string and preserve exact English/Hebrew key
  parity with RTL at the document root for Hebrew.

## Consequences

The UI can answer what needs attention, what changed, what was checked and what remains
unknown without inventing state. Queries are intentionally bounded and project
isolated. Future schema changes must extend the authoritative evidence model first;
the aggregate layer may then expose the new facts.
