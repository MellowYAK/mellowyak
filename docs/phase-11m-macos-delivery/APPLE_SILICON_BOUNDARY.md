# Apple Silicon boundary

Status: `WORKFLOW_CONFIGURED_NOT_RUNTIME_VERIFIED`.

The same-source CI path stages an architecture-matching browser, builds the Python engine and Tauri
application on a native arm64 runner, and inspects the main and engine Mach-O identities. This Intel
host did not produce or run an arm64 package. No universal binary claim is made because every nested
browser helper, framework, engine and executable would need both architectures.
