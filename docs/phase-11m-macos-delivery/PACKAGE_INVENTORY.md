# Intel macOS package inventory

## Application

- Bundle: `apps/desktop/src-tauri/target/release/bundle/macos/MellowYak.app`
- Product version: `0.2.0-preview.1`
- Architecture: x86_64
- Application tree size: 887,631,373 bytes
- Desktop executable: 22,949,728 bytes
- Desktop SHA-256: `92cc3b80a931d4f0cb28737ddb9109a7dea264beb594643aa7a0265d118ea7cc`

## Packaged engine

- Relative path: `Contents/Resources/engine/mellowyak-engine/mellowyak-engine`
- Architecture: x86_64
- Engine executable: 15,680,192 bytes
- Engine directory: 224,377,307 bytes
- Engine SHA-256: `ca3f4744e7e397ec6513a854afa5352ff1c3cd9e1e74ed0d26a9ccaf8493e77f`
- Packaging: PyInstaller onedir; generated cache files are excluded from staged Alembic resources.

## Browser

- Identity: Google Chrome for Testing 151.0.7922.34
- Architecture: x86_64
- Browser resource directory: 637,205,282 bytes
- Role: local packaged browser probes only; no CDN or external runtime dependency.

## DMG

- Path: `apps/desktop/src-tauri/target/release/bundle/dmg/MellowYak_0.2.0-preview.1_x64.dmg`
- Size: 435,933,674 bytes
- SHA-256: `3f06b78fb901f71ef5b2418d4254768c780e4ebfda8789889b8310c167c9e030`
- Inspection: ad-hoc signature valid, read-only mount passed, application and `/Applications`
  symlink present, contained desktop hash matched, clean detach passed.

The package scan found no database, snapshots, evidence, Repair Workspace, Apply journal, recovery or
support bundle, browser profile, private key, provider data or local user-home build path.
