# ADR-0007: deterministic Context Receipt

- Status: Accepted
- Date: 2026-08-24
- Schema: `mellowyak.context_receipt.v1`

## Context

Coding tools need a compact explanation of a local change and its known relationships. Passing broad repository content would violate the local-first boundary and make selection hard to audit.

## Decision

The Local Engine generates a model-neutral JSON Context Receipt from one current impact analysis. Selection is deterministic and ranked from explicit facts: exact changed paths, graph distance, provenance, test relationships, optional tokenized task-intent overlap and same-directory locality.

The Phase 3 receipt contains metadata only. It has explicit budgets of 20 files, 20 symbols, 12 paths, zero snippets, zero source bytes and 65,536 serialized JSON bytes. Every selected item records why it was selected. Sensitive, stale, unknown, missing and over-budget context is listed with an exclusion reason. Absolute repository paths and source content are excluded. Copying JSON is a user-triggered local clipboard action; no connector or destination is implemented.

## Consequences

- Identical Change, analysis, intent and budget inputs produce the same stored receipt.
- Receipt timestamps are stable because an existing keyed receipt is reused.
- `source_uploaded` is always false in Phase 3.
- No provider tokens, token-savings claims, model calls or outbound network dependency exist.

