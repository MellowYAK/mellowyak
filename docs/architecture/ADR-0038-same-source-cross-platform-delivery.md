# ADR-0038: Same-source cross-platform desktop delivery

Status: accepted architecture; native acceptance remains platform-specific
Date: 2026-08-25

## Context

MellowYak must support work on macOS and Windows in parallel without creating a Mac
product and a separate Windows product. Product behavior, API contracts, migrations,
translations, privacy rules and safety invariants must advance once in one repository.
Operating systems still require different bundles, filesystem adapters, notification
integration, embedded web runtimes, installers and updater artifacts.

## Decision

- One Git repository, source tree, version and exact commit define a MellowYak release.
- Shared React, TypeScript, Python engine, SQLite migrations, OpenAPI contract,
  translations and product tests are platform-neutral.
- Tauri configuration and narrowly scoped native adapters own platform differences.
- macOS produces `.app`/`.dmg`; Windows x64 produces an NSIS `.exe` and may later add
  MSI; Linux produces AppImage/DEB. Generated installers are release artifacts, never
  committed source.
- Pin Node, Python target and Rust toolchain. Every artifact manifest records the exact
  commit, platform, architecture, schema, validation status and file hashes.
- Bootstrap, build and validation entry points are platform-specific wrappers over the
  same source: `bootstrap-macos.sh`, `bootstrap-windows.ps1`, `bootstrap-linux.sh`,
  `build-platform.sh`/`.ps1`, and `validate-linux.sh`/`validate-windows.ps1`.
- The updater selects an artifact for the running platform from the same release
  version and commit. It must not cross-install artifacts.
- A configured CI job or successful source build is not native runtime acceptance.
  Windows/Linux remain `SOURCE_PACKAGE_VERIFIED` until their full packaged lifecycle
  is executed on that native OS; only then may the manifest record `VERIFIED_WORKING`.
- Parallel work uses short-lived platform branches such as
  `platform/windows-x64-acceptance`, but product changes return to the shared branch.
  No product feature may be reimplemented separately per OS.

## Windows handoff contract

1. Check out the exact baseline or requested commit.
2. Run `scripts/bootstrap-windows.ps1` in PowerShell 7.
3. Run `scripts/build-platform.ps1 -Bundle nsis`.
4. Run `scripts/validate-windows.ps1` without `-LifecycleVerified` for build/package
   evidence. Use `-LifecycleVerified` only after a native operator completes startup,
   engine handshake, tray, notification, close-to-background, explicit Quit, update
   selection and uninstall checks.
5. Retain the `.exe` and artifact manifest together. Report failures against the exact
   commit; fix shared code or a narrowly scoped adapter, then merge the fix back.

## Consequences

Mac and Windows work can proceed concurrently while sharing every product improvement.
Native acceptance evidence remains honest and cannot be inferred from another OS.
Maintainers must keep platform conditionals at adapter/configuration boundaries and
must reject divergent schemas, translations, product flows or version numbers.
