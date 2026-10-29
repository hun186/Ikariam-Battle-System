# P0 — Local, user-reported visual review ledger for pending battle captures

**Research-only, Issue #73.** Owner-merged PRs #110–#113 created
pending manually transcribed slot review queues and a local screenshot
byte-hash coverage preflight. The next step is a **human record of
unresolved visible positions** that remains separate from actual
Gameforge-authenticated observations and simulator formulas.

This two-phase local tool never decodes the images and never certifies
anything the reviewer enters. It instead guards against copying a
review conclusion from a different battle case, slot, image file or
updated transcription. It uses exact browser JSON case **bytes** and
freshly re-hashed local image bytes as **integrity anchors, not
authenticity certificates**.

## 1. Create a Draft worksheet (private Linux/POSIX workstation)

From the repository root, with Python 3.11+, Node and the same
original images and filled capture manifest used by the PR #111–#113
tools:

    python -m tools.research.p0_report_case_manual_visual_review \
      --case private-browser-case.json \
      --manifest private-capture-manifest.json \
      --evidence-root private-original-screenshots \
      --write-review-worksheet NEW-private-review-worksheet.json

Every pending manually typed physical-position comparison (including
an explicitly location-less `NO_ENTERED_VISIBLE_SLOTS` reminder)
is populated from the **canonical JavaScript**
`M.summarizeCapturedTimeline()` + `M.compareCapturedRounds()`.
Rows include exact capture IDs, numeric captured game rounds,
round-number gaps, same-phase flag, side/line/physical position,
original typed-field review reason, and **current SHA-256 file bytes**
for both earlier and target captures (or null when missing).

Every `review_status` starts `NOT_REVIEWED`. The file does NOT
include screenshot bytes, free-text `round.source` notes, absolute
local paths or prefilled factual results. Source manifest validation
and hashing reject malformed/ambiguous/duplicate or mismatched
image stages before creating a worksheet. Partial missing files
may create a worksheet but remain non-evidentiary.

## 2. Manually inspect the original private images

Change only the per-row `review_status` to one of:

| Value | Meaning |
| --- | --- |
| `NOT_REVIEWED` | No manual assessment supplied. |
| `REVIEWER_REPORTS_IMAGES_READABLE` | User reports the **two source images** can be read. Does NOT verify the typed HP/count values. |
| `REVIEWER_REPORTS_TRANSCRIPTION_CONFLICT` | User reports a possible conflict with transcribed fields, for human correction. |
| `REVIEWER_REPORTS_IMAGE_UNREADABLE` | User reports screenshot content cannot reliably be read. |

The three positive/negative reviewer claims are allowed only when
**both source files are locally fingerprinted**. A no-visible-fields
location-less reminder cannot be marked
`REVIEWER_REPORTS_IMAGES_READABLE`. Do not claim an absent file,
an untyped slot, or a missing captured game round has been observed.
A screenshot file hash does not prove the time or game origin, and
a reviewer declaration is **not** an independent Gameforge holdout.

## 3. Validate the human report against the CURRENT originals

    python -m tools.research.p0_report_case_manual_visual_review \
      --case private-browser-case.json \
      --manifest private-capture-manifest.json \
      --evidence-root private-original-screenshots \
      --review-worksheet private-review-worksheet.json \
      --output-json NEW-private-review-assessment.json

The validator rehashes all local files each invocation, redoes
canonical pending-field calculations, and compares **every** worksheet
entry's case SHA, per-capture image SHA, pair IDs, rounds, phase,
physical address and reason against the current original. No missing,
duplicate, additional or modified rows, non-enumerated status, or
forged authority flags accepted. An older worksheet fails if **any**
source image bytes or case JSON bytes change. Use a NEW worksheet
after such edits; do not silently preserve older reviewer claims.

Both output modes use exclusive creation (never overwrite an
original screenshot, JSON backup, source manifest, or previous
review). Any rejected input exits nonzero without writing a new
assessment. Keep the worksheet and review assessment **private**;
they contain capture IDs and file SHA values, though no images
or personal source-note text.

The result is named
`USER_REPORTED_VISUAL_REVIEW_NOT_AUTHENTICATED` or
`NO_REVIEWER_REPORTS_NOT_AUTHENTICATED`. Even a worksheet where
every row has a reviewer-entered status never changes:

- `original_game_screenshots_authenticated=false`
- `source_provenance_independently_verified=false`
- `image_decoded_or_visually_inspected_by_tool=false`
- `independently_verified_game_observations=0`
- `independent_holdouts=0`
- `official_game_mechanism_verified=false`
- `model_calibration_verified=false`
- `combat_causality_inferred=false`

This tool is a provenance-aware *manual follow-up log*,
not an image-authentication workflow, automated OCR, casualty
calibration, or evidence of target selection/healing/Reserve HP
mechanics. CI fixtures are synthetic PNG/JPEG headers and invented
transcriptions, not actual original Gameforge screenshots.
Do not alter production damage/accuracy/healing algorithms
based on these labels. Issue #73 stays **OPEN** until genuine
original images and independent, held-out observations are
evaluated.
