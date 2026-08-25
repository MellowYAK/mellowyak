# Morning manual acceptance — Phase 8

Use this as one guided product session. Use only the synthetic Demo Lab. Do not select a real project.

## 1. Start and language

- Launch the fresh Phase 8 application.
- Confirm the startup completes and the local/privacy status is visible.
- Switch English → Hebrew. Confirm the entire product surface is RTL while paths/digests stay LTR.
- Switch back to English.

Expected: no login, cloud, Docker, provider, prompt, or coding-agent permission is requested.

## 2. Create the disposable Demo Lab

- Choose **Try MellowYak with a Demo Project**.
- Select an empty disposable folder.
- Confirm the product labels it **Synthetic demo**.
- Run the initial scan, runtime profile, Save Point, protected checkout behavior, and known-good Probe.

Expected: the known-good Probe passes, the fixture works without Git, Node, PHP, Docker, or an
external database, and no real project changes.

## 3. Signals and confirmed regression

- Inject the file-only change; confirm the state is WATCH, not regression.
- Inject the controlled regression and reproduce the failure.

Expected: the app shows prior accepted PASS, comparable current FAIL, retry FAIL, and CONFIRMED; it
does not claim root cause.

## 4. Working copy and candidates

- Create the Repair Workspace.
- Open it and confirm it is outside the demo live source.
- Create the bad demo candidate and validate it.

Expected: validation fails and Apply remains disabled.

- Reset/recreate the workspace, create the valid candidate, review its paths/diff, and validate.

Expected: the original failed Probe runs first, all required checks pass, and the exact revision is
VALIDATED.

## 5. Stale-source protection

- Use the guided stale-source scenario after validation.

Expected: Apply is blocked before any write; the exact changed identity/path is explained; export and
recreate options remain available; no automatic merge occurs.

## 6. Successful Apply

- Recreate and validate the fresh candidate.
- Open Apply confirmation and review paths, checks, unknowns, safety point, and rollback text.
- Deliberately confirm once.

Expected: a fresh pinned safety snapshot and journal appear before writes. Fresh live verification
runs after writes and does not reuse workspace PASS. Success becomes **Applied and verified**. No
Known-Good milestone is created automatically.

## 7. Automatic rollback

- Reset the disposable demo and choose **Simulate post-apply failure**.

Expected: Apply writes begin, live verification fails, automatic rollback restores byte-identical
pre-Apply bytes, unrelated files are unchanged, and the original regression remains unresolved.

## 8. Crash recovery

- Run the guided incomplete-transaction simulation, close, and relaunch the app.

Expected: the incomplete journal is detected. No success is assumed. The app either safely resumes
verification/rollback or shows **Manual recovery is required** with a redacted Recovery Bundle.

## 9. Product Self-Test

- Open Settings/Diagnostics and run **Local Product Self-Test**.
- Review every step and export its report.

Expected: the run uses a disposable folder, reports only executed checks, ends PASS/PARTIAL/FAILED
honestly, leaves no child process, performs no external network request, and cleans temporary data.

## 10. Delivery review

- Open `PHASE_8_SCREEN_GUIDE.md` or the PDF in this folder.
- Compare all 26 English/Hebrew states with the application.
- Confirm the app and DMG identities against `VERIFICATION_EVIDENCE.md`.

Acceptance is complete only if every expected result above is observed. Record any mismatch as a
manual finding; do not reinterpret a PARTIAL or FAILED result as PASS.
