# Phase 8 technical sources

Access date: 2026-08-25

| Source | Version | Engineering decision |
|---|---|---|
| [Python `os` documentation](https://docs.python.org/3/library/os.html) | Python 3.14.7 docs; implementation supports Python 3.11+ | Use `flush` + `os.fsync`, same-filesystem `os.replace`, and explicit error handling. A successful replace is atomic at the directory-entry boundary, not a whole multi-file transaction guarantee. |
| [POSIX `rename`](https://pubs.opengroup.org/onlinepubs/9799919799/functions/rename.html) | POSIX.1-2024 / Issue 8 | Treat each supported rename as one atomic directory operation; journal and rollback are still required across multiple files. Reject cross-filesystem operations and path races. |
| [Microsoft MoveFileExW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexw) | Win32 API | Expect replacement to fail for locks, ACLs, directory targets, or unsupported filesystems. Never force-close another process; stop and roll back. |
| [Microsoft moving and replacing files](https://learn.microsoft.com/en-us/windows/win32/fileio/moving-and-replacing-files) | Win32 file management | Preflight cannot prove writability from metadata alone; actual replacement remains authoritative and failures enter rollback. |
| [Apple `fsync(2)`](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/fsync.2.html) | macOS/BSD manual | Flush file content before replace and parent-directory metadata afterward where supported. Document that power-loss durability is best effort. |
| [Rust `std::fs::rename`](https://doc.rust-lang.org/std/fs/fn.rename.html) | Rust 1.98.0 docs | Preserve the same-filesystem/platform-specific limitation in desktop documentation and do not claim universal cross-platform atomicity. |
| [Tauri 2 capabilities](https://v2.tauri.app/security/capabilities/) | Tauri 2 | Keep live Apply authority in the authenticated engine and expose distinct scoped operations instead of granting generic filesystem access to the webview. |
| [Tauri 2 opener](https://v2.tauri.app/plugin/opener/) | Tauri 2 | Opening/export actions must remain explicit and scoped; dangerous open-path operations are not enabled as a blanket frontend capability. |

No dependency was added for these decisions. Phase 8 uses the existing Python standard library,
SQLAlchemy/Alembic, FastAPI, React, Tauri, snapshot CAS, Probe Runner, and evidence stack; therefore
no new dependency license is introduced.
