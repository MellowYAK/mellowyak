# Runtime Profile guide

Runtime Profiles describe the approved ways a local project runs. They do not install a runtime,
download dependencies, or change source files. One project can have a primary profile and several
secondary profiles.

## First-time Runtime Wizard

Select **Add project** to open the eight-step wizard:

1. **Project** — choose a local source folder, confirm its display name, and review whether Git was
   detected. Git is optional and source remains local.
2. **Project type** — confirm Web App, API / Service, Desktop App, CLI Tool, Mobile App, Background
   Worker, Library, Mixed / Polyglot, or Other. Detection is a suggestion only.
3. **Detected runtimes** — review each detected runtime, select the profiles you want, and explicitly
   choose the primary runtime. MellowYak does not choose based on language frequency.
4. **How it runs** — enter a profile name, mode, executable, one argument per line, project-relative
   working directory, optional ports and loopback health URL, test definition, runtime version,
   dependency manifests, and safe environment-variable names.
5. **Tests** — approve only the discovered test targets that MellowYak may run. Nothing is enabled
   simply because it was detected.
6. **Monitoring and privacy** — select passive or paused monitoring, light/deep observation when
   supported, retention days, and the project storage soft cap. The default is passive, light,
   loopback-only, sensitive-excluded monitoring.
7. **Initial Save Point** — review included/excluded counts, new physical bytes, reused bytes,
   optional Git anchor, and snapshot identity.
8. **Done** — review source/runtime state, available probe types, and every explicit limitation.

Existing projects remain usable. If a project has no approved Runtime Profile, its Runtime screen
shows **Setup incomplete** and **Complete runtime setup** while source monitoring, scanning, Impact,
Episodes, and Save Points continue.

## Profile fields

### Profile name and role

Choose a human-readable name such as `Desktop UI`, `API`, or `Background worker`. Mark exactly one
profile primary when that distinction is useful. Secondary profiles are first-class and can be bound
to probes independently.

### Execution mode

- **Managed** — MellowYak may start and stop the explicitly approved executable.
- **External** — the user or another local tool owns the process; MellowYak observes supported health.
- **Manual** — MellowYak records the runtime relationship but does not manage execution.

### Executable, arguments, and working directory

The executable and arguments are stored separately. Enter one argument per line. Shell syntax,
pipelines, redirection, and command substitution are not accepted. The working directory must be
relative to and resolve inside the selected project.

### Network and environment

Phase 7 uses `LOOPBACK_ONLY` by default. Health/API/browser URLs must target an explicit local
runtime. A profile stores only approved environment-variable **names** and a minimal safe execution
environment; values, tokens, passwords, cookies, registry credentials, and complete environments are
not persisted.

## Runtime screen

Open a project and select **Runtime** to:

- run detection again;
- inspect all candidates and their limitations;
- add or revise a profile;
- see the immutable version history represented by the current version number;
- validate availability and configuration;
- start or stop a managed runtime;
- inspect process/health/test status and expandable technical details;
- reopen the Runtime Wizard if setup is incomplete.

Editing a profile appends an auditable version. Existing probe runs continue to reference the prior
version that produced their evidence.

## Adapter expectations

| Adapter | Detection | Approved execution | Important limit |
|---|---|---|---|
| Python | Python manifests, local environments, version, pytest and common entry points | Supported when a compatible local executable is available | No `pip config`, complete environment, or automatic install |
| Node.js | package/lock files, package manager, version, scripts and test frameworks | Supported for an approved executable/argv | Detection never runs install or package scripts |
| PHP | Composer/PHPUnit markers and bounded CLI metadata | Supported only when a compatible local PHP executable is available | No `phpinfo()` or stored INI values |
| Generic process | User-specified executable and bounded health | Supported after explicit approval | No unrelated process inspection or memory access |
| Ruby / Java | Metadata detection when recognized | Metadata-only may be reported | Execution availability is not implied |

Runtime availability is local and platform-specific. `Detected` does not mean `running`, and
`configured` does not mean a probe passed.

## Ready with limits

Select the **Ready with limits** badge to see, for each limitation:

- what it means;
- why it matters;
- what MellowYak can still do;
- the recommended next action.

Adapter failure is fail-open. It must never block editor writes, source watching, Episodes, snapshots,
or opening the desktop application.
