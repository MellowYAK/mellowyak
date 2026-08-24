# MellowYak mascot usage

The original transparent sheet is preserved byte-for-byte in `assets/mascot/sheet/mellowyak-sheet.png`. The 16 pose files were extracted from its automatically detected transparent row and column separators, retain their source pixels, and add 16 transparent pixels around the detected visible bounds.

## Localization contract

Mascot files never supply user-facing copy. Every visible caption, status, tooltip, and accessible image description must come from a translation key. The JSON manifest therefore stores `meaningKey` and stable screen/state identifiers instead of rendered English strings. English and Hebrew descriptions live in the desktop translation catalogs, and Hebrew surfaces render in RTL.

## Placement rules

- Use one prominent mascot per sparse surface at most.
- Prefer onboarding, empty states, calm monitoring, helper cards, warnings, success confirmations, and privacy reassurance.
- Avoid mascots in dense technical tables unless an illustration explains an otherwise ambiguous state.
- Large onboarding or empty-state art: 160–240 px. Helper panels: 96–160 px. State stickers: 64–96 px.
- On narrow screens, place art above the copy, constrain it to 120–160 px, and keep it out of the primary action path.
- `state-critical` art reinforces translated text and icons; it must never be the only indication of a warning, failure, unknown, or success state.
- Do not present `yak-alert-point` as a detected regression or `yak-success-check` as verified completion until those capabilities and fresh evidence exist. Phase 3 may use them only for truthful issue, readiness, or milestone states.

## Exact screen map

| Surface | Primary pose | Optional pose | Guidance |
| --- | --- | --- | --- |
| Welcome | `yak-wave` | `yak-neutral` | Large, friendly side illustration. |
| First setup | `yak-security-shield` | `yak-neutral` | Reinforce local-only/privacy copy. |
| Add project | `yak-search-inspect` | `yak-working-laptop` | Use in the sparse folder selection or inspection state. |
| Initial scan | `yak-working-laptop` | `yak-confused`, `yak-success-check` | Active scan, unknown coverage, then truthful project readiness. |
| Home / command center | `yak-sleeping` | `yak-peek-laptop` | Calm idle or passive observation; use alerts only for a real issue. |
| Projects empty | `yak-wave` | `yak-neutral` | Pair with the single primary add-project action. |
| Project overview | none | `yak-teaching-map` | Keep dense metrics clear; illustration only in a helper card. |
| Change cockpit | `yak-thinking` | `yak-alert-point` | Analysis state or a real attention condition. |
| Impact map | `yak-teaching-map` | `yak-search-inspect` | Empty/help state, not every result card. |
| Protected behaviors (future) | `yak-security-shield` | `yak-success-check` | Only after explicit behavior definitions exist. |
| Verification (future) | `yak-working-laptop` | `yak-success-check`, `yak-warning-stop` | Results must remain textually and accessibly explicit. |
| Regression and repair (future) | `yak-alert-point` | `yak-thinking` | Only after evidence-backed regression classification exists. |
| Evidence | none | `yak-search-inspect` | Empty state only. |
| Value | `yak-relaxed-chair` | `yak-wink-thumbsup` | Calm, passive-first product character. |
| Connectors (future) | `yak-teaching-map` | `yak-working-laptop` | Guidance without implying a connector is enabled. |
| Settings / privacy | `yak-security-shield` | `yak-neutral` | Small reassurance panel. |

## Pose catalog

| Pose | Meaning translation key | Tone | Role | Preferred sizes |
| --- | --- | --- | --- | --- |
| `yak-neutral` | `mascot.meaning.neutral` | neutral | supportive | 96, 160, 240 px |
| `yak-wave` | `mascot.meaning.wave` | helpful | supportive | 120, 180, 240 px |
| `yak-thinking` | `mascot.meaning.thinking` | helpful | supportive | 72, 120, 180 px |
| `yak-peek-laptop` | `mascot.meaning.peekLaptop` | watchful | decorative | 96, 160, 220 px |
| `yak-wink-thumbsup` | `mascot.meaning.winkThumbsup` | success | supportive | 72, 120, 180 px |
| `yak-warning-stop` | `mascot.meaning.warningStop` | warning | state-critical | 64, 96, 144 px |
| `yak-teaching-map` | `mascot.meaning.teachingMap` | helpful | supportive | 96, 160, 220 px |
| `yak-security-shield` | `mascot.meaning.securityShield` | trust | supportive | 80, 140, 200 px |
| `yak-working-laptop` | `mascot.meaning.workingLaptop` | active | supportive | 72, 120, 180 px |
| `yak-search-inspect` | `mascot.meaning.searchInspect` | helpful | supportive | 88, 144, 210 px |
| `yak-alert-point` | `mascot.meaning.alertPoint` | warning | state-critical | 64, 96, 144 px |
| `yak-success-check` | `mascot.meaning.successCheck` | success | state-critical | 64, 96, 160 px |
| `yak-confused` | `mascot.meaning.confused` | unknown | state-critical | 72, 120, 180 px |
| `yak-sleeping` | `mascot.meaning.sleeping` | idle | supportive | 88, 144, 210 px |
| `yak-celebrate` | `mascot.meaning.celebrate` | success | decorative | 96, 160, 220 px |
| `yak-relaxed-chair` | `mascot.meaning.relaxedChair` | calm | decorative | 120, 180, 240 px |

## Core V1 subset

Start with eight poses: `yak-neutral`, `yak-wave`, `yak-thinking`, `yak-working-laptop`, `yak-alert-point`, `yak-success-check`, `yak-security-shield`, and `yak-sleeping`. The current desktop should use only poses whose state is already truthful; future verification and regression meanings remain explicitly gated by their later product phases.

## Regenerating the crops

Install Pillow in a tooling environment, then run:

```bash
python3 scripts/extract_mascot_sheet.py \
  "docs/validation/ChatGPT Image Aug 24, 2026, 07_33_41 AM.png" \
  assets/mascot
```

The command detects separators, writes transparent crops, verifies clean transparent outer edges, and confirms that the preserved sheet SHA-256 matches its source.
