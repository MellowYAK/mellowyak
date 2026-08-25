# macOS notification guide

Native notifications use the local macOS notification implementation. Activation navigates only
after the native default action is reported; showing a notification does not itself change route.
The existing application is focused and receives the validated local destination without creating
a second engine.

Notification route generation and project ownership validation remain in the shared product layer.
Payloads must never contain source, evidence bytes, full paths, bearer tokens, credentials or
provider data. Forged, stale, deleted or cross-project destinations are rejected before navigation.

Automated bridge and existing-instance behavior are verified. A physical Notification Center click
requires a person and is `IMPLEMENTED_NOT_RUNTIME_VERIFIED`.
