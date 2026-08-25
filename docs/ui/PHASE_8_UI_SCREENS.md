# Phase 8 product screens

Phase 8 extends the existing Regression Detail and Repair Workspace surfaces. It does not create a
second repair architecture. Every visible label, status, instruction, warning, and action is rendered
from English-base and Hebrew translation catalogs; Hebrew uses RTL while paths, IDs, and digests stay
LTR.

The required screen/state set is documented with a purpose, displayed state, deterministic data
source, available actions, known facts, unknowns, next step, and live-source mutation status in
[`../phase-8-delivery/PHASE_8_SCREEN_GUIDE.md`](../phase-8-delivery/PHASE_8_SCREEN_GUIDE.md).

Primary product surfaces:

- Regression Detail embeds the real Repair Workspace → Candidate → Validate → Prepare Apply flow.
- Candidate review exposes bounded file operations, sizes, exact revision identity, warnings, and
  text diffs without requiring Git terminology.
- Apply confirmation explains the fresh safety point, one-time confirmation, affected paths, fresh
  live checks, rollback, and unknown boundaries before a write can occur.
- Apply/rollback/recovery states distinguish working-copy evidence from fresh live evidence and never
  claim success before the Completion Gate passes.
- Demo Lab and Product Self-Test use disposable synthetic data only and are clearly labeled.
- Technical identifiers remain expandable and do not replace novice product language.

Critical states are not playful. Mascot assets are used sparingly for orientation; recovery and
failure text remains primary. Reduced-motion presentation retains all state and progress information.
