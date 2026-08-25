# Validated Repair Guide

## Safe flow

1. Open a confirmed Regression and create a Repair Workspace.
2. Edit only the isolated working copy with an editor, script, or external tool.
3. Create or refresh the Candidate Repair and review every operation and limitation.
4. Run Candidate Validation. The original failed Probe runs first; every required check must pass.
5. Select **Prepare Apply**. If the live source changed, Apply stops before any write.
6. Review the exact paths, Safety Snapshot, post-Apply checks, rollback behavior, and unknowns.
7. Deliberately confirm the one-time Apply transaction.
8. Wait for fresh live verification. Workspace PASS evidence is never reused.

`Applied and verified` means the fresh live checks passed for the current known scope. `Restored safely` means only transaction-affected paths were returned byte-for-byte to the pre-Apply Safety Snapshot. `Recovery required` means MellowYak stopped further writes and produced local diagnostics.

MellowYak does not generate code, infer intent with a model, merge a stale candidate, replace Last Known Good, or automatically create a new milestone.
