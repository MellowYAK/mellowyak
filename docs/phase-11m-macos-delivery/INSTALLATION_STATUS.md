# Installation status

Status: `VERIFIED_WORKING` for the local ad-hoc Intel development package.

- Installed path: `/Applications/MellowYak.app`.
- Recoverable prior application:
  `/Applications/MellowYak-previous-20260825-201627-4a1cf1.app`.
- Installed desktop SHA-256 matched the validated build:
  `92cc3b80a931d4f0cb28737ddb9109a7dea264beb594643aa7a0265d118ea7cc`.
- Installed engine SHA-256 matched:
  `ca3f4744e7e397ec6513a854afa5352ff1c3cd9e1e74ed0d26a9ccaf8493e77f`.
- Installed code-sign structure verified.
- Exact installed application launched with an isolated data root and created one engine child.
- Explicit quit left no engine orphan.
- Exact installed engine reached schema `0009_technical_preview_readiness`, passed Product Self-Test,
  Apply, rollback and no-external-network checks in `MACOS_INSTALLED_VALIDATION.json`.

Physical close-to-tray/reopen was not automated and remains an honest manual boundary. This
installation is not public-distribution ready because it is not Developer ID signed or notarized.
