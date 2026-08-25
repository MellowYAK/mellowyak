# MellowYak macOS Acceptance Lab

This dependency-light polyglot fixture is permanently marked as synthetic. It contains a local
Python HTTP service, a command-line surface, static HTML/JavaScript, translation catalogs, and a
local test command. Phase 11M copies it to a temporary root; it must never be registered in place
or used as a private-project substitute.

Runtime profiles:

- Web/API: `python3 service.py --port 0`
- CLI: `python3 cli.py status`
- Test: `python3 run_checks.py`

The UI has no literal display strings. English is the base catalog and Hebrew applies RTL.
