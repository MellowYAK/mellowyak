# Disposable-copy real-project readiness guide

Do not point Phase 11M test-only actions at a private working tree. A later operator-controlled run
must begin from a byte-verified disposable copy with credentials and ignored data removed.

1. Record source digest, Git state, filesystem type, runtime commands and expected known-good checks.
2. Create a separate MellowYak data root and confirm loopback binding.
3. Add only the disposable copy through normal product UI; never add the original.
4. Complete Runtime Wizard and validate each profile without external credentials.
5. Establish Save Point and Known Good only from actual passing evidence.
6. Make a harmless controlled change and confirm WATCH is not called a regression.
7. Run impacted checks; require comparable repeated failure before CONFIRMED.
8. Validate a candidate only in its Repair Workspace.
9. Before Apply, compare live-source identity, require explicit confirmation and preserve an unrelated
   sentinel.
10. Verify Safety Snapshot, journal-before-write, fresh post-check and byte-identical rollback.
11. Explicitly Quit and verify zero owned processes.

Stop on any source mismatch, unresolved symlink/alias, locked file, unbounded file or Recovery Required
state. This guide does not authorize connecting a real project during Phase 11M.
