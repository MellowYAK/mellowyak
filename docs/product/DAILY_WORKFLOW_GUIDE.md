# Daily workflow guide

## Start on Home

Home answers one question first: does anything require attention? Read the overall status, then the
attention queue, project rows and recent activity. `No confirmed issue` means no confirmed regression
is present in the currently available evidence; it never means total coverage or guaranteed safety.
`Needs attention`, `Ready with limits`, `Unknown`, disconnected source and pending recovery all remain
visible and actionable.

Use **Add project** for a local repository or **Demo Lab** for the disposable synthetic walkthrough.
No source is uploaded. Home summaries are bounded and link to the exact local entity behind a status.

## Open a project

Project Overview is the daily center for one project. Review current source identity, latest Episode,
checks, protected behaviors, regressions, runtime readiness, storage and limitations. Follow the
recommended next action; open technical disclosure only when paths, hashes, IDs or provenance are
needed.

## Follow a change

Activity groups facts chronologically by Episode. Open an Episode to see what changed, which checks
were required or skipped, what evidence exists and the final signal. An impacted area is a reason to
recheck, not proof that it broke.

## Respond to a confirmed regression

Open Regression Detail, compare the accepted prior PASS with reproducible current FAIL evidence, and
review limitations. Create or open an isolated Repair Workspace. Candidate validation happens in the
workspace and does not edit the live source. Apply remains a separate, explicit action.

## Apply safely

Only an exact validated candidate can proceed. Confirm deliberately, verify the fresh source identity,
and allow MellowYak to create a Safety Snapshot and durable journal before writes. Fresh live
verification runs afterward. A failed post-check restores only transaction-affected paths; uncertain
recovery stops further writes.

## End or troubleshoot

Closing the window keeps background monitoring when configured. Use the native tray to Show or Quit.
Diagnostics reports local engine, database, storage and package state without exposing tokens or
source. Product Self-Test uses disposable synthetic data. Inspect every support bundle before sharing.
