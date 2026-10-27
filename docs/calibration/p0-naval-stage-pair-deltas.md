# Naval R1-end versus R2-prefire: read-only delta ledger

Issue #73, research only. This utility performs simple arithmetic on
USER-TRANSCRIBED archive-v2 screenshot labels. It does NOT verify Gameforge
origin, image identity, timing, HP-rounding or official battle algorithms.

Run locally (keep private source JSON and images outside GitHub):

    PYTHONPATH=. python tools/research/p0_naval_stage_pair_deltas.py --input private-archive-v2.json --output-json private-stage-deltas.json

A valid nonempty PR #88 archive transcription is required. Comparison only
proceeds for distinct nonblank declared R1 and R2 source labels, a record
explicitly claiming R2-prefire timing, and explicit no reinforcements.
Rows must match ALL FOUR user-declared strings: side, unit_id, wave_label
and physical_slot_label. **Additional ambiguity guard:** if the same phase
and side assigns the same user-labeled physical slot to multiple different
unit_id/wave_label identities, none of that slot's apparently matching rows
may produce a delta, even if the competing owner exists in only R1 or only
R2. The output records the phase, side, slot, conflicting unit/wave labels,
and original observation indices in `ambiguous_physical_slots`; other
uncontested slots still permit provisional arithmetic. Reusing a slot label
on the opposing side or a different phase is not in itself a conflict.
This is a conservative transcription-consistency rule, NOT an official
Gameforge formation restriction.
Ownership conflicts are indexed from ALL archive-validated rows before
source-ref eligibility checks; a conflicting row whose source_ref is missing
or wrong, or whose Wave label is unknown, still disqualifies that physical
slot's apparent delta. Source refs remain required for individual row pairing.
Partial observations do not become authenticated evidence through this guard.
Each row must contain the two integer observations
units_alive and visible_percent. Missing or mismatched rows are retained as
follow-up diagnostics; no wave/slot identity is guessed.

The result contains ONLY label strings, integer values, arithmetic differences
(R2 minus R1) and a user-JSON SHA-256, no original image bytes or original
record copy. Labels, hashes and "confirmed" values come from a submitter
and are NOT independently authenticated. Matching labels do not verify
physical ship continuity, even with declared zero reinforcements.

Statuses: UNVERIFIED_LABEL_MATCHED_STAGE_DELTAS means complete literal row
matching only; UNVERIFIED_PARTIAL_STAGE_COMPARISON identifies incomplete,
physical-slot-ownership conflicts or blocked comparisons; INVALID means the archive was invalid/blank,
writes diagnostics and exits 2. Partial reports exit 0.

Every report retains false flags for screenshot provenance, physical identity,
independently confirmed observations, independent holdouts, official healing/
damage mechanism and battle hypothesis comparison. A rendered HP percentage
increase with no ship-count change is NOT proof of Tender repair: aggregation,
rounding, reserve rebuild and heal/RR sequence remain unknown.

Only invented test records are included in CI. The workflow uploads its
existing EMPTY archive template, never user's records or screenshot bytes.
No battle engine production code or official-game formulas changed.
Issue #73 remains OPEN awaiting separately corroborated real game material.
