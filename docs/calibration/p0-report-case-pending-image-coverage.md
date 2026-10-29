# P0 — Pending captured-round screenshot coverage preflight

**Issue #73, research-only.** After owner-merged PRs #110–#112, a user
can export a browser report-case JSON v1, generate a case-bound screenshot
worksheet, and fingerprint local PNG/JPEG bytes for each capture. The
remaining question is: **which adjacent captured-round comparisons have
local files on both sides, which lack earlier or target images, and which
skip intervening game rounds?**

This additional PRIVATE local audit uses existing canonical case
comparison logic. It never views, verifies, authenticates, or publishes
the original images, and never changes the battle simulator.

## Local workflow

On trusted Linux/POSIX with Python 3.11+ and Node:

1. Export the v1 report case JSON from the browser.
2. Generate and fill a safe case-bound image manifest as documented in
   [local byte binding](p0-report-case-local-image-binding.md).
   Unfinished draft worksheets cannot be processed as evidence.
3. Keep the original images private under an evidence-root directory.
4. Run the audit from the repository root with a NEW output filename:

       python -m tools.research.p0_report_case_pending_image_coverage \
         --case private-browser-case.json \
         --manifest private-filled-image-manifest.json \
         --evidence-root private-game-images \
         --output-json NEW-private-image-coverage.json

The tool performs a **fresh local byte read and SHA-256 check** using the
same secure source binder from PR #111. It does NOT trust or ingest old
editable digest receipts. It separately executes the canonical
`battle-cases-model.js` `summarizeCapturedTimeline()` on the exact
same case bytes, so adjacent captured pairs, game-round number gaps,
different prefire/end-of-round phases, and typed physical-slot review
reason counts are not independently reconstructed by Python.

For each adjacent pair the report includes capture IDs and numeric
rounds, `round_number_gap`, `unknown_intermediate_game_rounds`,
`same_capture_phase`, existing `pending_review_counts` (excluding
comparable typed fields), `comparable_typed_position_count`, and
`file_coverage`: `BOTH_FILES_FINGERPRINTED_UNAUTHENTICATED`,
`ONLY_EARLIER_FILE_FINGERPRINTED_UNAUTHENTICATED`,
`ONLY_TARGET_FILE_FINGERPRINTED_UNAUTHENTICATED`, or
`NEITHER_FILE_FINGERPRINTED`. A pair with no entered visible slots
still has **one location-less follow-up** under
`NO_ENTERED_VISIBLE_SLOTS`; this does not mean there is one game slot.
The total is a **review task count**, not a measured casualty or
physical-position population.

The tool provides actionable next steps:
`COLLECT_MISSING_CAPTURE_IMAGES_THEN_VISUALLY_REVIEW` when one or both
capture files are unbound, and
`MANUALLY_VERIFY_ORIGINAL_CAPTURE_CONTENTS_AND_TIMING` when both byte
fingerprints exist. A gap from R50 to R80 means **29 intervening
game rounds have not been captured**, not that their troops or HP bars
can be inferred.

## Gate and failure boundaries

An invalid case/manifest, unsafe or missing original file that
produces an invalid image binding, hash mismatch, or ambiguous
identical-byte stage returns `INVALID` and exit 2, with **no**
accepted pair coverage. Partial missing files produce
`UNVERIFIED_MISSING_IMAGE_COVERAGE`. All files present yield
`UNVERIFIED_LOCAL_FILES_PRESENT_PENDING_VISUAL_REVIEW`, **not**
verification of the images or a combat algorithm. A one-round case
reports `NO_ADJACENT_CAPTURES_NOT_AUTHENTICATED`, never an inferred
pair. The output file is created exclusively: never overwrite a case,
image, manifest, existing receipt, or symlink/hard link.

The output deliberately does not include image bytes, private
`round.source` free text, or absolute local paths. Every report
fixes `original_game_screenshots_authenticated=false`,
`source_provenance_independently_verified=false`,
`image_decoded_or_visually_inspected=false`,
`independently_verified_game_observations=0`,
`independent_holdouts=0`,
`official_game_mechanism_verified=false` and
`model_calibration_verified=false`.

**No new original Gameforge screenshots are part of this PR.** Test
fixtures use invented minimal PNG/JPEG headers and manually entered
slot values. This preflight is **only a collection/review task aid**,
not scientific verification. Issue #73 remains OPEN pending independent
human corroboration of real captures, consistent physical addresses
and held-out empirical observations before production formulas change.
