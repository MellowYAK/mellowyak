# Phase 4 UI review map

No new screenshots are committed for Phase 4. This map identifies every new surface for a fast manual design review without placing local user desktop captures in the public repository.

| Surface | What is visible | Main actions | State claim |
|---|---|---|---|
| Protected Behaviors list | title, lifecycle state, current version, baseline state | create draft, open behavior, archive | `VERIFIED_WORKING` |
| Behavior detail | immutable version history, description, expected outcome, source/runtime links | add version, archive, revoke baseline | `VERIFIED_WORKING` |
| Runtime configuration | command, working directory, loopback entry URL, readiness state | save, test runtime | `VERIFIED_WORKING` |
| Capture controls | current capture state and bounded runtime information | start, pause, resume, stop, cancel | `VERIFIED_WORKING` |
| Capture review | ordered steps, editable labels, include/exclude choices, observations, screenshots | curate, delete review artifact, submit review | `VERIFIED_WORKING` |
| Evidence details | bundle lineage, artifact type, byte size, SHA-256, source revision | view content, open local location, delete when safe | `VERIFIED_WORKING` |
| Last Known Good | accepted baseline, behavior version, evidence bundle, revision identity | accept after review, revoke | `VERIFIED_WORKING` |
| Change detail links | exact known behavior links for changed FILE paths | open linked behavior | `IMPLEMENTED_NOT_RUNTIME_VERIFIED` |
| Hebrew variants | the same surfaces translated and mirrored | all core actions | `VERIFIED_WORKING` |

Design review should focus on density in Capture Review, the distinction between historical evidence and fresh verification, long artifact hashes, lifecycle-state contrast, and Hebrew wrapping. All visible copy must remain translation-key driven.
