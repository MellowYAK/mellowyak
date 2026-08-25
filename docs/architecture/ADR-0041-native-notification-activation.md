# ADR-0041: native macOS notification activation

Status: implemented; physical Notification Center click remains a manual runtime gate.

## Decision

The engine validates the typed, project-bound route before the desktop displays a notification. On
macOS the desktop retains the native notification handle and, only after the default user action,
focuses the existing window and emits that exact validated route. Merely displaying a notification
does not change pending navigation. Notification content excludes source, paths, tokens and evidence.

Portable non-macOS notification sending remains unchanged. A source/structural test does not upgrade
the physical macOS click to runtime verified.
