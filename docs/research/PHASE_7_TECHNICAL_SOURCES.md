# Phase 7 technical sources

Access date for every source: 2026-08-24. Research was bounded to primary/official documentation. No repository content, source, path or evidence was uploaded. No new dependency was selected.

| Official source | Version | Decision informed |
|---|---|---|
| [Python `os.replace` and `os.fsync`](https://docs.python.org/3/library/os.html#os.replace) | Python 3.14.7 docs; implementation remains Python 3.11-compatible | Publish objects/manifests from a same-directory temporary file after flush/fsync, using same-filesystem `os.replace`; reject cross-filesystem publication. |
| [Python `hashlib.file_digest`](https://docs.python.org/3/library/hashlib.html#hashlib.file_digest) and [JSON encoder](https://docs.python.org/3/library/json.html#json.dumps) | Python 3.11+ API | SHA-256 objects and canonical sorted compact JSON with `allow_nan=False` produce deterministic manifest/snapshot identities. |
| [Python `pathlib`](https://docs.python.org/3/library/pathlib.html#pathlib.Path.resolve) | Python 3.14.7 docs | Resolve and confine roots, never traverse directory symlinks, classify links explicitly and sort traversal because recursive discovery ordering is unspecified. |
| [Python `shutil.which`](https://docs.python.org/3/library/shutil.html#shutil.which) and [`subprocess.run`](https://docs.python.org/3/library/subprocess.html#subprocess.run) | Python 3.14.7 docs | Discover exact executables and execute an argv sequence with `shell=False`, bounded time/output and an allow-listed environment. |
| [Python command-line options](https://docs.python.org/3/using/cmdline.html#cmdoption-V), [virtual environments](https://docs.python.org/3/library/venv.html#how-venvs-work), [PyPA `pyproject.toml`](https://packaging.python.org/en/latest/specifications/pyproject-toml/) | Current official docs/spec | Prefer a project virtual-environment interpreter without activation; parse manifests without execution; never persist a complete environment. |
| [Node.js CLI](https://nodejs.org/api/cli.html#-v---version) and [`execFile`](https://nodejs.org/api/child_process.html#child_processexecfilefile-args-options-callback) | Node.js 26.7.0 docs | Identify Node directly and preserve executable-plus-argv/no-shell semantics in the Python engine. |
| [npm scripts](https://docs.npmjs.com/cli/using-npm/scripts/) | npm CLI 12.0.2 docs | Detect scripts but require explicit approval; document npm's internal platform-shell and pre/post-hook behavior; never run install or scripts during detection. |
| [PHP CLI options](https://www.php.net/manual/en/features.commandline.options.php), [`php_sapi_name`](https://www.php.net/manual/en/function.php-sapi-name.php), [`get_loaded_extensions`](https://www.php.net/manual/en/function.get-loaded-extensions.php) | PHP 8 manual | Use `php --version` and only fixed bounded metadata code; never persist `phpinfo`, INI values, environment values or credentials. |
| [Composer schema](https://getcomposer.org/doc/04-schema.md) | Current Composer schema | Detect `composer.json`/lock without invoking Composer and fingerprint lock bytes. |
| [Node.js filesystem-watch caveats](https://nodejs.org/api/fs.html#fswatchfilename-options-listener) | Node.js 26.7.0 docs | Treat watcher events as hints, then debounce/settle and perform an authoritative filtered rescan with periodic reconciliation and fail-open fallback. |
| [Tauri 2 commands](https://v2.tauri.app/develop/calling-rust/) and [capabilities](https://v2.tauri.app/security/capabilities/) | Tauri 2.x | Keep heavy runtime/snapshot work in the authenticated engine; expose only typed bounded native commands and least-privilege local capabilities. |
| [Tauri sidecars](https://v2.tauri.app/develop/sidecar/), [system tray](https://v2.tauri.app/learn/system-tray/), [distribution](https://v2.tauri.app/distribute/) | Tauri 2.x | Preserve target-triple managed sidecar packaging and existing tray lifecycle; do not claim Linux tray mouse events that Tauri does not support. |

## Dependency decision

The existing standard library, SQLAlchemy/Alembic, FastAPI, `watchfiles`, `pathspec`, Tauri and current browser stack are sufficient. Phase 7 introduces no new runtime dependency and therefore no new dependency license. Existing licenses remain governed by the repository lockfiles and current third-party notices.
