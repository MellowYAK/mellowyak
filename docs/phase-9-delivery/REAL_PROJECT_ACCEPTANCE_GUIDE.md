# Real-project Technical Preview acceptance guide

This guide is for a human operator after Phase 9. The automated implementation run
did **not** connect a real project. Start with a disposable copy and maintain an
independent backup. Do not use production credentials, customer data, or an
irreplaceable working tree.

## Action labels

- **SAFE LIVE READ:** expected to inspect local metadata/source without writing it.
- **DISPOSABLE COPY:** run only against a throwaway duplicate first.
- **SOURCE WRITE:** can change the selected project.
- **EXPLICIT APPLY:** requires a validated candidate, exact identity, deliberate
  confirmation, Safety Snapshot, durable journal, and fresh post-Apply verification.

## Procedure

1. **DISPOSABLE COPY — Back up:** create and independently verify a backup; duplicate
   the project into a temporary acceptance root.
2. **SAFE LIVE READ — Preflight:** confirm no pending Apply journal, rollback,
   recovery-required state, or incomplete previous acceptance exists.
3. **SAFE LIVE READ — Launch:** start the installed app, record version/platform, and
   confirm Diagnostics reports schema 0009 and storage `PASS`.
4. **SAFE LIVE READ — Add project:** add only the disposable copy; review discovered
   identity, limits, ignored/sensitive exclusions, and unknown coverage.
5. **SAFE LIVE READ — Runtime Wizard:** inspect detected commands; approve only known
   executables/argv and loopback origins. Do not paste shell command strings.
6. **SAFE LIVE READ — Snapshot:** create an initial snapshot and verify manifest,
   object reuse, exclusions, and no change to project files.
7. **SAFE LIVE READ — Episode:** make one harmless operator-controlled change in the
   disposable copy and verify it creates the expected Episode.
8. **SAFE LIVE READ — Milestone:** create a milestone and verify restart/reload keeps
   its source identity and references.
9. **DISPOSABLE COPY — Probe:** run one bounded known-safe Probe and verify child
   cleanup, output bounds, timeout/cancel behavior, and expected evidence.
10. **DISPOSABLE COPY — Baseline:** accept a known PASS as comparable baseline only
    after inspecting its source identity and signals.
11. **DISPOSABLE COPY — Controlled regression:** introduce a reversible failure and
    verify a change alone is insufficient; comparable PASS then reproducible FAIL is
    required.
12. **DISPOSABLE COPY — Decision:** confirm the supported sequence can become
    `CONFIRMED`, while flaky/unknown/unavailable evidence cannot.
13. **DISPOSABLE COPY — Repair Workspace:** create the isolated workspace; verify it
    is outside live source, contains no excluded secret, and leaves live bytes intact.
14. **DISPOSABLE COPY — Candidate validation:** prepare a minimal manual repair in the
    workspace; verify manifest/path/security checks and fresh candidate evidence.
15. **DISPOSABLE COPY — Stale protection:** change live source after validation and
    prove Apply stops before the first write.
16. **EXPLICIT APPLY / SOURCE WRITE — Confirmation:** return to the expected source
    identity, inspect the diff and verification plan, and deliberately issue the
    short-lived one-time confirmation. Never automate this step.
17. **EXPLICIT APPLY / SOURCE WRITE — Live verification:** verify the Safety Snapshot
    and journal precede writes and fresh live verification follows them.
18. **DISPOSABLE COPY — Rollback:** simulate a post-Apply check failure and verify only
    transaction-affected paths return byte-identically; retain evidence.
19. **SAFE LIVE READ — Tray/lifecycle:** verify private-safe project status, close to
    tray, Show, second launch focus, explicit Quit, and no orphan engine.
20. **SAFE LIVE READ — Notifications:** test an in-app alert and, where supported, a
    native activation; verify it opens only the matching allowlisted local context.
21. **DISPOSABLE COPY — Disconnect/reconnect/relocate:** temporarily rename the copy,
    verify disconnected history, reject a different repository, reconnect the same
    identity, and relocate without moving source.
22. **SAFE LIVE READ — Support:** run Diagnostics and create a support bundle; inspect
    every file for source, secrets, paths, cookies, tokens, and evidence before sharing.
23. **DISPOSABLE COPY — Product Self-Test:** run the marker-guarded synthetic self-test
    and compare every result with the packaged Phase 8/9 evidence.
24. **Cleanup:** explicitly Quit, confirm no child process, remove only the disposable
    project and temporary acceptance data, and retain the independent backup until
    the operator signs off.

Any mismatch, stale identity, failed integrity check, uncertain rollback, unexpected
network destination, secret in an export, or unsupported platform stops acceptance.
Do not continue with the live project until the cause is understood.
