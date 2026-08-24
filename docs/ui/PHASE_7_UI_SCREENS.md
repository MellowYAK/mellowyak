# Phase 7 current product screens

Phase 7 adds Runtime and source-memory workflows to the existing Command Center, Projects, Alerts,
Settings, Overview, Changes, Impact, and Behaviors surfaces.

## Translation and direction contract

Every visible React label, title, message, placeholder, accessible name, and mascot description must
resolve through `apps/desktop/src/i18n.ts`. English is the base catalog. Hebrew must have exact key
parity and set document direction to RTL. The translation-only checker covers all Phase 7 components.

## Navigation map

Project navigation remains compact:

1. Overview
2. Changes
3. Impact
4. Behaviors
5. Runtime
6. Memory

## Runtime Wizard

The Add Project action opens an eight-step wizard: Project, Project type, Detected runtimes, How it
runs, Tests, Monitoring/privacy, Initial Save Point, and Done. It uses a small contextual mascot and
never puts mascot art in dense technical tables.

Existing projects with no profile display Setup incomplete and can reopen the same wizard without
losing source monitoring or previous data.

## Runtime

The Runtime screen shows detected candidates and all versioned primary/secondary profiles. It exposes
managed/external/manual mode, executable/argv safety, working directory, health, process state,
ports, tests, limitations, and validate/start/stop actions. Detection and configuration do not imply
a PASS.

## Memory / Save Points

The Memory screen shows Episode history, Save Points, included/excluded metrics, logical/new/reused
bytes, integrity, pins, known-good milestones, optional Git anchors, retention, storage soft cap,
manifest detail, and isolated materialization. It states that Git is optional and a Save Point alone
is not behavioral evidence.

## Behaviors and Probes

The Behaviors screen includes **This works — save it** and a Universal Probe panel. Users can define
Browser, API, CLI, Process, Test, or Manual evidence, optionally bind a Runtime Profile version, run or
cancel the check, review the last result, and expand technical details. Automatic eligibility requires
approval and supported configuration.

## Signals and Repair Workspace

Change/regression context uses friendly `WATCH`, `SUSPECTED`, `HIGH`, or `CONFIRMED` language with
expandable deterministic reasons. `Ready with limits` is interactive and describes meaning, impact,
still-available capabilities, and next action. A confirmed incident can expose an isolated Repair
Workspace panel with create/open/delete actions; no apply or coding-agent action exists.

## Visual delivery

The 23-state deterministic screenshot specification is
[`../phase-7-delivery/PHASE_7_SCREEN_GUIDE.md`](../phase-7-delivery/PHASE_7_SCREEN_GUIDE.md). Image
capture and inspection are complete; exact final evidence is recorded in the Phase 7 delivery folder.
