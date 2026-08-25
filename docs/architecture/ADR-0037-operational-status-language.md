# ADR-0037: Operational status language

Status: accepted for Phase 10
Date: 2026-08-25

Status wording must match the strongest evidence actually available.

- `Everything currently looks okay` is reserved for projects whose required recorded
  checks justify that statement.
- `No confirmed issue found` is used when evidence has not confirmed a regression but
  coverage or runtime boundaries remain incomplete.
- `Ready with limits` always includes what works, the exact limitations and a next
  action; it is not a badge-only state.
- `May be affected` describes a relationship or selection, not a failure.
- `Something that worked before broke` requires an accepted prior result and a current
  confirmed failure.
- Root cause and blast radius remain unknown unless direct evidence proves them.
- Candidate success says it passed in the isolated workspace and explicitly says the
  live project is not yet verified.
- Apply success is not shown until post-Apply live verification commits.
- Rollback reports what was restored and its byte-identity result without alarmist copy.

English is the base translation catalog. Hebrew has exact key parity and renders RTL;
technical identifiers remain LTR in both languages.
