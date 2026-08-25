# Demo Lab walkthrough

Demo Lab is an opt-in, local-only synthetic checkout project. It is disposable and guarded by an
explicit marker so Demo actions cannot target a real registered project.

1. Create the demo in an empty folder.
2. Establish the initial Save Point and `Checkout completes successfully` known-good Probe.
3. Inject a harmless file-only change and observe WATCH.
4. Inject the controlled regression and reproduce CONFIRMED.
5. Create a Repair Workspace and the bad candidate; observe VALIDATION_FAILED and disabled Apply.
6. Create the valid candidate; observe VALIDATED.
7. Change the live fixture after validation; observe stale-source block with zero writes.
8. Recreate/validate, deliberately confirm Apply, observe fresh safety snapshot, journal, new live
   identity, fresh live checks, and COMMITTED.
9. Reset and simulate post-Apply failure; observe automatic byte-identical ROLLED_BACK.
10. Run incomplete-journal recovery; observe safe cancellation/rollback or RECOVERY_REQUIRED.
11. Switch to Hebrew to review validated, confirmation, and rollback RTL states.
12. Reset the demo to remove synthetic scenario state.

The Demo Lab never proves Windows/Linux/Apple Silicon behavior, signing, notarization, production
deployment, external database isolation, or a real project's test coverage.
