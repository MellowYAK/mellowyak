# Phase 10 privacy and security review

## Data and network boundary

Product Truth adds read-only local aggregation. It does not add source upload, cloud sync, analytics,
account, model/provider SDK, prompt/history access, APC runtime access or a new non-loopback endpoint.
Packaged Phase 8–10 validation used disposable synthetic data, reported no external product network
and touched no real project.

## Isolation

Home is installation-scoped but returns privacy-safe aliases and bounded facts. Project Overview,
Activity, Episode and Regression Detail require exact project ownership; foreign entity IDs are
rejected. Technical detail is opt-in. Diagnostics redacts the bearer token and reports the data root
as a safe alias.

## Source writes

Product Truth endpoints are read-only. Candidate generation/validation stays inside a confined Repair
Workspace. Live writes still require validated exact identity, fresh path hashes, deliberate one-time
confirmation, a pinned Safety Snapshot and durable fsynced journal. Failed live verification performs
transaction-scoped byte-checked rollback; uncertain recovery stops writes.

## Support and package review

Support bundles exclude source/evidence bytes, full home paths, tokens, cookies, credentials, private
keys, snapshots and repair content and have no upload action. The final app scan found no user build
path, supplied password, private-key marker or persisted session-token assignment. The package is
unsigned and unnotarized, so it has no public publisher trust and is not a release candidate.

## Residual risk

Screenshots or support data can still reveal local operational metadata chosen by the user; inspect
before sharing. Production updater network/signature delivery is not runtime accepted. Windows,
Linux and Apple Silicon require native threat/lifecycle evidence. Real-project acceptance remains a
separate explicit operator decision.
