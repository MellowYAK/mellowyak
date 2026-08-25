# Product Self-Test

The Product Self-Test runs the repair safety loop in a newly generated temporary fixture. It never selects, reads, or mutates a connected real project.

It records each executed step, status, duration, and bounded error code. Final states are `PASS`, `PARTIAL`, or `FAILED`; an unrun or cancelled step is never reported as PASS. The current test covers snapshots, deduplication, isolated workspace materialization, candidate manifest, invalid/valid validation behavior, Safety Snapshot integrity, durable journal, safe Apply, fresh verification, transaction rollback, byte identity, restart journal loading, source hash integrity, no external network, no owned child process, and cleanup.

The exported JSON report contains no private paths, secrets, source contents, provider state, or uploads. Use it as local diagnostic evidence, not as a platform signing or production-deployment certification.
