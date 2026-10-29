# P0 — Source-anchored user model candidate vs typed target snapshot

**Issue #73; research-only; not an automated simulator fitting tool.**

PR #114 introduced private manual visual-review worksheets for unresolved
battle-report capture pairs. Those labels remain **user reports** and cannot
authenticate Gameforge source images, HP bars, casualties, target selection,
or the actual simulator. This step adds a controlled, **user-supplied model
candidate** versus **user-transcribed target slot** diagnostic. It deliberately
does **not** claim to run `ikariam_battle.simulate()`: an arbitrary browser
battle case lacks a verified, round-aligned engine scenario/projection
contract. Ingesting a user-entered candidate is **not a proof** that the
current engine produced it.

## Local private workflow (Linux/POSIX with Node and Python)

Keep v1 case JSON, actual screenshots, filled capture image manifest, and
human-filled visual review worksheet private; see:

- [Local screenshot binding](p0-report-case-local-image-binding.md)
- [Manual pending-slot review](p0-report-case-manual-visual-review.md)

Create a **new unfilled model proposal** from those exact sources:

    python -m tools.research.p0_report_case_model_candidate_diagnostic \
      --case private-case.json \
      --manifest private-capture-manifest.json \
      --evidence-root private-images \
      --review-worksheet private-filled-review.json \
      --write-model-worksheet NEW-private-model-candidate.json

The CLI freshly fingerprints the real local image bytes and validates the
human review worksheet against the canonical JavaScript pending-slot
comparisons. It anchors the result to exact **case JSON bytes SHA-256**,
**filled review worksheet bytes SHA-256**, individual earlier/target image
SHA-256 values, capture IDs, phase/round, side/line/physical position,
pending review reason, and current user-typed target slot details.
It does not copy source-note free text or image bytes.

The worksheet is written as compact UTF-8 JSON (not verbose pretty-printed
JSON) and its **serialized byte length is checked before file creation**
against the same 64 MiB limit used when it is read back for assessment.
If a very large valid case would exceed that limit even in compact form,
the CLI rejects worksheet creation rather than reporting success with an
unimportable result. No original file is overwritten.

The resulting worksheet marks
`model_source_class=USER_ENTERED_MODEL_CANDIDATE_NOT_ENGINE_ATTESTED`
and `model_run_label=null`. To propose candidate predictions, fill
`model_run_label` (short descriptive label, **not** a verified engine
revision), and the per-row `predicted_target_unit`,
`predicted_target_wave`, `predicted_target_count` and
`predicted_target_hp_percent`. Omit numerical values by leaving them
null; **numeric zero remains zero, not missing**. The model values must
be entered **for the target captured snapshot**, not inferred
round-to-round deaths or changes. This is a diagnostic input form,
not executable simulator output. Do not label manual predictions as a
verified engine run.

Assess with a separate **NEW** output path:

    python -m tools.research.p0_report_case_model_candidate_diagnostic \
      --case private-case.json \
      --manifest private-capture-manifest.json \
      --evidence-root private-images \
      --review-worksheet private-filled-review.json \
      --model-worksheet private-model-candidate.json \
      --output-json NEW-private-model-diagnostic.json

All fixed fields and row ordering must match the current source snapshot.
The tool rejects missing/extra/forged rows, changed case/review file bytes,
changed screenshot bytes, modified slot or captured round identity, invalid
user model values, spoofed authority fields and overwrite attempts. It
never modifies original case data, review history, screenshots, engine
code or game mechanics.

## Numeric-diagnostic gates

For a row to have a **descriptive** model minus user-transcribed target
count/HP percentage-point difference, ALL are required:

1. Earlier and target screenshot files have fresh, unambiguous local
   fingerprints and the human review status is
   `REVIEWER_REPORTS_IMAGES_READABLE` (a user report only).
2. The two captures are for **consecutive game rounds**
   (`round_number_gap=1`) and **the same recorded phase**.
3. The **target** slot has complete manually entered unit, Wave,
   count and HP percentage. The location-less no-fields row cannot pass.
4. Candidate target slot contains all corresponding fields with
   valid count/HP and exactly matching unit and Wave labels.
5. The tool **independently checks any known earlier unit and Wave labels**,
   even when canonical `INCOMPLETE` takes precedence because earlier count
   or HP is missing. If any known earlier label differs from the target,
   the row is `NOT_ASSESSABLE_KNOWN_EARLIER_TARGET_LABEL_CHANGE`.
   A missing earlier/target identity, label-changed pair or manually
   reported transcription conflict is never treated as comparable.

This calculation does **not** reconstruct any unseen battle rounds,
verify recorded phases against real game clocks, validate source
screenshots visually, identify actual focus fire, or prove a simulator
mechanism. Eligible outputs are only:

- `USER_ENTERED_MODEL_TARGET_SNAPSHOT_EQUAL_UNVERIFIED`
- `USER_ENTERED_MODEL_TARGET_SNAPSHOT_DIFFERENT_UNVERIFIED`

All other cases get an explicit `NOT_ASSESSABLE_*` reason and
**null** numeric differences. Even matching transcriptions are
**not** independent holdout successes. Numerical differences are
`predicted_target_count - target_typed_count` and
`predicted_target_hp_percent - target_typed_hp_percent` (percentage
points), not differences between two battle rounds.

Every report maintains
`original_game_screenshots_authenticated=false`,
`source_provenance_independently_verified=false`,
`image_decoded_or_visually_inspected_by_tool=false`,
`independently_verified_game_observations=0`,
`independent_holdouts=0`,
`official_game_mechanism_verified=false`,
`model_calibration_verified=false`,
`model_prediction_engine_attested=false` and
`combat_causality_inferred=false`.

Automated tests include ONLY synthetic image headers, synthetic
transcriptions and user-entered model projections; **no original
Gameforge images or real combat simulations**. The next genuinely
scientific step remains independent source authentication, robust
in-game time/slot reconciliation and a separate actual engine
prediction adapter with explicit assumptions and held-out battles.
Do not adjust production Accuracy, HP, targeting, healing or Reserve
formulas based on these candidate diagnostics. Issue #73 remains OPEN.
