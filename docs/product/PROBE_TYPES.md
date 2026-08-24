# Universal Probe types

Universal Probes answer a bounded question about one exact source and runtime state. They reuse the
existing Protection Plan, behavior, evidence, regression, and Completion Gate architecture.

## Common probe contract

Every Probe has a stable definition and immutable versions. A run records:

- exact source snapshot/identity and optional Episode;
- exact Probe and Runtime Profile versions;
- approved definition and expected result;
- timeout, retry, and bounded evidence policy;
- result, limitations, and deterministic signal reasons.

Runs support cancellation and cleanup. Approval does not guarantee availability or PASS.

## Browser Probe

Uses the existing MellowYak Browser Replay path. It is available only when the runtime is valid, the
accepted baseline is current and compatible, supported selectors/assertions exist, and packaged
replay is available. Browser sessions remain ephemeral and loopback-confined.

Use it for a protected web flow with a recorded expected outcome. A Browser screenshot by itself is
not a PASS and is not a regression decision.

## API Probe

Sends a bounded request to a loopback/local endpoint and can assert status, selected JSON fields,
text, and response time. Authorization headers, cookies, secret query values, and request/response
bodies are not stored by default. External URLs are denied by the Phase 7 policy.

Use it for a local health or behavior endpoint with a safe deterministic response.

## CLI Probe

Runs one explicitly approved executable with an argv array and project-relative working directory.
It can assert exit code, bounded stdout/stderr text or regex, and an expected output file. It never
uses a shell, interprets a command string, or inherits the complete user environment.

Use it for a small deterministic command or fixture—not a destructive maintenance script.

## Process Health Probe

Observes a selected process start, bounded liveness, exit code, local port, and optional loopback
health response. It does not inject into processes, read arbitrary memory, inspect unrelated
processes, or attach system-wide.

A related new crash can produce `HIGH` evidence. It becomes `CONFIRMED` only when comparable accepted
evidence and reproduction requirements are satisfied.

## Test Runner Probe

Runs an explicitly approved existing test target, such as one pytest test ID, Vitest/Jest path,
Playwright test, or PHPUnit target. Impact and behavior links select relevant tests; the complete suite
is not run by default.

Use it when the repository already contains a focused deterministic check. The underlying test runner
remains the execution authority.

## Manual Probe

Records an explicit human confirmation bound to exact source and time, with optional bounded local
evidence. The UI marks it manual and not automated.

Use it when no safe automatic check exists. Manual attestation is honest evidence with an explicit
limitation; it must never be presented as automated replay.

## Signal states

| State | Meaning |
|---|---|
| `WATCH` | A source/impact change may require a check. No behavioral failure is claimed. |
| `SUSPECTED` | One failure or anomaly exists without reproducible comparable evidence. |
| `HIGH` | A related crash or prior accepted PASS followed by one current FAIL needs retry/review. |
| `CONFIRMED` | A comparable accepted PASS is followed by reproducible current FAIL, or the existing supported regression engine independently supports the finding. |

A changed file, dependency, or wide impact path is never a regression by itself. Flaky failure that
passes on retry is not `CONFIRMED`. The UI shows friendly language first and expandable technical
details, including what remains unknown.

## Impact-based selection

MellowYak prioritizes explicit human behavior links, runtime-observed links, parsed source links,
relevant tests, always-recheck critical behaviors, history, and then heuristics. Large fan-out is
bounded with sentinels, truncation, and visible unknowns. Selection means “check this,” not “everything
else is safe.”

## Known-Good relationship

“This works — save it” may create a pinned milestone only after the selected automatic Probe passes
or the user explicitly attests. The milestone does not replace Last Known Good evidence for unrelated
behaviors and does not automatically create a Protected Behavior.
