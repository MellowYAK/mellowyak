# Phase 9 platform matrix

| Platform | Build configuration | Local package | Runtime acceptance | Honest status |
|---|---|---|---|---|
| macOS Intel x86_64 | configured | `.app` and DMG built | source, package, install, lifecycle, migration, Phase 8/9 gates executed | **VERIFIED_WORKING** |
| macOS Apple Silicon arm64 | configured native job | not built in this run | not executed | **WORKFLOW_CONFIGURED_NOT_RUNTIME_VERIFIED** |
| Windows x64 | configured native job | not built in this run | not executed | **WORKFLOW_CONFIGURED_NOT_RUNTIME_VERIFIED** |
| Linux x64 | configured native job | not built in this run | not executed | **WORKFLOW_CONFIGURED_NOT_RUNTIME_VERIFIED** |

The GitHub Actions matrices are source configuration only because this task performs
no push and no remote workflow execution. A workflow definition is not package or
runtime evidence. A universal macOS claim requires every executable, sidecar,
framework, and bundled browser component to carry and execute both architecture
slices; that was not established here.

Before another platform can move to `VERIFIED_WORKING`, its native job must build the
locked source, inspect the produced package, run schema migrations, execute package
smoke and Phase 9 acceptance, verify lifecycle/orphan behavior, and publish an exact
artifact manifest from the same commit.
